"""Rule layer cho classifier — chạy SAU model ML, ghi đè khi keyword rõ.

Triết lý:
- Model ML (TF-IDF + LinearSVC) cho dự đoán nền.
- Rule keyword ghi đè khi có tín hiệu MẠNH và RÕ (an toàn, supply, app, payment...).
- Confidence phản ánh độ chắc thật: rule mạnh cao, mâu thuẫn/ngắn/mơ hồ thì thấp.
- needs_review = true khi: severity cao (P4/P5), confidence thấp, hoặc safety override.

Mọi keyword đều so trên text đã lower. Có xử lý phủ định cơ bản tiếng Việt
("không", "ko", "chẳng", "chưa") để tránh gán sai ví dụ "app không thân thiện".
"""

from __future__ import annotations

# Ngưỡng confidence dưới mức này -> cần người duyệt (model rất không chắc).
REVIEW_CONFIDENCE_THRESHOLD = 0.55

# Severity (số) từ mức này trở lên -> cần người duyệt dù confidence cao.
# Chỉ P5 (nguy hiểm) tự động vào Review Queue; P4 chỉ vào nếu confidence thấp.
REVIEW_SEVERITY_THRESHOLD = 5

NEGATIONS = ["không", "ko", "k ", "chẳng", "chưa", "đừng", "chả"]

# --- Nhóm keyword theo topic. Thứ tự ưu tiên: Safety > Payment > App > Supply > Driver > Pricing > Delay ---

SAFETY_KEYWORDS = [
    "tai nạn", "tai nan", "xe tông", "xe tong", "đụng xe", "dung xe", "tông",
    "bỏ chạy", "bo chay", "say xỉn", "say xin", "say rượu", "cướp", "cuop",
    "đánh nhau", "danh nhau", "hành hung", "hanh hung", "sàm sỡ", "sam so",
    "quấy rối", "quay roi", "đe doạ", "đe dọa", "de doa", "nguy hiểm", "nguy hiem",
    "hăm doạ", "ham doa", "bạo lực", "bao luc", "sờ soạng", "quấy rầy",
]

# Gian lận / mất tiền -> Payment, nghiêm trọng (có thể cần duyệt).
PAYMENT_FRAUD_KEYWORDS = [
    "mất tiền", "mat tien", "gian lận", "gian lan", "lừa đảo", "lua dao",
    "bịp", "bip", "trừ tiền", "tru tien", "tự trừ", "tu tru", "lừa", "chặt chém",
    "thu thêm", "thu them", "tính sai tiền", "ăn chặn", "an chan",
]

PAYMENT_KEYWORDS = [
    "thanh toán", "thanh toan", "hoá đơn", "hoa don", "hóa đơn", "ví", "momo",
    "chuyển khoản", "chuyen khoan", "hoàn tiền", "hoan tien", "phí", "cước",
]

APP_KEYWORDS = [
    "app văng", "app vang", "văng ra", "vang ra", "thoát ứng dụng", "thoat ung dung",
    "tự thoát", "tu thoat", "crash", "đơ", "lag", "treo", "lỗi app", "loi app",
    "không cập nhật", "khong cap nhat", "ko cập nhật", "cập nhật xong", "đăng nhập",
    "dang nhap", "load", "tải lại", "bị lỗi", "bi loi", "ứng dụng lỗi", "giao diện",
]

MAP_KEYWORDS = [
    "bản đồ", "ban do", "ghim vị trí", "ghim vi tri", "định vị", "dinh vi",
    "google map", "google maps", "chỉ đường", "chi duong", "sai đường", "sai duong",
    "sai vị trí", "sai vi tri", "gps", "bản đồ sai", "map sai", "đi sai đường",
]

# Tài xế thiếu cuốc / supply.
SUPPLY_KEYWORDS = [
    "không nổ cuốc", "khong no cuoc", "ko nổ cuốc", "không có đơn", "khong co don",
    "ko có đơn", "không có cuốc", "không phát chuyến", "khong phat chuyen",
    "không nhận được cuốc", "ít đơn", "it don", "không có khách", "khong co khach",
    "4 tiếng 4 đơn", "không có cuốc nào", " ế ", "vắng khách", "không nổ cuốc nào",
]

# Hành vi tài xế TÍCH CỰC.
DRIVER_POSITIVE_KEYWORDS = [
    "tài xế thân thiện", "tai xe than thien", "tài xế nhiệt tình", "tai xe nhiet tinh",
    "bác tài tốt", "bac tai tot", "tài xế tốt", "lái xe lịch sự", "lai xe lich su",
    "tài xế vui vẻ", "tai xe vui ve", "tài xế lịch sự", "tài xế dễ thương",
    "tài xế chu đáo", "bác tài nhiệt tình", "tài xế hoà nhã", "thân thiện nhiệt tình",
    "tài xế ân cần", "tài xế nhiệt huyết",
]

# Hành vi tài xế TIÊU CỰC.
DRIVER_NEGATIVE_KEYWORDS = [
    "tài xế thái độ", "thái độ tài xế", "tài xế hỗn", "tài xế cộc", "tài xế chửi",
    "tài xế quát", "tài xế khó chịu", "lái ẩu", "lai au", "chạy ẩu", "chay au",
    "tài xế trễ", "tài xế đến muộn", "huỷ chuyến", "hủy chuyến", "huy chuyen",
    "tài xế hủy", "tài xế từ chối", "phóng nhanh", "vượt ẩu", "vuot au",
]

PRICING_KEYWORDS = [
    "giá đắt", "gia dat", "giá cao", "đắt quá", "dat qua", "chặt chém giá",
    "giá cước cao", "tăng giá", "tang gia", "phụ phí", "phu phi", "giá ảo",
]

DELAY_KEYWORDS = [
    "chờ lâu", "cho lau", "đợi lâu", "doi lau", "đến muộn", "den muon", "trễ giờ",
    "tre gio", "chậm", "lâu quá", "đợi mãi", "chờ mãi",
]

# Cụm tích cực chung (không gắn topic cụ thể).
POSITIVE_KEYWORDS = [
    "tuyệt vời", "tuyet voi", "rất tốt", "rat tot", "hài lòng", "hai long",
    "tốt", "ổn", "ok", "cảm ơn", "cam on", "5 sao", "tuyệt", "hay", "thích",
    "ưng", "đáng tiền", "recommend", "sẽ dùng tiếp", "dùng tiếp", "tốt lắm",
    "không có vấn đề", "ko có vấn đề", "chưa gặp vấn đề", "ổn định", "ngon",
]

# Cụm tiêu cực chung (chê / bực / slang / chửi) — rất phổ biến ở review ngắn.
# Bắt các câu như "app chán", "quá tệ", "cskh tệ", "đắt cc" để KHÔNG dồn
# nhầm vào Review Queue dưới nhãn "câu ngắn/mơ hồ".
NEGATIVE_KEYWORDS = [
    "tệ", "kém", "chán", "dở", "tồi", "ngu", "đểu", "cùi", "lởm", "lỏ", "lol",
    "loz", "lz", "lol", "cc", "đm", "vl", "vcl", "rác", "thất vọng", "bực",
    "khó chịu", "phiền", "bức xúc", "chậm", "lâu", "không hài lòng",
    "ko hài lòng", "chả ra gì", "vô dụng", "vô lý", "bịp", "lừa", "như lol",
    "như cc", "quá kém", "quá tệ", "tệ hại", "thậm tệ", "kinh khủng",
]


def _has(text: str, keywords: list[str]) -> str | None:
    for kw in keywords:
        if kw in text:
            return kw
    return None


def _negated_near(text: str, keyword: str, window: int = 12) -> bool:
    """Kiểm có từ phủ định ngay TRƯỚC keyword trong cửa sổ ký tự không.

    Ví dụ 'app không thân thiện' -> 'thân thiện' bị phủ định.
    """
    idx = text.find(keyword)
    if idx == -1:
        return False
    prefix = text[max(0, idx - window):idx]
    return any(neg in prefix for neg in NEGATIONS)


def _sev_to_int(severity) -> int:
    if isinstance(severity, int):
        return severity
    try:
        return int(str(severity).upper().lstrip("P"))
    except (ValueError, AttributeError):
        return 3


def apply_rules(text: str, model_topic: str, model_sentiment: str,
                model_severity: int, model_confidence: float) -> dict:
    """Ghi đè kết quả model bằng rule keyword khi tín hiệu rõ.

    Trả về dict: topic, sentiment, severity (int), confidence (0..1),
    needs_review (bool), review_reason (str|None).
    """
    t = text.lower().strip()
    topic = model_topic
    sentiment = model_sentiment
    severity = _sev_to_int(model_severity)
    confidence = model_confidence
    matched_rule = False
    review_reason = None

    # --- 1. SAFETY (ưu tiên cao nhất) ---
    kw = _has(t, SAFETY_KEYWORDS)
    if kw:
        topic, sentiment, severity = "Safety", "negative", 5
        confidence = 0.55  # nghiêm trọng nhưng chưa chắc tuyệt đối -> vẫn buộc duyệt
        matched_rule = True
        review_reason = f"Từ khoá an toàn: '{kw}'"
        return _finalize(topic, sentiment, severity, confidence, review_reason, force_review=True)

    # --- 2. DRIVER tích cực (tín hiệu rõ, ưu tiên cao, có negation guard) ---
    kw = _has(t, DRIVER_POSITIVE_KEYWORDS)
    if kw and not _negated_near(t, kw):
        topic, sentiment, severity = "Driver Behavior", "positive", 1
        confidence = 0.88
        return _finalize(topic, sentiment, severity, confidence, None)

    # --- 3. PAYMENT FRAUD / mất tiền ---
    kw = _has(t, PAYMENT_FRAUD_KEYWORDS)
    if kw:
        topic, sentiment = "Payment", "negative"
        severity = max(severity, 4)
        confidence = 0.8
        matched_rule = True
        review_reason = f"Nghi gian lận/mất tiền: '{kw}'"

    # --- 3. APP issue ---
    if not matched_rule:
        kw = _has(t, APP_KEYWORDS)
        if kw:
            topic, sentiment = "App Issue", "negative"
            severity = max(severity, 3)
            confidence = 0.82
            matched_rule = True

    # --- 4. MAP/Navigation -> App Issue (không có topic Map riêng trong model) ---
    if not matched_rule:
        kw = _has(t, MAP_KEYWORDS)
        if kw:
            topic = "App Issue"
            sentiment = "negative" if sentiment != "positive" else "neutral"
            severity = max(severity, 3)
            confidence = 0.78
            matched_rule = True

    # --- 5. PAYMENT thường ---
    if not matched_rule:
        kw = _has(t, PAYMENT_KEYWORDS)
        if kw:
            topic = "Payment"
            severity = max(severity, 3)
            confidence = 0.75
            matched_rule = True

    # --- 6. SUPPLY (tài xế thiếu cuốc) ---
    if not matched_rule:
        kw = _has(t, SUPPLY_KEYWORDS)
        if kw:
            topic, sentiment = "Other", "negative"  # không có Driver Supply trong model -> Other
            severity = max(severity, 3)
            confidence = 0.72
            matched_rule = True
            review_reason = "Tài xế thiếu cuốc (supply)"

    # --- 7. DRIVER tiêu cực ---
    if not matched_rule:
        kw = _has(t, DRIVER_NEGATIVE_KEYWORDS)
        if kw:
            topic, sentiment = "Driver Behavior", "negative"
            severity = max(severity, 3)
            confidence = 0.8
            matched_rule = True

    # --- 9. PRICING ---
    if not matched_rule:
        kw = _has(t, PRICING_KEYWORDS)
        if kw:
            topic, sentiment = "Pricing", "negative"
            severity = max(severity, 3)
            confidence = 0.76
            matched_rule = True

    # --- 10. DELAY ---
    if not matched_rule:
        kw = _has(t, DELAY_KEYWORDS)
        if kw:
            topic, sentiment = "Delay", "negative"
            severity = max(severity, 3)
            confidence = 0.74
            matched_rule = True

    # --- 11. POSITIVE chung (có negation guard) ---
    if not matched_rule:
        kw = _has(t, POSITIVE_KEYWORDS)
        if kw and not _negated_near(t, kw):
            sentiment, severity = "positive", 1
            confidence = max(confidence, 0.78)
            matched_rule = True

    # --- 12. NEGATIVE chung (chê/slang/chửi) — bắt review ngắn rõ nghĩa ---
    if not matched_rule:
        kw = _has(t, NEGATIVE_KEYWORDS)
        if kw and not _negated_near(t, kw):
            sentiment = "negative"
            severity = max(severity, 3)
            confidence = max(confidence, 0.72)
            matched_rule = True

    # --- Câu thật sự vô nghĩa / gibberish: mới cần duyệt ---
    # Chỉ đánh dấu khi câu ngắn VÀ không match rule nào VÀ trông như gõ ngẫu nhiên
    # (ít chữ cái tiếng Việt, nhiều ký tự lặp). Câu ngắn rõ nghĩa đã được rule trên bắt.
    word_count = len(t.split())
    if word_count <= 3 and not matched_rule and _looks_gibberish(t):
        confidence = min(confidence, 0.5)
        review_reason = review_reason or "Câu quá ngắn/khó hiểu"

    return _finalize(topic, sentiment, severity, confidence, review_reason)


def _looks_gibberish(t: str) -> bool:
    """Đoán câu vô nghĩa: bỏ dấu cách, nếu phần lớn KHÔNG phải nguyên âm
    tiếng Việt thông thường hoặc lặp ký tự bất thường thì coi là khó hiểu.
    Heuristic nhẹ — chỉ để lọc 'Hnh Hnh Hhigvv' kiểu OCR/gõ ẩu."""
    compact = t.replace(" ", "")
    if not compact:
        return True
    vowels = sum(1 for c in compact if c in "aàáảãạăằắẳẵặâầấẩẫậeèéẻẽẹêềếểễệiìíỉĩịoòóỏõọôồốổỗộơờớởỡợuùúủũụưừứửữựyỳýỷỹỵ")
    # Tỷ lệ nguyên âm quá thấp -> chuỗi phụ âm bất thường -> nhiều khả năng gibberish.
    return (vowels / len(compact)) < 0.2


def _finalize(topic, sentiment, severity, confidence, review_reason, force_review=False):
    needs_review = force_review
    if confidence < REVIEW_CONFIDENCE_THRESHOLD:
        needs_review = True
        review_reason = review_reason or f"Confidence thấp ({round(confidence * 100)}%)"
    if severity >= REVIEW_SEVERITY_THRESHOLD:
        needs_review = True
        review_reason = review_reason or f"Mức nghiêm trọng P{severity}"
    return {
        "topic": topic,
        "sentiment": sentiment,
        "severity": severity,
        "confidence": round(float(confidence), 3),
        "needs_review": needs_review,
        "review_reason": review_reason,
    }
