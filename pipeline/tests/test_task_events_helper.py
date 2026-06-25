import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from _fakedb import FakeDB
from auth_guard import AuthUser
import main


def _actor():
    return AuthUser(id="u1", email="a@x.com", role="manager", department="IT")


def test_log_task_event_writes_row():
    db = FakeDB(task_events=[])
    main._log_task_event(
        db, task_id="t1", actor=_actor(), team="IT", action="assigned",
        from_status="open", to_status="assigned",
    )
    rows = db.tables["task_events"]
    assert len(rows) == 1
    assert rows[0]["action"] == "assigned"
    assert rows[0]["actor_id"] == "u1"
    assert rows[0]["actor_role"] == "manager"
    assert rows[0]["from_status"] == "open"
    assert rows[0]["to_status"] == "assigned"


def test_log_task_event_never_raises(monkeypatch):
    class Boom:
        def table(self, *_):
            raise RuntimeError("db down")
    # Không được ném lỗi ra ngoài (audit là phụ trợ).
    main._log_task_event(
        Boom(), task_id="t1", actor=_actor(), team="IT", action="accepted",
    )
