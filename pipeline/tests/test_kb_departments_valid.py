"""Mọi tài liệu KB được index PHẢI gắn department thuộc 6 phòng ban — nếu không,
search_knowledge (lọc đúng department) sẽ không bao giờ trả về tài liệu đó cho ops."""
import os

from departments import DEPARTMENTS

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
KB_DIR = os.path.join(REPO, "data", "knowledge_base")


def _department_of(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s.lower().startswith("department:"):
                return s.split(":", 1)[1].strip()
    return None


def test_every_indexed_kb_doc_has_valid_department():
    bad = []
    for root, _dirs, files in os.walk(KB_DIR):
        for fname in files:
            if not fname.endswith(".md") or fname == "README.md":  # loader bỏ README
                continue
            dep = _department_of(os.path.join(root, fname))
            if dep not in DEPARTMENTS:
                bad.append((fname, dep))
    assert not bad, f"KB doc gắn phòng ban không hợp lệ (không thuộc 6 phòng): {bad}"
