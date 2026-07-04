from agents.task_agent import create_ticket_task


class _Exec:
    def __init__(self, d): self.data = d
class _Q:
    def __init__(self, sink): self._sink = sink
    def insert(self, row, *a, **k):
        self._sink.append(row)
        return _Q2(row)
class _Q2:
    def __init__(self, row): self._row = row
    def execute(self): return _Exec([{"id": f"task-{len(self._row.get('title',''))}", **self._row}])
class _DB:
    def __init__(self): self.sink = []
    def table(self, name): return _Q(self.sink)


def test_always_creates_new_ticket_task():
    db = _DB()
    t1 = create_ticket_task(db, "CSKH", "HN-Cau-Giay", "P3", "Ticket A", "tóm tắt")
    t2 = create_ticket_task(db, "CSKH", "HN-Cau-Giay", "P3", "Ticket B", "tóm tắt")
    assert t1 and t2
    assert len(db.sink) == 2
    assert all(r["source"] == "ticket" for r in db.sink)
    assert db.sink[0]["assigned_team"] == "CSKH" and db.sink[0]["status"] == "open"
