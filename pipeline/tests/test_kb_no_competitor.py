"""Guardrail: KB chỉ chứa nguồn/liên hệ xanhSM (greensm); KHÔNG có Be/Grab.

Số liệu và liên hệ của đối thủ tuyệt đối không được lọt vào KB xanhSM.
"""
import re
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"
KB_DIRS = [DATA / "knowledge_base", DATA / "public_kb"]
BANNED = re.compile(r"be\.com\.vn|grab\.com|help\.grab|gojek", re.I)


def _md_files():
    for d in KB_DIRS:
        if d.exists():
            yield from d.rglob("*.md")


def test_no_competitor_domain_in_kb():
    bad = [str(f) for f in _md_files() if BANNED.search(f.read_text(encoding="utf-8"))]
    assert not bad, f"KB chứa tên miền/đối thủ competitor: {bad}"


def test_kb_has_files():
    assert any(_md_files()), "KB rỗng?"
