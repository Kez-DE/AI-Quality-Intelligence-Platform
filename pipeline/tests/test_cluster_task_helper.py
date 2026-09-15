"""Hợp đồng gom cụm alert -> task (agents/task_agent.py).

Mỗi test ở đây khoá một quy tắc đã từng sai trong production, xem docstring task_agent.
"""
import agents.task_agent as task_agent
from agents.task_agent import (
    alert_priority,
    cluster_alerts_into_tasks,
    escalate_task_priority,
    fallback_cluster_title,
    find_or_create_cluster_task,
    priority_rank,
)
from _fakedb import FakeDB


def _task(**over):
    row = {
        "id": "t-1", "assigned_team": "CSKH", "area": "HN-Cau-Giay", "topic": "Other",
        "priority": "P2", "status": "open", "due_at": None,
    }
    row.update(over)
    return row


def _alert(**over):
    row = {
        "id": "a-1", "title": "Sự cố", "description": "", "area": "HN-Cau-Giay",
        "topic": "Other", "priority": "P3", "severity": "P3", "status": "open",
        "assigned_team": "CSKH", "task_id": None,
    }
    row.update(over)
    return row


# ── find_or_create_cluster_task ─────────────────────────────────────────────

def test_reuse_task_of_same_cluster():
    db = FakeDB(tasks=[_task()])
    tid = find_or_create_cluster_task(db, "CSKH", "HN-Cau-Giay", "P3", "X", topic="Other")
    assert tid == "t-1"
    assert len(db.tables["tasks"]) == 1  # không insert thêm


def test_creates_when_no_task_for_cluster():
    db = FakeDB(tasks=[])
    tid = find_or_create_cluster_task(db, "CSKH", "HN-Cau-Giay", "P3", "X", topic="Delay")
    row = db.tables["tasks"][0]
    assert tid == row["id"]
    assert row["assigned_team"] == "CSKH" and row["status"] == "open"
    assert row["source"] == "agent"
    assert row["topic"] == "Delay"          # không còn hardcode 'General'
    assert row["due_at"]                    # task agent-sinh phải có SLA


def test_different_topic_same_area_gets_its_own_task():
    """Safety P5 không được nuốt vào task Delay cùng khu vực."""
    db = FakeDB(tasks=[_task(topic="Delay", assigned_team="Vận hành")])
    tid = find_or_create_cluster_task(
        db, "Vận hành", "HN-Cau-Giay", "P5", "Tai nạn", topic="Safety"
    )
    assert tid != "t-1"
    assert len(db.tables["tasks"]) == 2


def test_absorbs_into_assigned_task_not_only_open():
    """Task đã giao vẫn hút alert mới — nếu không sẽ đẻ task trùng mỗi chu kỳ."""
    db = FakeDB(tasks=[_task(status="assigned")])
    tid = find_or_create_cluster_task(db, "CSKH", "HN-Cau-Giay", "P3", "X", topic="Other")
    assert tid == "t-1" and len(db.tables["tasks"]) == 1


def test_does_not_absorb_into_resolved_task():
    db = FakeDB(tasks=[_task(status="resolved")])
    find_or_create_cluster_task(db, "CSKH", "HN-Cau-Giay", "P3", "X", topic="Other")
    assert len(db.tables["tasks"]) == 2


# ── leo thang ưu tiên ───────────────────────────────────────────────────────

def test_priority_rank_orders_p5_highest():
    assert priority_rank("P5") > priority_rank("P4") > priority_rank("P1")
    assert priority_rank(None) == 0 and priority_rank("khẩn") == 0


def test_escalate_raises_priority_and_tightens_due():
    db = FakeDB(tasks=[_task(priority="P2", due_at="2099-01-01T00:00:00+00:00")])
    assert escalate_task_priority(db, db.tables["tasks"][0], "P5", "Safety") is True
    row = db.tables["tasks"][0]
    assert row["priority"] == "P5"
    assert row["due_at"] != "2099-01-01T00:00:00+00:00"


def test_escalate_never_lowers_priority():
    db = FakeDB(tasks=[_task(priority="P5")])
    assert escalate_task_priority(db, db.tables["tasks"][0], "P2", "Other") is False
    assert db.tables["tasks"][0]["priority"] == "P5"


# ── đọc mức ưu tiên của alert ───────────────────────────────────────────────

def test_alert_priority_prefers_structured_column():
    assert alert_priority(_alert(priority="P4", description="**Priority:** P1")) == "P4"


def test_alert_priority_falls_back_to_legacy_markdown():
    assert alert_priority(_alert(priority=None, description="**Priority:** P5\n")) == "P5"


def test_alert_priority_falls_back_to_severity():
    assert alert_priority(_alert(priority=None, description="", severity="P4")) == "P4"


# ── cluster_alerts_into_tasks (đường chính) ─────────────────────────────────

def _patch_db(monkeypatch, db):
    monkeypatch.setattr(task_agent, "get_db", lambda: db)
    monkeypatch.setattr(task_agent, "log_agent_run", lambda **kw: None)


def test_cluster_splits_by_topic_and_keeps_max_priority(monkeypatch):
    db = FakeDB(
        tasks=[],
        alerts=[
            _alert(id="a1", topic="Delay", priority="P3", assigned_team="Vận hành"),
            _alert(id="a2", topic="Delay", priority="P4", assigned_team="Vận hành"),
            _alert(id="a3", topic="Safety", priority="P5", assigned_team="Vận hành"),
        ],
    )
    _patch_db(monkeypatch, db)
    monkeypatch.setattr(task_agent, "_llm_cluster_title", lambda *a, **k: None)

    res = cluster_alerts_into_tasks()

    assert res["status"] == "success"
    assert res["tasks_created"] == 2          # Delay và Safety tách nhau
    assert res["alerts_assigned"] == 3
    by_topic = {t["topic"]: t for t in db.tables["tasks"]}
    assert by_topic["Delay"]["priority"] == "P4"    # lấy mức nặng nhất trong cụm
    assert by_topic["Safety"]["priority"] == "P5"
    assert all(a["task_id"] for a in db.tables["alerts"])


def test_cluster_uses_fallback_title_when_llm_unavailable(monkeypatch):
    db = FakeDB(tasks=[], alerts=[_alert(id="a1", topic="Payment")])
    _patch_db(monkeypatch, db)
    monkeypatch.setattr(task_agent, "_llm_cluster_title", lambda *a, **k: None)

    res = cluster_alerts_into_tasks()

    assert res["tasks_created"] == 1 and res["clusters_failed"] == 0
    assert "Payment" in db.tables["tasks"][0]["title"]


def test_cluster_never_drops_alerts_when_llm_raises(monkeypatch):
    """LLM nổ không được làm alert mồ côi — đây là lỗi cũ 'except: continue'."""
    def _boom(*_a, **_k):
        raise RuntimeError("provider down")

    db = FakeDB(tasks=[], alerts=[_alert(id="a1", topic="App Issue")])
    _patch_db(monkeypatch, db)
    monkeypatch.setattr(task_agent, "call_llm", _boom)

    res = cluster_alerts_into_tasks()

    assert res["tasks_created"] == 1
    assert db.tables["alerts"][0]["task_id"] is not None


def test_cluster_reports_failure_instead_of_claiming_success(monkeypatch):
    """Cụm hỏng phải hiện ra ở kết quả, không được báo 'success' trơn."""
    db = FakeDB(tasks=[], alerts=[_alert(id="a1", topic="Other")])
    _patch_db(monkeypatch, db)
    monkeypatch.setattr(task_agent, "_llm_cluster_title", lambda *a, **k: None)
    monkeypatch.setattr(
        task_agent, "find_or_create_cluster_task",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("insert denied")),
    )

    res = cluster_alerts_into_tasks()

    assert res["status"] == "partial_success"
    assert res["clusters_failed"] == 1 and res["alerts_assigned"] == 0
    assert db.tables["alerts"][0]["task_id"] is None   # vẫn chờ chu kỳ sau, không mất


def test_cluster_escalates_existing_task(monkeypatch):
    db = FakeDB(
        tasks=[_task(assigned_team="Vận hành", topic="Safety", priority="P3")],
        alerts=[_alert(id="a1", topic="Safety", priority="P5", assigned_team="Vận hành")],
    )
    _patch_db(monkeypatch, db)

    res = cluster_alerts_into_tasks()

    assert res["tasks_created"] == 0 and res["tasks_escalated"] == 1
    assert db.tables["tasks"][0]["priority"] == "P5"


def test_fallback_title_states_no_llm():
    out = fallback_cluster_title("IT", "HN-Cau-Giay", "App Issue", 4)
    assert "App Issue" in out["title"] and "HN-Cau-Giay" in out["title"]
    assert "4" in out["summary"] and "không có phân tích LLM" in out["summary"]
