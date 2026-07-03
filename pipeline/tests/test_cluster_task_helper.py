from agents.task_agent import find_or_create_cluster_task

class _Exec:
    def __init__(self, d): self.data = d
class _Q:
    def __init__(self, rows, sink=None): self._rows=rows; self._sink=sink
    def select(self,*a,**k): return self
    def eq(self,*a,**k): return self
    def limit(self,*a,**k): return self
    def insert(self, row,*a,**k):
        if self._sink is not None: self._sink.append(row)
        return _Q([{"id":"new-task-1", **row}])
    def execute(self): return _Exec(self._rows)
class _DB:
    def __init__(self, existing=None, sink=None): self._existing=existing or []; self.sink=sink if sink is not None else []
    def table(self, name): return _Q(self._existing, self.sink)

def test_reuse_open_task():
    db=_DB(existing=[{"id":"t-open"}])
    tid=find_or_create_cluster_task(db,"CSKH","HN-Cau-Giay","P3","Ticket X","tóm tắt")
    assert tid=="t-open" and db.sink==[]   # không insert

def test_create_when_none():
    db=_DB(existing=[])
    tid=find_or_create_cluster_task(db,"CSKH","HN-Cau-Giay","P3","Ticket X","tóm tắt")
    assert tid=="new-task-1"
    assert db.sink and db.sink[0]["assigned_team"]=="CSKH" and db.sink[0]["status"]=="open"
