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

# Mức độ nghiêm trọng suy ra từ sentiment khi model không tự sinh severity.
# Thang P1..P5, P5 = nghiêm trọng nhất (theo blueprint).
SENTIMENT_SEVERITY = {"negative": 4, "neutral": 3, "positive": 1}

# Từ khoá an toàn — bất kỳ phản hồi nào chứa các từ này bị ép Safety/severity 5
# và hạ confidence để buộc Human-in-the-Loop review lại.
SAFETY_KEYWORDS = ["tai nạn", "đụng xe", "tài xế say", "cướp", "đánh nhau", "sàm sỡ", "quấy rối"]


def apply_safety_rules(text: str, current_topic: str, current_severity: int, current_confidence: float):
    """
    Rule-based khẩn cấp: Bắt các keyword nguy hiểm.
    Trả về (is_modified, new_topic, new_severity, new_confidence)
    """
    text_lower = text.lower()
    for kw in SAFETY_KEYWORDS:
        if kw in text_lower:
            # Phát hiện từ khoá nguy hiểm -> Ép mức độ nghiêm trọng lên 5 (Cao nhất)
            # Và giảm confidence xuống để yêu cầu nhân viên (Human) vào Review lại
            return True, "Safety", 5, 0.3

    return False, current_topic, current_severity, current_confidence


def _model_confidence(model, text: str, default: float = 0.85) -> float:
    """LinearSVC không có predict_proba; ước lượng độ tin cậy từ decision_function margin."""
    try:
        import numpy as np

        scores = model.decision_function([text])[0]
        scores = np.atleast_1d(scores)
        if scores.size == 1:
            margin = abs(float(scores[0]))
        else:
            ordered = np.sort(scores)[::-1]
            margin = float(ordered[0] - ordered[1])
        # Squash margin (0..~3) về khoảng (0.5..0.99) bằng logistic đơn giản.
        confidence = 1.0 / (1.0 + np.exp(-margin))
        return round(float(confidence), 3)
    except Exception:
        return default


def predict_feedback(text: str):
    """
    Hàm dự đoán chính.
    Chạy Model (TF-IDF + LinearSVC) -> Rule-based Safety override -> kết quả cuối.
    Nếu model chưa load được thì fallback an toàn (không làm vỡ pipeline ingest).
    """
    if _topic_model is not None and _sentiment_model is not None:
        topic = str(_topic_model.predict([text])[0])
        sentiment = str(_sentiment_model.predict([text])[0])
        severity = SENTIMENT_SEVERITY.get(sentiment, 3)
        # Confidence lấy theo model topic (quyết định routing) — đủ cho demo HITL.
        confidence = _model_confidence(_topic_model, text)
    else:
        # Fallback khi thiếu artifact: nhãn trung tính, đánh dấu cần review.
        print("Warning: classifier chạy fallback vì chưa load được model .joblib")
        topic = "Other"
        sentiment = "neutral"
        severity = 3
        confidence = 0.3

    # Rule-based ghi đè (Safety Override) — luôn thắng model.
    is_modified, rule_topic, rule_severity, rule_confidence = apply_safety_rules(
        text, topic, severity, confidence
    )
    if is_modified:
        topic = rule_topic
        severity = rule_severity
        confidence = rule_confidence
        sentiment = "negative"

    return {
        "topic": topic,
        "sentiment": sentiment,
        "severity": severity,
        "confidence": confidence,
    }

# Khởi tạo model ngay khi module được import
load_models()
