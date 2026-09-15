from agent.model_router import chat_completion, parse_json_response, provider_has_key, resolve_provider

def mock_spike_response(area: str, feedback_texts: list[str]) -> dict:
    """Mô tả suy diễn khi không có LLM — chỉ nhắc lại dữ liệu thật, KHÔNG bịa nguyên nhân.

    Bản cũ trả một đoạn cố định về "thái độ phục vụ nhân viên và chất lượng sản phẩm
    giảm sút trong giờ cao điểm" cho MỌI alert, bất kể nội dung phản hồi. Không có LLM
    key là mọi ticket trong hệ mang cùng một nguyên nhân bịa.
    """
    print(f"[{area}] Chưa có LLM API key. Mô tả lấy trực tiếp từ dữ liệu (không suy luận).")
    samples = [t.strip() for t in feedback_texts if t and t.strip()][:3]
    quoted = "; ".join(f"\"{s[:120]}\"" for s in samples) or "không có mẫu văn bản"
    return {
        "title": f"Cụm phản hồi tiêu cực tại {area}",
        "description": (
            f"{len(feedback_texts)} phản hồi cùng nhóm tại {area}. Trích mẫu: {quoted}. "
            "Chưa có phân tích nguyên nhân (không khả dụng LLM) — cần người phụ trách đọc và kết luận."
        ),
        "action": "Phân công người phụ trách đọc cụm phản hồi này và xác định nguyên nhân.",
    }

def build_spike_prompt(area: str, feedback_texts: list[str]) -> str:
    reviews_text = "\n".join([f"- {text}" for text in feedback_texts])
    return f"""
Bạn là một chuyên gia phân tích dữ liệu khách hàng (Customer Insights Analyst).
Hệ thống vừa phát hiện một lượng lớn phản hồi tiêu cực (Spike) tại khu vực: {area}.

Dưới đây là danh sách các phản hồi (reviews) thu thập được:
{reviews_text}

Nhiệm vụ của bạn:
1. Đọc kỹ các phản hồi trên và tìm ra nguyên nhân gốc rễ chung nhất (Root Cause).
2. Viết một tiêu đề (title) ngắn gọn, súc tích (dưới 10 từ) mô tả sự cố.
3. Đề xuất một hành động (action) cần thực hiện ngay lập tức để khắc phục.
YÊU CẦU BẮT BUỘC: Bạn CHỈ ĐƯỢC PHÉP trả về kết quả dưới dạng JSON theo đúng định dạng sau, không thêm bất kỳ văn bản giải thích nào khác ngoài JSON:
{{
  "title": "Tên sự cố ngắn gọn",
  "description": "Mô tả nguyên nhân gốc rễ một cách chuyên nghiệp",
  "action": "Đề xuất hành động khắc phục"
}}
"""

def analyze_spike(area: str, feedback_texts: list[str]) -> dict:
    """
    Gửi danh sách các phản hồi tiêu cực của một khu vực cho LLM để phân tích nguyên nhân gốc rễ.
    """
    provider = resolve_provider()
    if provider == "mock" or not provider_has_key(provider):
        return mock_spike_response(area, feedback_texts)

    try:
        # Bỏ sleep(2) demo: model_router đã có retry + backoff cho 429, còn 20 spike/lượt
        # nhân 2 giây là 40 giây chờ trắng mỗi chu kỳ pipeline.
        print(f"[{area}] Đang gọi AI provider={provider} phân tích...")
        response = chat_completion(
            [{"role": "user", "content": build_spike_prompt(area, feedback_texts)}],
            response_json=True,
            temperature=0.3,
        )
        if response.get("provider") == "mock":
            return mock_spike_response(area, feedback_texts)
        return parse_json_response(response["content"])
    except Exception as e:
        print(f"Error calling LLM or parsing JSON: {e}")
        return {
            "title": f"Cảnh báo sự cố tại {area}",
            "description": f"Phát hiện {len(feedback_texts)} phản hồi tiêu cực. Không thể tự động phân tích chi tiết do lỗi LLM: {str(e)[:50]}...",
            "action": "Cần nhân viên CSKH kiểm tra thủ công ngay lập tức.",
        }
