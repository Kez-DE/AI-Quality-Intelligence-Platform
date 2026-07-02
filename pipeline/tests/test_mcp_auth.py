"""Test auth token→identity resolve LIVE từ profiles (theo user_id)."""
import pytest

import mcp_auth as a


class _Exec:
    def __init__(self, data): self.data = data


class _Query:
    def __init__(self, rows): self._rows = rows
    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def update(self, *a, **k): return self
    def insert(self, row, *a, **k):
        self._captured = row
        return self
    def execute(self): return _Exec(self._rows)


class _DB:
    """Fake trả rows khác nhau theo tên bảng."""
    def __init__(self, by_table): self._by = by_table; self.last = {}
    def table(self, name):
        q = _Query(self._by.get(name, []))
        self.last[name] = q
        return q


def _db(token_rows, profile_rows):
    return _DB({"mcp_tokens": token_rows, "profiles": profile_rows})


def test_hash_deterministic():
    assert a.hash_token("abc") == a.hash_token("abc") != a.hash_token("abd")


def test_admin_profile_is_system_wide():
    db = _db([{"id": "t1", "user_id": "u1"}], [{"role": "admin", "department": None}])
    assert a.verify_token("raw", db=db) == {"role": "admin", "scope_team": None}


def test_staff_with_department_is_scoped():
    db = _db([{"id": "t1", "user_id": "u1"}], [{"role": "staff", "department": "CSKH"}])
    assert a.verify_token("raw", db=db) == {"role": "staff", "scope_team": "CSKH"}


def test_staff_without_department_downgrades_to_guest():
    # nhân viên chưa được admin gán phòng → chỉ submit_feedback, KHÔNG toàn hệ thống
    db = _db([{"id": "t1", "user_id": "u1"}], [{"role": "staff", "department": None}])
    assert a.verify_token("raw", db=db) == {"role": "guest", "scope_team": None}


def test_guest_profile_only_submit():
    db = _db([{"id": "t1", "user_id": "u1"}], [{"role": "guest", "department": None}])
    assert a.verify_token("raw", db=db) == {"role": "guest", "scope_team": None}


def test_unknown_token_returns_none():
    assert a.verify_token("nope", db=_db([], [])) is None


def test_token_without_owner_returns_none():
    assert a.verify_token("orphan", db=_db([{"id": "t1", "user_id": None}], [])) is None


def test_missing_profile_returns_none():
    db = _db([{"id": "t1", "user_id": "ghost"}], [])
    assert a.verify_token("raw", db=db) is None


def test_issue_requires_user_id():
    with pytest.raises(ValueError):
        a.issue_token("", db=_db([], []))


def test_issue_stores_user_id():
    db = _db([], [])
    raw = a.issue_token("u1", label="self:a@b.c", db=db)
    assert isinstance(raw, str) and len(raw) > 20
    assert db.last["mcp_tokens"]._captured["user_id"] == "u1"
