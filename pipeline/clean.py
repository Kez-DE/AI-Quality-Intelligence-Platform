import re
from typing import Any


PUBLIC_CONTACT_EMAILS = {
    "support.vn@greensm.com",
    "dpooffice@greensm.com",
}

PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:(?:(?:\+?84)|0)[\s.\-]?(?:3|5|7|8|9)\d(?:[\s.\-]?\d){7}"
    r"|(?:(?:\+?84)|0)[\s.\-]?2\d(?:[\s.\-]?\d){8})(?!\d)"
)
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}\b")
LICENSE_PLATE_PATTERN = re.compile(
    r"(?<!\w)\d{2}\s*[A-ZĐ]{1,2}\d?\s*[-.]?\s*\d{3}(?:[.\s-]?\d{2,3})(?!\w)",
    re.IGNORECASE,
)


def mask_pii(text: str) -> str:
    """
    Xóa hoặc che giấu các thông tin nhạy cảm (PII - Personally Identifiable Information)
    như Số điện thoại và Email trong phản hồi của khách hàng.
    """
    if not isinstance(text, str):
        return text

    protected_emails: dict[str, str] = {}

    def protect_public_email(match: re.Match[str]) -> str:
        email = match.group(0)
        if email.lower() not in PUBLIC_CONTACT_EMAILS:
            return email
        token = f"__PUBLIC_EMAIL_{len(protected_emails)}__"
        protected_emails[token] = email
        return token
    
    # Mask số điện thoại di động VN, kể cả dạng +84/84 và có dấu phân cách.
    text = PHONE_PATTERN.sub('[SĐT_ĐÃ_ẨN]', text)
    
    # Mask Email (ví dụ: test@gmail.com -> [EMAIL_ĐÃ_ẨN]).
    # Email hỗ trợ công khai của Green SM được allowlist để chatbot khách có thể
    # cung cấp đúng kênh liên hệ chính thức, trong khi email cá nhân vẫn bị ẩn.
    text = EMAIL_PATTERN.sub(protect_public_email, text)
    text = EMAIL_PATTERN.sub('[EMAIL_ĐÃ_ẨN]', text)
    for token, email in protected_emails.items():
        text = text.replace(token, email)

    # Mask biển số ô tô/xe máy VN ở dạng liền, có gạch, dấu chấm hoặc khoảng trắng.
    text = LICENSE_PLATE_PATTERN.sub('[BIỂN_SỐ_ĐÃ_ẨN]', text)
    
    return text


def sanitize_pii_payload(value: Any) -> Any:
    """Tạo bản sao payload và che PII trong mọi chuỗi trước khi gửi ra ngoài."""
    if isinstance(value, str):
        return mask_pii(value)
    if isinstance(value, list):
        return [sanitize_pii_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_pii_payload(item) for item in value)
    if isinstance(value, dict):
        return {key: sanitize_pii_payload(item) for key, item in value.items()}
    return value

def clean_text(text: str) -> str:
    """
    Làm sạch văn bản cơ bản trước khi đưa vào mô hình NLP.
    """
    if not isinstance(text, str):
        return ""
        
    text = mask_pii(text)
    
    # Xoá khoảng trắng thừa
    text = " ".join(text.split())
    
    return text

# Test thử function nếu chạy file trực tiếp
if __name__ == "__main__":
    sample_text = "Tài xế đi xe biển số 29A-12345 gọi cho tôi qua số 0912345678 và chửi bới. Email của tôi là khachhang@gmail.com"
    print("Raw:", sample_text)
    print("Cleaned:", clean_text(sample_text))
