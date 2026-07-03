"""Task resolved → tự đóng các alert liên kết (task_id)."""
import types
from main import _resolve_alerts_for_task


class _Q:
    def __init__(self, sink):
        self.sink = sink
    def update(self, patch):
        self.sink["patch"] = patch
        return self
    def eq(self, col, val):
        self.sink.setdefault("eq", []).append((col, val))
        return self
    def neq(self, col, val):
        self.sink.setdefault("neq", []).append((col, val))
        return self
    def execute(self):
        class R:
            data = []
        return R()


class _DB:
    def __init__(self, sink):
        self.sink = sink
    def table(self, name):
        self.sink["table"] = name
        return _Q(self.sink)


def test_resolve_alerts_for_task_sets_fields_and_filters():
    sink = {}
    _resolve_alerts_for_task(_DB(sink), "t-1", types.SimpleNamespace(id="u-9"))
    assert sink["table"] == "alerts"
    assert sink["patch"]["status"] == "resolved"
    assert sink["patch"]["resolved_by"] == "u-9"
    assert ("task_id", "t-1") in sink["eq"]
    assert ("status", "resolved") in sink["neq"]   # chỉ alert chưa resolved
