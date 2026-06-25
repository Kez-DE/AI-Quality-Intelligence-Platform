"""Supabase double in-memory cho test endpoint task.

Hỗ trợ đúng tập thao tác các endpoint dùng: table().select()/insert()/update()
kèm .eq()/.in_()/.neq()/.lt()/.limit()/.order()/.execute(). Mỗi bảng là list[dict].
"""
from __future__ import annotations

import copy
import itertools


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, table, op, payload=None):
        self._t = table
        self._op = op            # "select" | "insert" | "update"
        self._payload = payload
        self._filters = []       # (kind, col, val)
        self._limit = None
        self._order = None

    def eq(self, col, val):
        self._filters.append(("eq", col, val)); return self

    def in_(self, col, vals):
        self._filters.append(("in", col, list(vals))); return self

    def neq(self, col, val):
        self._filters.append(("neq", col, val)); return self

    def lt(self, col, val):
        self._filters.append(("lt", col, val)); return self

    def limit(self, n):
        self._limit = n; return self

    def order(self, col, desc=False):
        self._order = (col, desc); return self

    def _match(self, row):
        for kind, col, val in self._filters:
            cur = row.get(col)
            if kind == "eq" and cur != val:
                return False
            if kind == "in" and cur not in val:
                return False
            if kind == "neq" and cur == val:
                return False
            if kind == "lt" and not (cur is not None and cur < val):
                return False
        return True

    def execute(self):
        rows = self._t.rows
        if self._op == "select":
            out = [copy.deepcopy(r) for r in rows if self._match(r)]
            if self._order:
                col, desc = self._order
                out.sort(key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)
            if self._limit is not None:
                out = out[: self._limit]
            return _Result(out)
        if self._op == "insert":
            recs = self._payload if isinstance(self._payload, list) else [self._payload]
            inserted = []
            for rec in recs:
                rec = copy.deepcopy(rec)
                rec.setdefault("id", self._t.db._next_id())
                rows.append(rec)
                inserted.append(copy.deepcopy(rec))
            return _Result(inserted)
        if self._op == "update":
            updated = []
            for r in rows:
                if self._match(r):
                    r.update(self._payload)
                    updated.append(copy.deepcopy(r))
            return _Result(updated)
        raise AssertionError(f"op không hỗ trợ: {self._op}")


class _Table:
    def __init__(self, db, name):
        self.db = db
        self.rows = db.tables.setdefault(name, [])

    def select(self, *_cols):
        return _Query(self, "select")

    def insert(self, payload):
        return _Query(self, "insert", payload)

    def update(self, payload):
        return _Query(self, "update", payload)


class FakeDB:
    def __init__(self, **tables):
        self.tables = {k: [dict(r) for r in v] for k, v in tables.items()}
        self._ids = itertools.count(1)

    def _next_id(self):
        return f"id-{next(self._ids)}"

    def table(self, name):
        return _Table(self, name)
