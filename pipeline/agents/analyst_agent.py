"""Analyst Agent — dùng LLM phân tích root-cause xuyên suốt nhiều feedback của 1 phòng ban."""

import json
from typing import Any, Dict

from agents.common import call_llm, parse_json_response


def _fallback_analysis(team: str, insights: Dict[str, Any], risk_level: str = "MEDIUM") -> Dict[str, Any]:
    top_topics = insights.get("top_topics") or []
    first_topic = top_topics[0] if isinstance(top_topics, list) and top_topics else {}
    top_topic = first_topic.get("topic") if isinstance(first_topic, dict) else None
    top_topic = top_topic or "general"
    return {
        "status": "fallback",
        "analysis": {
            "root_cause_summary": f"Nhiều phàn nàn liên quan đến {top_topic}",
            "risk_level": risk_level,
            "action_items": [
                {"action": f"Rà soát ticket gần đây của phòng {team}", "deadline": "24h"},
                {"action": "Liên hệ khách hàng bị ảnh hưởng", "deadline": "48h"},
                {"action": "Cập nhật quy trình nội bộ", "deadline": "1w"},
            ],
        },
    }


def _normalize_analysis(payload: Dict[str, Any]) -> Dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    action_items = payload.get("action_items")
    if not isinstance(action_items, list):
        action_items = []

    normalized_items = []
    for item in action_items[:5]:
        if isinstance(item, dict):
            action = str(item.get("action") or "").strip()
            if action:
                normalized_items.append({
                    "action": action,
                    "deadline": str(item.get("deadline") or "").strip() or None,
                })
        elif isinstance(item, str) and item.strip():
            normalized_items.append({"action": item.strip(), "deadline": None})

    summary = str(payload.get("root_cause_summary") or "").strip()
    risk_level = str(payload.get("risk_level") or "MEDIUM").strip().upper()
    if risk_level not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        risk_level = "MEDIUM"

    if not summary and not normalized_items:
        return None

    return {
        "root_cause_summary": summary or "Chưa đủ tín hiệu để kết luận nguyên nhân gốc.",
        "risk_level": risk_level,
        "action_items": normalized_items,
    }


def analyze_root_cause(team: str, insights: Dict[str, Any]) -> Dict[str, Any]:
    """Phân tích nguyên nhân gốc rễ + đề xuất 3 action item cho một phòng ban."""
    samples = insights.get("recent_samples", [])
    if not samples:
        return {"status": "skipped", "reason": "No recent samples to analyze", "analysis": None}

    texts = [str(s.get("text") or "").strip() for s in samples if isinstance(s, dict)]
    texts = [text for text in texts if text]
    if not texts:
        return {"status": "skipped", "reason": "No usable sample text to analyze", "analysis": None}

    combined_texts = "\n- ".join(texts)

    system_prompt = f"""Bạn là chuyên gia phân tích vận hành cho phòng {team}.
Nhiệm vụ: đọc các phản hồi tiêu cực gần đây và tìm NGUYÊN NHÂN GỐC RỄ (root cause),
không chỉ tóm tắt. Tìm các vấn đề mang tính hệ thống.

Trả về JSON đúng cấu trúc:
{{
  "root_cause_summary": "1-2 câu tóm tắt vấn đề hệ thống chính",
  "risk_level": "LOW | MEDIUM | HIGH | CRITICAL",
  "action_items": [
    {{"action": "Hành động cụ thể 1", "deadline": "24h"}},
    {{"action": "Hành động cụ thể 2", "deadline": "48h"}},
    {{"action": "Hành động cụ thể 3", "deadline": "1w"}}
  ]
}}"""

    user_prompt = f"Phân tích các phản hồi gần đây cho phòng {team}:\n- {combined_texts}"
    response_text = call_llm(system_prompt, user_prompt, response_format="json_object")

    try:
        if response_text:
            parsed = parse_json_response(response_text)
            normalized = _normalize_analysis(parsed)
            if normalized:
                return {"status": "success", "analysis": normalized}
    except (json.JSONDecodeError, ValueError, TypeError, AttributeError):
        print(f"[analyst_agent] Failed to parse LLM JSON: {response_text[:200]}")

    return _fallback_analysis(team, insights)


if __name__ == "__main__":
    mock = {
        "recent_samples": [
            {"text": "App crash khi thanh toán"},
            {"text": "Màn hình thanh toán treo 5 phút"},
        ],
        "top_topics": [{"topic": "App Issue"}],
    }
    print(analyze_root_cause("IT", mock))
