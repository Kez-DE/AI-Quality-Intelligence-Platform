"""Analyst Agent — dùng LLM phân tích root-cause xuyên suốt nhiều feedback của 1 phòng ban."""

import json
from typing import Any, Dict
import time
import hashlib

from agents.common import call_llm, parse_json_response, log_agent_run
from agents.schemas import AnalystOutput, AnalystAnalysis, ActionItem


# Persona chuyên biệt theo phòng ban: mỗi phòng phân tích root-cause qua một
# "lăng kính" riêng (persona + priorities chèn vào system prompt) và có sẵn bộ
# action-item dự phòng (fallback_actions) đúng nghiệp vụ khi LLM lỗi.
# Phòng không có trong bảng (vd team lạ) -> dùng prompt + action generic.
DEPARTMENT_PERSONAS: Dict[str, Dict[str, Any]] = {
    "IT": {
        "persona": "Bạn là kỹ sư phần mềm phân tích sự cố kỹ thuật.",
        "priorities": "Tập trung tìm lỗi kỹ thuật, xác định severity hệ thống và các bước "
                      "tái hiện (repro steps) rõ ràng cho đội phát triển.",
        "fallback_actions": [
            ("Tạo ticket kỹ thuật kèm các bước tái hiện (repro steps)", "24h"),
            ("Kiểm tra log/monitoring để khoanh vùng nguyên nhân kỹ thuật", "48h"),
            ("Lên kế hoạch hotfix hoặc bản vá cho lỗi đã xác định", "1w"),
        ],
    },
    "CSKH": {
        "persona": "Bạn là chuyên gia chăm sóc khách hàng.",
        "priorities": "Ưu tiên trải nghiệm và cảm xúc khách hàng. Đề xuất hành động xoa dịu, "
                      "phản hồi kịp thời với tông giọng dịch vụ.",
        "fallback_actions": [
            ("Soạn kịch bản phản hồi cho các khách hàng bị ảnh hưởng", "24h"),
            ("Liên hệ xin lỗi và hỗ trợ khách hàng có phản hồi tiêu cực", "48h"),
            ("Cập nhật FAQ/quy trình hỗ trợ để giảm khiếu nại tương tự", "1w"),
        ],
    },
    "Vận hành": {
        "persona": "Bạn là chuyên gia điều phối vận hành (cung-cầu tài xế).",
        "priorities": "Tập trung vào tài xế, mật độ cung-cầu theo khu vực và các điểm nóng "
                      "thiếu cuốc/chậm trễ.",
        "fallback_actions": [
            ("Phân tích mật độ tài xế tại các khu vực nóng được phản ánh", "24h"),
            ("Điều phối bổ sung tài xế cho khu vực thiếu cuốc", "48h"),
            ("Đề xuất cải thiện quy trình điều phối/khuyến khích tài xế", "1w"),
        ],
    },
    "Marketing": {
        "persona": "Bạn là chuyên gia thương hiệu & truyền thông.",
        "priorities": "Nhìn vấn đề dưới góc nhận diện thương hiệu và cảm nhận thị trường. "
                      "Đánh giá rủi ro danh tiếng và cơ hội truyền thông tích cực.",
        "fallback_actions": [
            ("Đánh giá ảnh hưởng tới nhận diện thương hiệu", "48h"),
            ("Theo dõi cảm nhận thị trường trên các kênh truyền thông", "48h"),
            ("Đề xuất thông điệp truyền thông phù hợp", "1w"),
        ],
    },
}


def derive_risk_level(insights: Dict[str, Any]) -> str:
    """Derive report risk from measured severity, not LLM judgement."""
    severity = insights.get("severity_distribution") or {}
    if int(severity.get("CRITICAL", 0)) > 0:
        return "CRITICAL"
    if int(severity.get("WARNING", 0)) > 0:
        return "HIGH"
    if int(severity.get("WATCH", 0)) > 0:
        return "MEDIUM"
    return "LOW"


def _fallback_analysis(team: str, insights: Dict[str, Any]) -> Dict[str, Any]:
    top_topics = insights.get("top_topics") or []
    first_topic = top_topics[0] if isinstance(top_topics, list) and top_topics else {}
    top_topic = first_topic.get("topic") if isinstance(first_topic, dict) else None
    top_topic = top_topic or "general"

    persona = DEPARTMENT_PERSONAS.get(team)
    if persona and persona.get("fallback_actions"):
        action_items = [
            ActionItem(
                action=action,
                deadline=deadline,
                owner=team,
                success_metric="Hoàn thành và ghi nhận kết quả xử lý",
                priority=f"P{index}",
            )
            for index, (action, deadline) in enumerate(persona["fallback_actions"], start=1)
        ]
    else:
        action_items = [
            ActionItem(action=f"Rà soát ticket gần đây của phòng {team}", deadline="24h", owner=team, priority="P1"),
            ActionItem(action="Liên hệ khách hàng bị ảnh hưởng", deadline="48h", owner=team, priority="P2"),
            ActionItem(action="Cập nhật quy trình nội bộ", deadline="1w", owner=team, priority="P3"),
        ]

    analysis = AnalystAnalysis(
        root_cause_summary=(
            f"Dữ liệu ghi nhận nhiều phản hồi liên quan đến {top_topic}; "
            "chưa đủ bằng chứng để khẳng định nguyên nhân gốc rễ và cần xác minh thêm."
        ),
        risk_level=derive_risk_level(insights),
        action_items=action_items,
        evidence=[f"Chủ đề nổi bật trong kỳ: {top_topic}"],
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
    aggregate_facts = {
        "total_feedback": insights.get("total_feedback", 0),
        "severity_distribution": insights.get("severity_distribution", {}),
        "sentiment_distribution": insights.get("sentiment_distribution", {}),
        "task_status_distribution": insights.get("task_status_distribution", {}),
        "overdue_tasks": insights.get("overdue_tasks", 0),
        "top_topics": insights.get("top_topics", []),
        "top_areas": insights.get("top_areas", []),
    }

    persona = DEPARTMENT_PERSONAS.get(team)
    if persona:
        persona_intro = f"{persona['persona']}\n{persona['priorities']}\n\n"
    else:
        persona_intro = ""

    system_prompt = f"""{persona_intro}Bạn là chuyên gia phân tích vận hành cho phòng {team}.
Nhiệm vụ: đưa ra nhận định nguyên nhân cần xác minh và kế hoạch cải tiến cho phòng {team}.
Chỉ sử dụng số liệu và mẫu phản hồi được cung cấp. Không tự tạo số liệu, xu hướng,
tác động tài chính hoặc nguyên nhân không có bằng chứng. Nếu chưa đủ bằng chứng, phải nói rõ.

Trả về JSON đúng cấu trúc:
{{
  "root_cause_summary": "1-2 câu, ghi rõ đây là nhận định cần xác minh nếu dữ liệu chưa đủ",
  "risk_level": "LOW | MEDIUM | HIGH | CRITICAL",
  "evidence": ["2-4 bằng chứng ngắn lấy từ số liệu được cung cấp"],
  "action_items": [
    {{"priority": "P1", "action": "Hành động cụ thể", "owner": "{team}", "deadline": "24h", "success_metric": "Kết quả đo được"}}
  ]
}}"""

    user_prompt = (
        f"Số liệu tổng hợp:\n{json.dumps(aggregate_facts, ensure_ascii=False)}\n\n"
        f"Mẫu phản hồi gần đây:\n- {combined_texts}"
    )
    
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
            analysis.risk_level = derive_risk_level(insights)
            for index, action in enumerate(analysis.action_items[:5], start=1):
                action.priority = action.priority or f"P{min(index, 3)}"
                action.owner = action.owner or team
                action.deadline = action.deadline or "48h"
                action.success_metric = action.success_metric or "Hoàn thành và ghi nhận kết quả"
            analysis.action_items = analysis.action_items[:5]
                
            output = AnalystOutput(status="success", analysis=analysis)
            
            log_agent_run(
                run_id=f"analyst_{int(time.time())}",
                agent_name="analyst_agent",
                status="success",
                latency_ms=latency_ms,
                output_summary=f"Risk level: {analysis.risk_level}, {len(analysis.action_items)} actions.",
                error_message="",
                input_hash=input_hash,
                team=team
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
        input_hash=input_hash,
        team=team
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
