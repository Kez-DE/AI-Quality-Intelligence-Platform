"""Analyst Agent — dùng LLM phân tích root-cause xuyên suốt nhiều feedback của 1 phòng ban."""

import json
from typing import Any, Dict
import time
import hashlib

from agents.common import call_llm, parse_json_response, log_agent_run
from agents.schemas import AnalystOutput, AnalystAnalysis, ActionItem


def _fallback_analysis(team: str, insights: Dict[str, Any], risk_level: str = "MEDIUM") -> Dict[str, Any]:
    top_topics = insights.get("top_topics") or []
    first_topic = top_topics[0] if isinstance(top_topics, list) and top_topics else {}
    top_topic = first_topic.get("topic") if isinstance(first_topic, dict) else None
    top_topic = top_topic or "general"
    
    analysis = AnalystAnalysis(
        root_cause_summary=f"Nhiều phàn nàn liên quan đến {top_topic}",
        risk_level=risk_level,
        action_items=[
            ActionItem(action=f"Rà soát ticket gần đây của phòng {team}", deadline="24h"),
            ActionItem(action="Liên hệ khách hàng bị ảnh hưởng", deadline="48h"),
            ActionItem(action="Cập nhật quy trình nội bộ", deadline="1w"),
        ]
    )
    output = AnalystOutput(status="fallback", analysis=analysis)
    return output.model_dump()


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
    
    start_time = time.time()
    response_text = call_llm(system_prompt, user_prompt, response_format="json_object")
    latency_ms = int((time.time() - start_time) * 1000)
    
    input_hash = hashlib.md5(combined_texts.encode()).hexdigest()
    status = "success"
    error_msg = ""
    output_sum = ""

    try:
        if response_text:
            parsed = parse_json_response(response_text)
            analysis = AnalystAnalysis.model_validate(parsed)
            if analysis.risk_level not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
                analysis.risk_level = "MEDIUM"
                
            output = AnalystOutput(status="success", analysis=analysis)
            
            log_agent_run(
                run_id=f"analyst_{int(time.time())}",
                agent_name="analyst_agent",
                status="success",
                latency_ms=latency_ms,
                output_summary=f"Risk level: {analysis.risk_level}, {len(analysis.action_items)} actions.",
                error_message="",
                input_hash=input_hash
            )
            return output.model_dump()
            
    except Exception as e:
        status = "fallback"
        error_msg = f"Failed to parse LLM JSON: {str(e)}"
        print(f"[analyst_agent] {error_msg}")

    log_agent_run(
        run_id=f"analyst_{int(time.time())}",
        agent_name="analyst_agent",
        status=status,
        latency_ms=latency_ms,
        output_summary="Fallback triggered.",
        error_message=error_msg,
        input_hash=input_hash
    )
    
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
