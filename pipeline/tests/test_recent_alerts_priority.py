"""Board 'Phân loại Ticket': ticket open/in_progress không bị 'resolved' mới hơn chôn mất."""
from main import _fetch_board_alerts
from tests._fakedb import FakeDB


def _rows():
    # 150 'resolved' MỚI HƠN (tháng 07) + 5 'open' cũ hơn (tháng 01).
    resolved = [
        {"id": f"r{i}", "status": "resolved",
         "created_at": f"2026-07-05T{i // 60:02d}:{i % 60:02d}:00"}
        for i in range(150)
    ]
    opens = [
        {"id": f"o{i}", "status": "open", "created_at": "2026-01-01T10:00:00"}
        for i in range(5)
    ]
    return resolved + opens


def test_actionable_alerts_never_buried_by_newer_resolved():
    db = FakeDB(alerts=_rows())
    data = _fetch_board_alerts(db, 100)
    ids = {a["id"] for a in data}
    # Cả 5 ticket open phải xuất hiện dù có 150 'resolved' mới hơn tràn cửa sổ.
    assert all(f"o{i}" in ids for i in range(5)), "open alerts bị chôn dưới resolved"
    assert len(data) == 100  # vẫn lấp đủ limit bằng resolved gần nhất


def test_all_actionable_when_no_resolved_needed():
    db = FakeDB(alerts=[{"id": "o1", "status": "open", "created_at": "2026-01-01T10:00:00"}])
    data = _fetch_board_alerts(db, 100)
    assert [a["id"] for a in data] == ["o1"]


def test_non_admin_team_filtered_in_query():
    # Phòng khác có ticket MỚI HƠN nhiều — không được đẩy ticket phòng mình ra khỏi cửa sổ.
    alerts = (
        [{"id": f"it{i}", "status": "open", "assigned_team": "IT",
          "created_at": f"2026-01-01T00:{i:02d}"} for i in range(3)]
        + [{"id": f"cs{i}", "status": "open", "assigned_team": "CSKH",
            "created_at": f"2026-09-01T00:{i:02d}"} for i in range(50)]
    )
    db = FakeDB(alerts=alerts)
    data = _fetch_board_alerts(db, 100, team="IT")
    assert {a["id"] for a in data} == {"it0", "it1", "it2"}


def test_non_admin_includes_alerts_linked_to_team_tasks():
    alerts = [
        {"id": "own", "status": "open", "assigned_team": "IT", "created_at": "2026-01-01T00:00"},
        {"id": "linked", "status": "in_progress", "assigned_team": "CSKH",
         "task_id": "t-it", "created_at": "2026-01-01T00:01"},
        {"id": "other", "status": "open", "assigned_team": "CSKH", "created_at": "2026-01-01T00:02"},
    ]
    db = FakeDB(alerts=alerts)
    data = _fetch_board_alerts(db, 100, team="IT", task_ids={"t-it"})
    assert {a["id"] for a in data} == {"own", "linked"}  # 'other' bị loại
