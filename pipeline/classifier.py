import os
import joblib

# Model artifacts live beside the pipeline code in this repository.
MODEL_DIR = os.path.join(os.path.dirname(__file__), "ml")
TOPIC_MODEL_PATH = os.path.join(MODEL_DIR, "topic_model.joblib")
SENTIMENT_MODEL_PATH = os.path.join(MODEL_DIR, "sentiment_model.joblib")

# Biến global lưu model để tránh load lại nhiều lần
_topic_model = None
_sentiment_model = None

def load_models():
    """Tải model vào bộ nhớ nếu file tồn tại"""
    global _topic_model, _sentiment_model
    try:
        if os.path.exists(TOPIC_MODEL_PATH):
            _topic_model = joblib.load(TOPIC_MODEL_PATH)
        if os.path.exists(SENTIMENT_MODEL_PATH):
            _sentiment_model = joblib.load(SENTIMENT_MODEL_PATH)
    except Exception as e:
        print(f"Warning: Không thể load models: {e}")

def apply_safety_rules(text: str, current_topic: str, current_severity: int, current_confidence: float):
    """
    Rule-based khẩn cấp: Bắt các keyword nguy hiểm.
    Trả về (is_modified, new_topic, new_severity, new_confidence)
    """
    text_lower = text.lower()
    safety_keywords = ["tai nạn", "đụng xe", "tài xế say", "cướp", "đánh nhau", "sàm sỡ", "quấy rối"]
    
    for kw in safety_keywords:
        if kw in text_lower:
            # Phát hiện từ khoá nguy hiểm -> Ép mức độ nghiêm trọng lên 5 (Cao nhất)
            # Và giảm confidence xuống để yêu cầu nhân viên (Human) vào Review lại
            return True, "Safety", 5, 0.3
            
    return False, current_topic, current_severity, current_confidence

def predict_feedback(text: str):
    """
    Hàm dự đoán chính. 
    Chạy Model (nếu có) -> Chạy Rule-based -> Trả về kết quả cuối cùng.
    """
    # 1. Chạy AI Model (Giả lập kết quả nếu chưa có file .joblib)
    topic = "General"
    sentiment = "Neutral"
    severity = 3
    confidence = 0.85
    
    if _topic_model and _sentiment_model:
        # TODO: Code thực tế khi có file .joblib (vd: topic = _topic_model.predict([text])[0])
        pass
    else:
        # Giả lập AI đơn giản dựa trên độ dài (Tạm thời)
        if len(text) > 100:
            sentiment = "Negative"
            severity = 4
        
    # 2. Chạy Rule-based ghi đè (Safety Override)
    is_modified, rule_topic, rule_severity, rule_confidence = apply_safety_rules(text, topic, severity, confidence)
    if is_modified:
        topic = rule_topic
        severity = rule_severity
        confidence = rule_confidence
        sentiment = "Negative"
        
    return {
        "topic": topic,
        "sentiment": sentiment,
        "severity": severity,
        "confidence": confidence
    }

# Khởi tạo model ngay khi module được import
load_models()
