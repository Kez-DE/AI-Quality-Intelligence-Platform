import re

def mask_pii(text: str) -> str:
    """
    Xóa hoặc che giấu các thông tin nhạy cảm (PII - Personally Identifiable Information)
    như Số điện thoại và Email trong phản hồi của khách hàng.
    """
    if not isinstance(text, str):
        return text
    
    # Mask số điện thoại VN (ví dụ: 0912345678 -> [SĐT_ĐÃ_ẨN])
    phone_pattern = re.compile(r'\b(0|\+84)[-\s\.]?[1-9]\d{2}[-\s\.]?\d{3}[-\s\.]?\d{3}\b')
    text = phone_pattern.sub('[SĐT_ĐÃ_ẨN]', text)
    
    # Mask Email (ví dụ: test@gmail.com -> [EMAIL_ĐÃ_ẨN])
    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
    text = email_pattern.sub('[EMAIL_ĐÃ_ẨN]', text)

    # Mask Biển số xe VN (ví dụ: 29A-12345 hoặc 51F-123.45 -> [BIỂN_SỐ_ĐÃ_ẨN])
    license_plate_pattern = re.compile(r'\b\d{2}[A-ZĐ]\d?[-\s]?\d{3,4}\.?\d{0,2}\b', re.IGNORECASE)
    text = license_plate_pattern.sub('[BIỂN_SỐ_ĐÃ_ẨN]', text)
    
    return text

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
