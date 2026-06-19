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
    "Safety": {
        "persona": "Bạn là chuyên gia an toàn vận hành. Tính mạng và sự an toàn của "
                   "khách hàng, tài xế là ưu tiên TUYỆT ĐỐI.",
        "priorities": "Luôn giả định tình huống xấu nhất. Nâng mức rủi ro lên 1 cấp khi "
                      "có dấu hiệu đe doạ an toàn. Đề xuất escalate sớm, không chờ đủ dữ liệu.",
        "fallback_actions": [
            ("Escalate ngay các ca nghi mất an toàn lên trực lãnh đạo", "1h"),
            ("Liên hệ trực tiếp khách hàng/tài xế bị ảnh hưởng để xác minh", "6h"),
            ("Rà soát quy trình an toàn liên quan và cập nhật cảnh báo", "24h"),
        ],
    },
    "Pricing": {
        "persona": "Bạn là chuyên gia phân tích giá cước & doanh thu.",
        "priorities": "Nhìn vấn đề dưới góc doanh thu, độ co giãn giá và rò rỉ doanh thu. "
                      "Ước lượng tác động tiền bạc và mức độ ảnh hưởng tới chuyển đổi.",
        "fallback_actions": [
            ("Rà soát cấu hình giá/khuyến mãi tại khu vực bị phản ánh", "24h"),
            ("Phân tích tác động doanh thu của vấn đề giá đang gặp", "48h"),
            ("Đề xuất điều chỉnh chính sách giá/mã giảm giá", "1w"),
        ],
    },
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


def _fallback_analysis(team: str, insights: Dict[str, Any], risk_level: str = "MEDIUM") -> Dict[str, Any]:
    top_topics = insights.get("top_topics") or []
    first_topic = top_topics[0] if isinstance(top_topics, list) and top_topics else {}
    top_topic = first_topic.get("topic") if isinstance(first_topic, dict) else None
    top_topic = top_topic or "general"

    persona = DEPARTMENT_PERSONAS.get(team)
    if persona and persona.get("fallback_actions"):
        action_items = [
            ActionItem(action=action, deadline=deadline)
            for action, deadline in persona["fallback_actions"]
        ]
    else:
        action_items = [
            ActionItem(action=f"Rà soát ticket gần đây của phòng {team}", deadline="24h"),
            ActionItem(action="Liên hệ khách hàng bị ảnh hưởng", deadline="48h"),
            ActionItem(action="Cập nhật quy trình nội bộ", deadline="1w"),
        ]

    analysis = AnalystAnalysis(
        root_cause_summary=f"Nhiều phàn nàn liên quan đến {top_topic}",
        risk_level=risk_level,
        action_items=action_items,
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

    persona = DEPARTMENT_PERSONAS.get(team)
    if persona:
        persona_intro = f"{persona['persona']}\n{persona['priorities']}\n\n"
    else:
        persona_intro = ""

    system_prompt = f"""{persona_intro}Bạn là chuyên gia phân tích vận hành cho phòng {team}.
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
