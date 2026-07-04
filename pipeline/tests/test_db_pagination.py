"""fetch_paginated vượt cap 1000/response của PostgREST (mô phỏng bằng .range)."""
from db_utils import fetch_paginated
from tests._fakedb import FakeDB


def _rows(n):
    return [{"id": f"r{i}", "created_at": f"2026-01-01T00:00:{i:04d}"} for i in range(n)]


def test_fetch_all_beyond_single_page():
    # 2500 dòng, page 1000 → phải lấy đủ 2500 (không dừng ở 1000 như .limit bị cap).
    db = FakeDB(feedback=_rows(2500))
    got = fetch_paginated(lambda: db.table("feedback").select("*"), page_size=1000)
    assert len(got) == 2500
    assert len({r["id"] for r in got}) == 2500  # không trùng


def test_cap_stops_early():
    db = FakeDB(feedback=_rows(2500))
    got = fetch_paginated(lambda: db.table("feedback").select("*"), cap=1500, page_size=1000)
    assert len(got) == 1500


def test_empty():
    db = FakeDB(feedback=[])
    assert fetch_paginated(lambda: db.table("feedback").select("*")) == []
