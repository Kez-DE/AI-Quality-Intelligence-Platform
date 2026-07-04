"""Duyệt (approved) báo cáo hoàn thành → task resolved → resolve luôn ticket liên kết."""
import types
import main


def test_approve_calls_resolve_alerts(monkeypatch):
    calls = {}
    monkeypatch.setattr(main, "_resolve_alerts_for_task",
                        lambda db, task_id, actor: calls.setdefault("resolved_task", task_id))

    class _Q:
        def __init__(self, rows): self._rows = rows
        def select(self, *a, **k): return self
        def update(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def limit(self, *a, **k): return self
        def execute(self):
            class R: pass
            R.data = self._rows
            return R
    class _DB:
        def table(self, name):
            if name == "task_completion_reports":
                return _Q([{"team": "CSKH", "task_id": "task-9"}])
            if name == "tasks":
                return _Q([{"status": "pending_review"}])
            return _Q([])
    monkeypatch.setattr(main, "get_supabase", lambda: _DB())
    monkeypatch.setattr(main, "can_view_team", lambda user, team: True)

    user = types.SimpleNamespace(id="u1", email="e", role="manager", department="CSKH")
    payload = types.SimpleNamespace(status="approved", review_note="ok")
    main.review_completion_report("rep-1", payload, user)
    assert calls.get("resolved_task") == "task-9"


def test_reject_does_not_resolve_alerts(monkeypatch):
    calls = {}
    monkeypatch.setattr(main, "_resolve_alerts_for_task",
                        lambda db, task_id, actor: calls.setdefault("resolved_task", task_id))

    class _Q:
        def __init__(self, rows): self._rows = rows
        def select(self, *a, **k): return self
        def update(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def limit(self, *a, **k): return self
        def execute(self):
            class R: pass
            R.data = self._rows
            return R
    class _DB:
        def table(self, name):
            if name == "task_completion_reports":
                return _Q([{"team": "CSKH", "task_id": "task-9"}])
            if name == "tasks":
                return _Q([{"status": "pending_review"}])
            return _Q([])
    monkeypatch.setattr(main, "get_supabase", lambda: _DB())
    monkeypatch.setattr(main, "can_view_team", lambda user, team: True)

    user = types.SimpleNamespace(id="u1", email="e", role="manager", department="CSKH")
    payload = types.SimpleNamespace(status="rejected", review_note="làm lại")
    main.review_completion_report("rep-1", payload, user)
    assert "resolved_task" not in calls
