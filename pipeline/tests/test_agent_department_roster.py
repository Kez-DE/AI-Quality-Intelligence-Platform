"""build_agent_data_context phải chứa roster 6 phòng; admin có đếm per-phòng; guest không dính."""
import types

from services.agent_context import build_agent_data_context, GUEST_SYSTEM_PROMPT
from departments import DEPARTMENTS


def _user(role, department=None):
    return types.SimpleNamespace(role=role, department=department, id="u1", email="a@b.c")


def test_admin_context_has_full_roster():
    ctx = build_agent_data_context(_user("admin"))
    assert f"({len(DEPARTMENTS)})" in ctx or str(len(DEPARTMENTS)) in ctx
    for d in DEPARTMENTS:
        assert d in ctx, f"thiếu phòng {d} trong context admin"


class _Exec:
    def __init__(self, data):
        self.data = data


class _Table:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return _Exec(self._rows)


class _FakeDB:
    """Fake Supabase: feedback có sẵn để route ra phòng; alerts rỗng."""
    def table(self, name):
        if name == "feedback":
            return _Table([
                {"topic": "Payment", "severity": 3, "sentiment": "negative",
                 "area": "HN", "created_at": "2026-07-01"},
                {"topic": "Safety", "severity": 5, "sentiment": "negative",
                 "area": "HN", "created_at": "2026-07-01"},
            ])
        return _Table([])


def test_admin_context_has_per_department_feedback_line(monkeypatch):
    # Mock Supabase để không phụ thuộc DB thật (chạy được cả trong CI).
    import services.agent_context as ac
    monkeypatch.setattr(ac, "get_supabase", lambda: _FakeDB())
    ctx = ac.build_agent_data_context(_user("admin"))
    assert "Feedback theo phòng" in ctx


def test_staff_with_dept_sees_roster_names_not_other_dept_counts():
    ctx = build_agent_data_context(_user("staff", "CSKH"))
    for d in DEPARTMENTS:
        assert d in ctx                       # roster tên: có
    assert "Feedback theo phòng" not in ctx   # đếm per-phòng: KHÔNG (chỉ admin)


def test_staff_without_dept_unchanged():
    ctx = build_agent_data_context(_user("staff", None))
    assert "chưa" in ctx.lower()              # giữ thông báo chưa có phạm vi


def test_guest_prompt_has_no_roster():
    for d in DEPARTMENTS:
        assert d not in GUEST_SYSTEM_PROMPT
