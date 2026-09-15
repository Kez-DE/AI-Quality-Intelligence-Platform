import re
from datetime import datetime, timedelta, timezone
from typing import Any

_DEFAULT = timedelta(hours=48)

# Từ chỉ đơn vị thời gian mà LLM hay dùng, quy về token parse_deadline hiểu được.
_DEADLINE_UNITS = {
    "h": "h", "gio": "h", "giờ": "h", "tieng": "h", "tiếng": "h",
    "hour": "h", "hours": "h", "hr": "h",
    "d": "d", "ngay": "d", "ngày": "d", "day": "d", "days": "d",
    "w": "w", "tuan": "w", "tuần": "w", "week": "w", "weeks": "w",
    "thang": "mo", "tháng": "mo", "month": "mo", "months": "mo",
}


def normalize_deadline(raw: Any, default: str = "48h") -> str:
    """Quy thời hạn tự do về token chuẩn ('24h' / '7d' / '2w').

    Chuẩn hoá ở nơi SINH ra thời hạn (tác tử phân tích), không phải ở cổng duyệt.
    Lý do: ở khâu sinh, một giá trị mặc định là trung thực vì chưa ai cam kết gì;
    ở cổng duyệt thì thời hạn là ý chí của người duyệt, âm thầm thay nó bằng mặc
    định sẽ làm văn bản báo cáo và hạn thật của công việc lệch nhau.
    """
    if raw is None:
        return default
    text = str(raw).strip().lower()
    if re.fullmatch(r"\s*\d{1,4}\s*[hdw]\s*", text):
        return text.replace(" ", "")
    match = re.search(r"(\d{1,4})\s*([^\W\d_]+)", text, flags=re.UNICODE)
    if not match:
        return default
    amount, word = match.group(1), match.group(2)
    unit = _DEADLINE_UNITS.get(word)
    if unit is None:
        return default
    if unit == "mo":                      # tháng -> tuần, chặn trần cho an toàn
        return f"{min(int(amount) * 4, 9999)}w"
    return f"{amount}{unit}"


def parse_deadline(deadline: str | None) -> datetime:
    """Đổi token '1h'/'24h'/'7d'/'1w' thành thời điểm tuyệt đối. Không khớp -> +48h."""
    now = datetime.now(timezone.utc)
    if not deadline:
        return now + _DEFAULT
    # str() thay vì .strip() thẳng: payload có thể mang số/dict, và AttributeError ở đây
    # nổ ra ngoài try của endpoint -> 500 thay vì lỗi validate.
    m = re.fullmatch(r"\s*(\d+)\s*([hdw])\s*", str(deadline).strip().lower())
    if not m:
        return now + _DEFAULT
    n, unit = int(m.group(1)), m.group(2)
    if unit == "h":
        return now + timedelta(hours=n)
    if unit == "d":
        return now + timedelta(days=n)
    return now + timedelta(weeks=n)
