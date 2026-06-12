import re

def mask_pii(text: str) -> str:
    """
    Xóa hoặc che giấu các thông tin nhạy cảm (PII - Personally Identifiable Information)
    như Số điện thoại và Email trong phản hồi của khách hàng.
    """
    if not isinstance(text, str):
        return text
    
    # Mask số điện thoại VN (ví dụ: 0912345678 -> [SĐT_ĐÃ_ẨN])
    # Regex bắt các chuỗi từ 9 đến 11 số, có thể có dấu chấm/gạch ngang
    phone_pattern = re.compile(r'\b(0|\+84)[-\s\.]?[1-9]\d{2}[-\s\.]?\d{3}[-\s\.]?\d{3}\b')
    text = phone_pattern.sub('[SĐT_ĐÃ_ẨN]', text)
    
    # Mask Email (ví dụ: test@gmail.com -> [EMAIL_ĐÃ_ẨN])
    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
    text = email_pattern.sub('[EMAIL_ĐÃ_ẨN]', text)
    
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
