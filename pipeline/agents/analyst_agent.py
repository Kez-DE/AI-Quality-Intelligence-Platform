"""Analyst Agent — dùng LLM phân tích root-cause xuyên suốt nhiều feedback của 1 phòng ban."""

import json
from typing import Any, Dict

from agents.common import call_llm


def analyze_root_cause(team: str, insights: Dict[str, Any]) -> Dict[str, Any]:
    """Phân tích nguyên nhân gốc rễ + đề xuất 3 action item cho một phòng ban."""
    samples = insights.get("recent_samples", [])
    if not samples:
        return {"status": "skipped", "reason": "No recent samples to analyze", "analysis": None}

    texts = [s["text"] for s in samples]
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
            return {"status": "success", "analysis": json.loads(response_text)}
    except json.JSONDecodeError:
        print(f"[analyst_agent] Failed to parse LLM JSON: {response_text[:200]}")

    # Fallback heuristic khi LLM lỗi/thiếu key
    top_topic = (insights.get("top_topics") or [{"topic": "general"}])[0]["topic"]
    return {
        "status": "fallback",
        "analysis": {
            "root_cause_summary": f"Nhiều phàn nàn liên quan đến {top_topic}",
            "risk_level": "MEDIUM",
            "action_items": [
                {"action": f"Rà soát ticket gần đây của phòng {team}", "deadline": "24h"},
                {"action": "Liên hệ khách hàng bị ảnh hưởng", "deadline": "48h"},
                {"action": "Cập nhật quy trình nội bộ", "deadline": "1w"},
            ],
        },
    }


if __name__ == "__main__":
    mock = {
        "recent_samples": [
            {"text": "App crash khi thanh toán"},
            {"text": "Màn hình thanh toán treo 5 phút"},
        ],
        "top_topics": [{"topic": "App Issue"}],
    }
    print(analyze_root_cause("IT", mock))
