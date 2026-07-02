"""Test auth token→identity: hash, verify (fake db), issue validation."""
import pytest

import mcp_auth as a


class _FakeExec:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    """Fake chain của supabase-py cho mcp_tokens."""
    def __init__(self, rows):
        self._rows = rows

    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def update(self, *a, **k): return self
    def insert(self, *a, **k): return self
    def execute(self): return _FakeExec(self._rows)


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows
    def table(self, name): return _FakeQuery(self._rows)


def test_hash_is_deterministic_and_hex():
    h1 = a.hash_token("abc")
    h2 = a.hash_token("abc")
    assert h1 == h2 and len(h1) == 64
    assert a.hash_token("abc") != a.hash_token("abd")


def test_verify_valid_token_returns_identity():
    db = _FakeDB([{"id": "1", "role": "manager", "scope_team": "CSKH", "active": True}])
    ident = a.verify_token("rawtoken", db=db)
    assert ident == {"role": "manager", "scope_team": "CSKH"}


def test_verify_unknown_token_returns_none():
    db = _FakeDB([])
    assert a.verify_token("nope", db=db) is None


def test_verify_empty_token_returns_none():
    assert a.verify_token("", db=_FakeDB([])) is None


def test_issue_requires_scope_for_ops():
    with pytest.raises(ValueError):
        a.issue_token("staff", None, db=_FakeDB([]))


def test_issue_admin_forces_scope_none():
    captured = {}

    class _CapDB(_FakeDB):
        def table(self, name):
            outer = self
            class Q(_FakeQuery):
                def insert(self, row, *a, **k):
                    captured.update(row)
                    return self
            return Q(outer._rows)

    raw = a.issue_token("admin", "CSKH", label="x", db=_CapDB([]))
    assert isinstance(raw, str) and len(raw) > 20
    assert captured["scope_team"] is None  # admin ép scope=None dù truyền CSKH
    assert captured["role"] == "admin"
