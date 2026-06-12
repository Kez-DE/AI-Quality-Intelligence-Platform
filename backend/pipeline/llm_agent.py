import time
from agent.model_router import chat_completion, parse_json_response, provider_has_key, resolve_provider

def mock_spike_response(area: str, feedback_texts: list[str]) -> dict:
    print(f"[{area}] Chưa có LLM API key. Đang dùng chế độ giả lập (Mock AI)...")
    time.sleep(1)
    return {
        "title": f"Bùng nổ phàn nàn tại {area}",
        "description": f"Tổng hợp {len(feedback_texts)} review: Khách hàng phản ánh gay gắt về thái độ phục vụ của nhân viên và chất lượng sản phẩm giảm sút trong giờ cao điểm.",
        "action": "Yêu cầu Quản lý khu vực xuống trực tiếp chi nhánh kiểm tra camera và chấn chỉnh đội ngũ ngay lập tức.",
        "assigned_team": "Vận hành & Đào tạo",
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
4. Xác định phòng ban nào (assigned_team) cần chịu trách nhiệm xử lý (VD: Vận hành, Cửa hàng, IT, Giao hàng...).

YÊU CẦU BẮT BUỘC: Bạn CHỈ ĐƯỢC PHÉP trả về kết quả dưới dạng JSON theo đúng định dạng sau, không thêm bất kỳ văn bản giải thích nào khác ngoài JSON:
{{
  "title": "Tên sự cố ngắn gọn",
  "description": "Mô tả nguyên nhân gốc rễ một cách chuyên nghiệp",
  "action": "Đề xuất hành động khắc phục",
  "assigned_team": "Tên phòng ban xử lý"
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
        print(f"[{area}] Đang gọi AI provider={provider} phân tích...")
        time.sleep(2)
        response = chat_completion(
            [{"role": "user", "content": build_spike_prompt(area, feedback_texts)}],
            response_json=True,
            temperature=0.3,
        )
        return parse_json_response(response["content"])
    except Exception as e:
        print(f"Error calling LLM or parsing JSON: {e}")
        return {
            "title": f"Cảnh báo sự cố tại {area}",
            "description": f"Phát hiện {len(feedback_texts)} phản hồi tiêu cực. Không thể tự động phân tích chi tiết do lỗi LLM: {str(e)[:50]}...",
            "action": "Cần nhân viên CSKH kiểm tra thủ công ngay lập tức.",
            "assigned_team": "CSKH",
        }
