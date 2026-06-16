"""Agent 1 — Ingestion/Classifier Agent.

Nhận feedback thô, clean PII, chạy ML phân loại topic/sentiment/severity,
áp rule safety keyword. Trả về feedback đã được gán nhãn đầy đủ.

Agent này wrap logic từ clean.py + classifier.py + rules.py thành một unit
có input/output schema rõ ràng, có fallback khi model lỗi, và ghi agent_run_log.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agents.common import get_db


@dataclass
class IngestionInput:
    """Input cho Ingestion Agent."""
    text: str
    channel: str = "app"
    area: str = ""
    source: str = "manual"
    user_id: Optional[str] = None


@dataclass
class IngestionOutput:
    """Output sau khi Ingestion Agent xử lý."""
    cleaned_text: str
    topic: str
    sentiment: str
    severity: str
    confidence: float
    needs_review: bool
    review_reason: Optional[str] = None
    area: str = ""
    channel: str = "app"
    source: str = "manual"
    user_id: Optional[str] = None
    input_hash: str = ""


@dataclass
class AgentRunLog:
    """Log mỗi lần agent chạy."""
    run_id: str = ""
    agent_name: str = "ingestion_agent"
    input_hash: str = ""
    output_summary: str = ""
    status: str = "success"
    latency_ms: int = 0
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _compute_hash(text: str) -> str:
    """Hash nội dung để phát hiện trùng lặp."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:16]


def _fallback_classify(text: str) -> Dict[str, Any]:
    """Fallback heuristic khi model ML không load được."""
    # Safety keywords check
    safety_keywords = [
        "tai nạn", "say xỉn", "say rượu", "cướp", "hành hung",
        "sàm sỡ", "đe dọa", "tông", "bỏ chạy", "nguy hiểm",
        "chết", "thương", "đâm", "gian lận", "lừa đảo",
    ]
    text_lower = text.lower()
    is_safety = any(kw in text_lower for kw in safety_keywords)

    if is_safety:
        return {
            "topic": "Safety",
            "sentiment": "negative",
            "severity": "P5",
            "confidence": 0.75,
            "needs_review": True,
            "review_reason": "safety_keyword_fallback",
        }

    # Basic sentiment heuristic
    negative_words = ["tệ", "kém", "chậm", "lỗi", "hỏng", "xấu", "ghét", "dở"]
    positive_words = ["tốt", "hay", "nhanh", "tuyệt", "thích", "ok", "ổn"]

    neg_count = sum(1 for w in negative_words if w in text_lower)
    pos_count = sum(1 for w in positive_words if w in text_lower)

    if neg_count > pos_count:
        sentiment = "negative"
        severity = "P3"
    elif pos_count > neg_count:
        sentiment = "positive"
        severity = "P1"
    else:
        sentiment = "neutral"
        severity = "P2"

    return {
        "topic": "General",
        "sentiment": sentiment,
        "severity": severity,
        "confidence": 0.40,
        "needs_review": True,
        "review_reason": "fallback_heuristic",
    }


def process_feedback(input_data: IngestionInput) -> IngestionOutput:
    """Xử lý một feedback: clean -> classify -> trả output có schema.

    Có fallback khi classifier hoặc clean module lỗi.
    """
    start_time = time.time()
    input_hash = _compute_hash(input_data.text)

    # Step 1: Clean PII
    try:
        from clean import clean_text
        cleaned = clean_text(input_data.text)
    except Exception:
        # Fallback: giữ nguyên text nếu clean module lỗi
        cleaned = input_data.text

    # Step 2: Normalize area code
    try:
        from regions import region_code
        area = region_code(input_data.area) if input_data.area else ""
    except Exception:
        area = input_data.area

    # Step 3: Classify (ML + Rule engine)
    try:
        from classifier import predict_feedback
        prediction = predict_feedback(cleaned)
    except Exception:
        # Fallback heuristic khi model lỗi
        prediction = _fallback_classify(cleaned)

    # Normalize severity format
    severity = prediction.get("severity", "P3")
    if isinstance(severity, int):
        severity = f"P{severity}"
    elif isinstance(severity, str) and not severity.upper().startswith("P"):
        try:
            severity = f"P{int(severity)}"
        except ValueError:
            severity = "P3"

    output = IngestionOutput(
        cleaned_text=cleaned,
        topic=prediction.get("topic", "General"),
        sentiment=prediction.get("sentiment", "neutral"),
        severity=severity,
        confidence=prediction.get("confidence", 0.5),
        needs_review=prediction.get("needs_review", False),
        review_reason=prediction.get("review_reason"),
        area=area,
        channel=input_data.channel,
        source=input_data.source,
        user_id=input_data.user_id,
        input_hash=input_hash,
    )

    # Log agent run
    latency_ms = int((time.time() - start_time) * 1000)
    _log_run(AgentRunLog(
        run_id=f"ingest_{input_hash}_{int(time.time())}",
        input_hash=input_hash,
        output_summary=f"{output.topic}/{output.sentiment}/{output.severity}",
        latency_ms=latency_ms,
    ))

    return output


def process_batch(inputs: List[IngestionInput]) -> List[IngestionOutput]:
    """Xử lý batch feedback. Mỗi item độc lập — lỗi 1 item không ảnh hưởng batch."""
    results = []
    for item in inputs:
        try:
            results.append(process_feedback(item))
        except Exception as exc:
            # Không để 1 item hỏng cả batch
            print(f"[ingestion_agent] Error processing item: {exc}")
            results.append(IngestionOutput(
                cleaned_text=item.text,
                topic="Error",
                sentiment="neutral",
                severity="P3",
                confidence=0.0,
                needs_review=True,
                review_reason="processing_error",
                area=item.area,
                channel=item.channel,
                source=item.source,
                user_id=item.user_id,
                input_hash=_compute_hash(item.text),
            ))
    return results


def save_to_db(output: IngestionOutput) -> Dict[str, Any]:
    """Lưu kết quả vào Supabase feedback table."""
    db = get_db()
    row = {
        "text": output.cleaned_text,
        "topic": output.topic,
        "sentiment": output.sentiment,
        "severity": output.severity,
        "confidence": output.confidence,
        "needs_review": output.needs_review,
        "review_reason": output.review_reason,
        "area": output.area,
        "channel": output.channel,
        "source": output.source,
    }
    if output.user_id:
        row["user_id"] = output.user_id

    result = db.table("feedback").insert(row).execute()
    return (result.data or [{}])[0]


def _log_run(log: AgentRunLog):
    """Ghi agent_run_log vào DB (best-effort, không crash nếu lỗi)."""
    try:
        db = get_db()
        db.table("agent_run_logs").insert(asdict(log)).execute()
    except Exception:
        # Best-effort logging — không crash agent vì log
        pass


if __name__ == "__main__":
    test_input = IngestionInput(
        text="Tài xế say xỉn lái xe nguy hiểm quá",
        channel="app",
        area="HN-Cau-Giay",
    )
    result = process_feedback(test_input)
    print(f"Topic: {result.topic}")
    print(f"Sentiment: {result.sentiment}")
    print(f"Severity: {result.severity}")
    print(f"Needs review: {result.needs_review}")
    print(f"Confidence: {result.confidence}")
