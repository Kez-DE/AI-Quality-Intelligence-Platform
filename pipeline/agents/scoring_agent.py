"""Scoring Agent — sử dụng LLM chấm điểm rủi ro 5 chiều (Deep Risk Matrix) và chạy Waterfall algorithm."""

import json
from typing import Any, Dict, List
import time
import hashlib

from agents.common import call_llm, parse_json_response, log_agent_run
from agents.schemas import ScoringBatchOutput

def calculate_overall_risk(
    risk_safety: int, 
    risk_fraud: int, 
    risk_attitude: int, 
    risk_vehicle: int, 
    risk_compliance: int
) -> int:
    """Thuật toán Max-Pooling Rule-based Waterfall (Thác rơi ưu tiên rủi ro cao nhất).
    Quy đổi 5 vector rủi ro (thang 0-10) ra điểm cảnh báo chung (Thang 1-5).
    """
    # BẬC 5: KHẨN CẤP (🚨) — CHỈ rủi ro AN TOÀN tính mạng mới lên P5.
    # Bất biến hệ thống: P5 ⟹ routing ép về team Safety (Safety-first). Vì vậy
    # gian lận (fraud) — tuy nghiêm trọng nhưng là vấn đề tài chính — KHÔNG lên P5,
    # nếu không ticket Payment sẽ bị định tuyến nhầm sang Safety. Fraud nặng -> P4.
    if risk_safety >= 8:
        return 5

    # BẬC 4: NGUY HIỂM (🔴) — gian lận nặng, an toàn mức vừa, thái độ rất nặng.
    if risk_fraud >= 8 or risk_safety >= 5 or risk_fraud >= 5 or risk_attitude >= 8:
        return 4

    # BẬC 3: RỦI RO TRUNG BÌNH (🟠)
    count_medium = sum(1 for x in [risk_safety, risk_fraud, risk_attitude, risk_vehicle, risk_compliance] if x >= 4)
    if risk_vehicle >= 6 or risk_compliance >= 6 or risk_attitude >= 6 or count_medium >= 3: 
        return 3

    # BẬC 2: RỦI RO THẤP (🟡)
    if max(risk_safety, risk_fraud, risk_attitude, risk_vehicle, risk_compliance) >= 3: 
        return 2

    # BẬC 1: AN TOÀN / BÌNH THƯỜNG (🟢)
    return 1


def score_feedback_batch(feedbacks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Gom nhóm gọi LLM để lấy điểm rủi ro 5 chiều, sau đó áp dụng Waterfall.
    Nếu thất bại (API lỗi), gán needs_review = True làm Fallback thay vì Rule-based.
    """
    if not feedbacks:
        return []

    # Tạo mapping để đánh Index cho dễ LLM xử lý
    payload_texts = ""
    for idx, f in enumerate(feedbacks):
        text = f.get("text", "")
        payload_texts += f"ID {idx}: {text}\n"

    system_prompt = """Bạn là trợ lý đánh giá rủi ro (Risk Scoring Agent) cho dịch vụ gọi xe.
Cho danh sách các phản hồi tiêu cực của khách hàng. Hãy chấm điểm cho từng phản hồi dựa trên 5 tiêu chí sau (Thang điểm 0 đến 10):
- risk_safety (0-10): Đe dọa tính mạng, tai nạn, sàm sỡ, quấy rối, đánh nhau.
- risk_fraud (0-10): Hành vi gian lận cước, thu thêm tiền vô lý, lừa đảo, trừ tiền oan.
- risk_attitude (0-10): Cư xử lồi lõm, chửi bới, xúc phạm, khó chịu.
- risk_vehicle (0-10): Xe hỏng, hôi, dơ bẩn, điều hòa hỏng.
- risk_compliance (0-10): Đi sai đường, đón trễ lâu, ép hủy, không tuân thủ quy trình.

Yêu cầu: Trả về JSON chứa mảng `results`, mỗi item chứa ID và 5 điểm rủi ro kiểu số nguyên.
Định dạng JSON:
{
  "results": [
    {"id": 0, "risk_safety": 0, "risk_fraud": 0, "risk_attitude": 8, "risk_vehicle": 0, "risk_compliance": 0},
    {"id": 1, ...}
  ]
}
Chỉ trả về JSON thuần hợp lệ, không kèm văn bản nào khác.
"""

    user_prompt = f"Phân tích lô dữ liệu sau:\n{payload_texts}"
    
    start_time = time.time()
    response_text = call_llm(system_prompt, user_prompt, response_format="json_object")
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Mặc định Fallback: cần review thủ công nếu LLM chết
    fallback_result = {
        "risk_safety": 0, "risk_fraud": 0, "risk_attitude": 0, 
        "risk_vehicle": 0, "risk_compliance": 0,
        "needs_review": True,
        "review_reason": "Lỗi API LLM Scoring, cần con người kiểm duyệt"
    }
    
    input_hash = hashlib.md5(payload_texts.encode()).hexdigest()
    status = "success"
    error_msg = ""
    output_sum = ""

    try:
        parsed = parse_json_response(response_text)
        try:
            batch_output = ScoringBatchOutput.model_validate(parsed)
            results = batch_output.results
        except Exception as val_err:
            print(f"[scoring_agent] Pydantic validation error: {val_err}")
            results = []
            status = "fallback"
            error_msg = f"Validation Error: {str(val_err)}"
            
        output_sum = f"Scored {len(results)} items."
        
        # Tạo hash map id -> scores
        score_map = {}
        for r in results:
            score_map[r.id] = r

        for idx, f in enumerate(feedbacks):
            if idx in score_map:
                s = score_map[idx]
                safety = s.risk_safety
                fraud = s.risk_fraud
                attitude = s.risk_attitude
                vehicle = s.risk_vehicle
                compliance = s.risk_compliance
                
                f["risk_safety"] = safety
                f["risk_fraud"] = fraud
                f["risk_attitude"] = attitude
                f["risk_vehicle"] = vehicle
                f["risk_compliance"] = compliance
                f["overall_risk"] = calculate_overall_risk(safety, fraud, attitude, vehicle, compliance)
                f["needs_review"] = f.get("needs_review", False) 
            else:
                f.update(fallback_result)

    except Exception as e:
        print(f"[scoring_agent] Error calling/parsing LLM: {e}")
        status = "failed"
        error_msg = str(e)
        output_sum = "Fallback applied to all."
        # Gán Fallback cho toàn bộ lô
        for f in feedbacks:
            f.update(fallback_result)

    log_agent_run(
        run_id=f"scoring_{int(time.time())}",
        agent_name="scoring_agent",
        status=status,
        latency_ms=latency_ms,
        output_summary=output_sum,
        error_message=error_msg,
        input_hash=input_hash
    )

    return feedbacks
