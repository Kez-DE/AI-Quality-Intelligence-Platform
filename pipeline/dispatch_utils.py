import re
from datetime import datetime, timedelta, timezone

_DEFAULT = timedelta(hours=48)


def parse_deadline(deadline: str | None) -> datetime:
    """Đổi token '1h'/'24h'/'7d'/'1w' thành thời điểm tuyệt đối. Không khớp -> +48h."""
    now = datetime.now(timezone.utc)
    if not deadline:
        return now + _DEFAULT
    m = re.fullmatch(r"\s*(\d+)\s*([hdw])\s*", deadline.strip().lower())
    if not m:
        return now + _DEFAULT
    n, unit = int(m.group(1)), m.group(2)
    if unit == "h":
        return now + timedelta(hours=n)
    if unit == "d":
        return now + timedelta(days=n)
    return now + timedelta(weeks=n)
