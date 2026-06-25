# Vòng khép kín giao việc & duyệt hoàn thành task — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sửa luồng giao việc top-down (chỉ manager/admin giao → staff nhận → gửi báo cáo → manager duyệt), thêm trạng thái `assigned`/`pending_review`, và ghi audit log vòng đời task vào bảng mới `task_events`.

**Architecture:** Backend FastAPI chạy bằng `service_role` (bypass RLS) nên RBAC gate ở tầng API. Trạng thái task chuyển qua một validator tập trung; mỗi mốc vòng đời ghi một dòng `task_events` ở tầng ứng dụng (nơi duy nhất biết actor). Frontend React (TanStack Router) gọi API qua `apiFetch`, hiển thị theo vai trò.

**Tech Stack:** Python 3 + FastAPI + Supabase (postgrest client), pytest/unittest, venv `pipeline/.venv`; React + TypeScript + Vite ở `app/`.

## Global Constraints

- 4 phòng ban hợp lệ: `IT`, `CSKH`, `Vận hành`, `Marketing`. KHÔNG mở rộng 6 phòng.
- Backend chạy `service_role`; mọi endpoint ghi PHẢI tự kiểm tra role + scope phòng ở tầng API.
- RBAC giao việc: chỉ `manager`/`admin` giao task; người nhận (`owner_id`) bắt buộc là `staff` cùng phòng.
- Vòng đời task: `open → assigned → in_progress → pending_review → resolved`; reject → `in_progress`.
- Test gọi thẳng hàm endpoint (bỏ qua `Depends`), nên mỗi endpoint PHẢI có kiểm tra role nội bộ (giống `trigger_daily_report`), không chỉ dựa vào dependency.
- Mọi lệnh Python: `cd pipeline && .venv/bin/python ...`. Test: `.venv/bin/python -m pytest tests/<file> -q`.
- Frontend build/typecheck: `cd app && npm run build` (Vite + tsc). `noUnusedLocals=false` nên import/handler thừa không vỡ build.
- Mọi commit kết thúc bằng: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Spec nguồn: `docs/superpowers/specs/2026-06-25-task-completion-loop-design.md`.

## File Structure

- `supabase/migrations/20260628000000_task_events_and_status.sql` *(mới)* — bảng `task_events` + CHECK trạng thái task.
- `pipeline/auth_guard.py` *(sửa)* — thêm `require_manager`.
- `pipeline/main.py` *(sửa)* — `ALLOWED_TASK_TRANSITIONS`, `_assert_transition`, `_log_task_event`; sửa `assign_task`, `submit_completion_report`, `review_completion_report`, `list_assignable_users`; thêm `accept_task`, `list_task_events`.
- `pipeline/tests/_fakedb.py` *(mới)* — Supabase double in-memory cho test.
- `pipeline/tests/test_task_lifecycle.py` *(mới)* — test RBAC + state machine + audit log.
- `pipeline/tests/test_auth_guard_manager.py`, `test_task_transitions.py`, `test_migration_task_events.py` *(mới)* — unit nhỏ.
- `app/src/routes/_authenticated/tasks.tsx` *(sửa)* — gating manager-only, nút "Nhận việc", trạng thái mới, người nhận staff-only.
- `app/src/routes/_authenticated/completion-reports.tsx` *(sửa)* — phản ánh trạng thái task sau duyệt.

---

### Task 1: Migration — bảng task_events + CHECK trạng thái

**Files:**
- Create: `supabase/migrations/20260628000000_task_events_and_status.sql`
- Create: `pipeline/tests/test_migration_task_events.py`

**Interfaces:**
- Produces: bảng `public.task_events`; ràng buộc `tasks_status_check`.

- [ ] **Step 1: Viết migration**

Create `supabase/migrations/20260628000000_task_events_and_status.sql`:

```sql
-- Vòng đời task khép kín: thêm trạng thái + bảng audit task_events.
-- Backend chạy SERVICE_ROLE_KEY (bypass RLS); quyền gate ở tầng API. RLS là lớp phòng thủ.
-- Yêu cầu: 20260626000000_task_completion_reports.sql đã chạy trước (FK completion_report_id).

-- 1) Mở rộng trạng thái task: open -> assigned -> in_progress -> pending_review -> resolved
ALTER TABLE public.tasks DROP CONSTRAINT IF EXISTS tasks_status_check;
ALTER TABLE public.tasks ADD CONSTRAINT tasks_status_check
  CHECK (status IN ('open','assigned','in_progress','pending_review','resolved'));

-- 2) Audit log vòng đời task
CREATE TABLE IF NOT EXISTS public.task_events (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  task_id UUID NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
  actor_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  actor_email TEXT,
  actor_role TEXT,
  team TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN (
    'assigned','accepted','completion_submitted',
    'completion_approved','completion_rejected','reopened','status_changed'
  )),
  from_status TEXT,
  to_status TEXT,
  completion_report_id UUID REFERENCES public.task_completion_reports(id) ON DELETE SET NULL,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_task_events_task_id ON public.task_events(task_id);
CREATE INDEX IF NOT EXISTS idx_task_events_team ON public.task_events(team, created_at DESC);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.task_events TO authenticated;
GRANT ALL ON public.task_events TO service_role;
ALTER TABLE public.task_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Task events viewable by authenticated" ON public.task_events;
CREATE POLICY "Task events viewable by authenticated"
  ON public.task_events FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS "Task events insert by authenticated" ON public.task_events;
CREATE POLICY "Task events insert by authenticated"
  ON public.task_events FOR INSERT TO authenticated WITH CHECK (true);
DROP POLICY IF EXISTS "Task events manageable by service_role" ON public.task_events;
CREATE POLICY "Task events manageable by service_role"
  ON public.task_events FOR ALL TO service_role USING (true) WITH CHECK (true);

COMMENT ON TABLE public.task_events IS
  'Audit log vòng đời task: giao -> nhận -> gửi báo cáo -> duyệt/trả lại. Ghi ở tầng API (có actor).';

DO $$ BEGIN
  ALTER PUBLICATION supabase_realtime ADD TABLE public.task_events;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
```

- [ ] **Step 2: Viết guard test (chống xoá/sai DDL)**

Create `pipeline/tests/test_migration_task_events.py`:

```python
from pathlib import Path

MIG = (
    Path(__file__).resolve().parents[2]
    / "supabase" / "migrations" / "20260628000000_task_events_and_status.sql"
)


def test_migration_file_exists():
    assert MIG.is_file(), f"Thiếu migration: {MIG}"


def test_migration_has_task_events_table_and_status_check():
    sql = MIG.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS public.task_events" in sql
    assert "tasks_status_check" in sql
    assert "'pending_review'" in sql
    assert "'assigned'" in sql
    assert "completion_report_id" in sql
```

- [ ] **Step 3: Chạy guard test**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_migration_task_events.py -q`
Expected: PASS (2 test).

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/20260628000000_task_events_and_status.sql pipeline/tests/test_migration_task_events.py
git commit -m "feat(db): bảng task_events (audit vòng đời) + CHECK trạng thái task

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `require_manager` trong auth_guard

**Files:**
- Modify: `pipeline/auth_guard.py` (sau `require_admin`, ~dòng 74)
- Create: `pipeline/tests/test_auth_guard_manager.py`

**Interfaces:**
- Produces: `require_manager(user: AuthUser = Depends(get_current_user)) -> AuthUser` — raise 403 nếu role ∉ {manager, admin}.

- [ ] **Step 1: Viết failing test**

Create `pipeline/tests/test_auth_guard_manager.py`:

```python
import pytest
from fastapi import HTTPException

from auth_guard import require_manager, AuthUser


def _u(role: str) -> AuthUser:
    return AuthUser(id="u", email=None, role=role, department=None)


def test_manager_passes():
    assert require_manager(_u("manager")).role == "manager"


def test_admin_passes():
    assert require_manager(_u("admin")).role == "admin"


def test_staff_forbidden():
    with pytest.raises(HTTPException) as exc:
        require_manager(_u("staff"))
    assert exc.value.status_code == 403


def test_guest_forbidden():
    with pytest.raises(HTTPException) as exc:
        require_manager(_u("guest"))
    assert exc.value.status_code == 403
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_auth_guard_manager.py -q`
Expected: FAIL với `ImportError: cannot import name 'require_manager'`.

- [ ] **Step 3: Thêm `require_manager`**

Trong `pipeline/auth_guard.py`, ngay sau hàm `require_admin` (kết thúc ~dòng 74), thêm:

```python
def require_manager(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=403, detail="Yêu cầu quyền manager hoặc admin")
    return user
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_auth_guard_manager.py -q`
Expected: PASS (4 test).

- [ ] **Step 5: Commit**

```bash
git add pipeline/auth_guard.py pipeline/tests/test_auth_guard_manager.py
git commit -m "feat(auth): require_manager gate cho thao tác giao việc

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Validator chuyển trạng thái task

**Files:**
- Modify: `pipeline/main.py` (thêm hằng + helper, gần các helper `_parse_timestamp` ~dòng 79)
- Create: `pipeline/tests/test_task_transitions.py`

**Interfaces:**
- Produces:
  - `ALLOWED_TASK_TRANSITIONS: set[tuple[str, str]]`
  - `_assert_transition(from_status: str | None, to_status: str) -> None` — raise `HTTPException(400)` nếu cặp không hợp lệ; no-op nếu `from == to`.

- [ ] **Step 1: Viết failing test**

Create `pipeline/tests/test_task_transitions.py`:

```python
import pytest
from fastapi import HTTPException

from main import _assert_transition, ALLOWED_TASK_TRANSITIONS


def test_open_to_assigned_ok():
    _assert_transition("open", "assigned")


def test_assigned_to_in_progress_ok():
    _assert_transition("assigned", "in_progress")


def test_pending_review_to_resolved_ok():
    _assert_transition("pending_review", "resolved")


def test_pending_review_to_in_progress_ok():
    _assert_transition("pending_review", "in_progress")


def test_same_state_is_noop():
    _assert_transition("in_progress", "in_progress")


def test_open_to_resolved_rejected():
    with pytest.raises(HTTPException) as exc:
        _assert_transition("open", "resolved")
    assert exc.value.status_code == 400


def test_table_has_reassign_paths():
    assert ("in_progress", "assigned") in ALLOWED_TASK_TRANSITIONS
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_task_transitions.py -q`
Expected: FAIL với `ImportError: cannot import name '_assert_transition'`.

- [ ] **Step 3: Thêm hằng + helper**

Trong `pipeline/main.py`, ngay sau hàm `_parse_timestamp` (~dòng 85), thêm:

```python
# Vòng đời task hợp lệ. Reassign (đổi owner) đưa task active về 'assigned' để nhận lại.
ALLOWED_TASK_TRANSITIONS = {
    ("open", "assigned"),
    ("assigned", "assigned"),
    ("in_progress", "assigned"),
    ("assigned", "in_progress"),
    ("in_progress", "pending_review"),
    ("pending_review", "resolved"),
    ("pending_review", "in_progress"),
}


def _assert_transition(from_status: str | None, to_status: str) -> None:
    """Chặn chuyển trạng thái task không hợp lệ. No-op nếu giữ nguyên trạng thái."""
    if from_status == to_status:
        return
    if (from_status, to_status) not in ALLOWED_TASK_TRANSITIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Chuyển trạng thái không hợp lệ: {from_status} -> {to_status}",
        )
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_task_transitions.py -q`
Expected: PASS (7 test).

- [ ] **Step 5: Commit**

```bash
git add pipeline/main.py pipeline/tests/test_task_transitions.py
git commit -m "feat(tasks): validator chuyển trạng thái vòng đời task

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Supabase test double + `_log_task_event`

**Files:**
- Create: `pipeline/tests/_fakedb.py`
- Modify: `pipeline/main.py` (thêm `_log_task_event` sau `_assert_transition`)
- Create: `pipeline/tests/test_task_events_helper.py`

**Interfaces:**
- Produces:
  - `FakeDB(**tables)` với `.table(name)` hỗ trợ `select/insert/update` + `.eq/.in_/.neq/.lt/.limit/.order/.execute`; `.tables[name]` là list dict đã ghi.
  - `_log_task_event(db, *, task_id, actor, team, action, from_status=None, to_status=None, completion_report_id=None, note=None) -> None` — INSERT một dòng `task_events`; lỗi ghi không làm hỏng thao tác chính.

- [ ] **Step 1: Viết Supabase double**

Create `pipeline/tests/_fakedb.py`:

```python
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
```

- [ ] **Step 2: Viết failing test cho `_log_task_event`**

Create `pipeline/tests/test_task_events_helper.py`:

```python
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
```

- [ ] **Step 3: Chạy test, xác nhận FAIL**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_task_events_helper.py -q`
Expected: FAIL với `AttributeError: module 'main' has no attribute '_log_task_event'`.

- [ ] **Step 4: Thêm `_log_task_event`**

Trong `pipeline/main.py`, ngay sau `_assert_transition` (Task 3), thêm:

```python
def _log_task_event(
    db, *, task_id, actor, team, action,
    from_status=None, to_status=None, completion_report_id=None, note=None,
):
    """Ghi một mốc vòng đời task vào task_events. Audit là phụ trợ: lỗi ghi không
    được làm hỏng thao tác chính (bọc try/except)."""
    try:
        db.table("task_events").insert({
            "task_id": task_id,
            "actor_id": getattr(actor, "id", None),
            "actor_email": getattr(actor, "email", None),
            "actor_role": getattr(actor, "role", None),
            "team": team,
            "action": action,
            "from_status": from_status,
            "to_status": to_status,
            "completion_report_id": completion_report_id,
            "note": note,
        }).execute()
    except Exception as exc:  # noqa: BLE001 — audit không chặn nghiệp vụ
        logging.getLogger("task_events").warning("Không ghi được task_event: %s", str(exc)[:200])
```

Nếu `main.py` chưa import `logging`, thêm `import logging` vào khối import đầu file.

- [ ] **Step 5: Chạy test, xác nhận PASS**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_task_events_helper.py -q`
Expected: PASS (2 test).

- [ ] **Step 6: Commit**

```bash
git add pipeline/tests/_fakedb.py pipeline/tests/test_task_events_helper.py pipeline/main.py
git commit -m "feat(tasks): helper ghi audit task_events + Supabase test double

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `list_assignable_users` → chỉ staff

**Files:**
- Modify: `pipeline/main.py` (`list_assignable_users`, ~dòng 568-570)
- Create: `pipeline/tests/test_task_lifecycle.py` (file dùng chung cho Task 5–10)

**Interfaces:**
- Consumes: `FakeDB` (Task 4).
- Produces: `/api/users/assignable` chỉ trả profiles `role == 'staff'`, vẫn scope theo phòng.

- [ ] **Step 1: Viết failing test**

Create `pipeline/tests/test_task_lifecycle.py`:

```python
import os
import sys
from unittest.mock import patch

import pytest
from fastapi import HTTPException

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from _fakedb import FakeDB
from auth_guard import AuthUser
from main import (
    list_assignable_users,
    assign_task,
    submit_completion_report,
    review_completion_report,
    AssignTaskReq,
    CompletionReportReq,
    ReviewReportReq,
)
# accept_task (Task 7) và list_task_events (Task 10) sẽ được thêm vào import này
# khi tới các task đó — chỉ import symbol đã tồn tại để test chạy được ngay.


def _user(role: str, dept=None, uid="u1") -> AuthUser:
    return AuthUser(id=uid, email=f"{uid}@x.com", role=role, department=dept)


def test_assignable_returns_staff_only():
    db = FakeDB(profiles=[
        {"id": "s1", "email": "s@x", "role": "staff", "department": "IT", "full_name": None},
        {"id": "m1", "email": "m@x", "role": "manager", "department": "IT", "full_name": None},
        {"id": "a1", "email": "a@x", "role": "admin", "department": "IT", "full_name": None},
    ])
    with patch("main.get_supabase", return_value=db):
        out = list_assignable_users(team=None, user=_user("manager", "IT"))
    assert {u["role"] for u in out["data"]} == {"staff"}
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_task_lifecycle.py::test_assignable_returns_staff_only -q`
Expected: FAIL — endpoint hiện trả cả manager/admin (`{'staff','manager','admin'}`).

- [ ] **Step 3: Sửa endpoint**

Trong `pipeline/main.py`, hàm `list_assignable_users`, đổi khối query (~dòng 568-570):

```python
        q = db.table("profiles") \
            .select("id,email,role,full_name,department") \
            .in_("role", ["staff", "manager", "admin"])
```

thành:

```python
        q = db.table("profiles") \
            .select("id,email,role,full_name,department") \
            .eq("role", "staff")
```

Cập nhật docstring hàm: người nhận task chỉ là `staff` cùng phòng.

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_task_lifecycle.py::test_assignable_returns_staff_only -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pipeline/main.py pipeline/tests/test_task_lifecycle.py
git commit -m "fix(tasks): danh sách người nhận chỉ gồm staff cùng phòng

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: `assign_task` — manager-only, owner là staff, status `assigned`, ghi event

**Files:**
- Modify: `pipeline/main.py` (`assign_task`, dòng 361-403)
- Modify: `pipeline/tests/test_task_lifecycle.py` (thêm test)

**Interfaces:**
- Consumes: `require_manager` (Task 2), `_assert_transition` (Task 3), `_log_task_event` (Task 4).
- Produces: `assign_task` set `status='assigned'`, validate owner `role=='staff'` cùng phòng, ghi event `assigned`.

- [ ] **Step 1: Thêm failing tests**

Trong `pipeline/tests/test_task_lifecycle.py`, thêm:

```python
def _db_with_task(status="open", team="IT"):
    return FakeDB(
        tasks=[{"id": "t1", "assigned_team": team, "status": status, "owner_id": None}],
        profiles=[
            {"id": "s1", "email": "s@x", "role": "staff", "department": "IT", "full_name": "S"},
            {"id": "m1", "email": "m@x", "role": "manager", "department": "IT", "full_name": "M"},
        ],
        task_events=[],
    )


def test_staff_cannot_assign():
    db = _db_with_task()
    with patch("main.get_supabase", return_value=db):
        with pytest.raises(HTTPException) as exc:
            assign_task("t1", AssignTaskReq(owner_id="s1"), user=_user("staff", "IT"))
    assert exc.value.status_code == 403


def test_assign_rejects_manager_owner():
    db = _db_with_task()
    with patch("main.get_supabase", return_value=db):
        with pytest.raises(HTTPException) as exc:
            assign_task("t1", AssignTaskReq(owner_id="m1"), user=_user("manager", "IT"))
    assert exc.value.status_code == 400


def test_assign_sets_status_and_logs_event():
    db = _db_with_task()
    with patch("main.get_supabase", return_value=db):
        assign_task("t1", AssignTaskReq(owner_id="s1"), user=_user("manager", "IT"))
    task = db.tables["tasks"][0]
    assert task["status"] == "assigned"
    assert task["owner_id"] == "s1"
    assert any(e["action"] == "assigned" for e in db.tables["task_events"])
```

- [ ] **Step 2: Chạy, xác nhận FAIL**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_task_lifecycle.py -k assign -q`
Expected: FAIL (staff hiện vẫn gán được; owner manager hiện cho qua; chưa set `assigned`).

- [ ] **Step 3: Viết lại `assign_task`**

Thay toàn bộ hàm `assign_task` (dòng 361-403) bằng:

```python
@app.patch("/api/tasks/{task_id}/assign")
def assign_task(task_id: str, payload: AssignTaskReq, user: AuthUser = Depends(require_manager)):
    if user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=403, detail="Chỉ manager hoặc admin được giao task.")
    update_fields: dict = {}
    if payload.due_at is not None:
        update_fields["due_at"] = payload.due_at
    if payload.owner_id is None and not update_fields:
        raise HTTPException(status_code=400, detail="Must provide owner_id or due_at")
    try:
        db = get_supabase()
        rows = db.table("tasks").select("assigned_team,status").eq("id", task_id).limit(1).execute().data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Task not found")
        task_team = rows[0].get("assigned_team")
        cur_status = rows[0].get("status")
        if user.role != "admin" and not can_view_team(user, task_team):
            raise HTTPException(status_code=403, detail="Bạn không có quyền gán task của phòng ban khác.")
        new_status = cur_status
        if payload.owner_id is not None:
            owners = db.table("profiles").select("role,department").eq("id", payload.owner_id).limit(1).execute().data or []
            if not owners:
                raise HTTPException(status_code=404, detail="Không tìm thấy người nhận.")
            owner = owners[0]
            if owner.get("role") != "staff":
                raise HTTPException(status_code=400, detail="Người nhận task phải là nhân viên (staff).")
            if task_team and owner.get("department") != task_team:
                raise HTTPException(
                    status_code=400,
                    detail=f"Người nhận phải thuộc phòng ban '{task_team}' của task.",
                )
            _assert_transition(cur_status, "assigned")
            update_fields["owner_id"] = payload.owner_id
            update_fields["status"] = "assigned"
            new_status = "assigned"
        update_fields["updated_at"] = "now()"
        data = db.table("tasks").update(update_fields).eq("id", task_id).execute().data or []
        if payload.owner_id is not None:
            _log_task_event(
                db, task_id=task_id, actor=user, team=task_team, action="assigned",
                from_status=cur_status, to_status=new_status,
                note=f"owner={payload.owner_id}",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot assign task: {str(exc)[:300]}") from exc
    if not data:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "success", "data": data[0]}
```

- [ ] **Step 4: Chạy, xác nhận PASS**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_task_lifecycle.py -k assign -q`
Expected: PASS (3 test).

- [ ] **Step 5: Commit**

```bash
git add pipeline/main.py pipeline/tests/test_task_lifecycle.py
git commit -m "fix(tasks): chỉ manager/admin giao task, owner phải là staff, set assigned + audit

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Endpoint `POST /api/tasks/{id}/accept`

**Files:**
- Modify: `pipeline/main.py` (thêm endpoint ngay sau `assign_task`)
- Modify: `pipeline/tests/test_task_lifecycle.py` (thêm `accept_task` vào import + test)

**Interfaces:**
- Consumes: `require_ops_staff`, `_assert_transition`, `_log_task_event`.
- Produces: `accept_task(task_id, user)` — owner staff nhận task `assigned → in_progress`, ghi event `accepted`.

- [ ] **Step 1: Thêm `accept_task` vào import của test + thêm test**

Trong `pipeline/tests/test_task_lifecycle.py`, thêm `accept_task` vào khối `from main import (...)` (thêm dòng `    accept_task,`). Rồi thêm test:

```python
def test_accept_by_owner_moves_in_progress():
    db = FakeDB(
        tasks=[{"id": "t1", "assigned_team": "IT", "status": "assigned", "owner_id": "s1"}],
        task_events=[],
    )
    with patch("main.get_supabase", return_value=db):
        accept_task("t1", user=_user("staff", "IT", uid="s1"))
    assert db.tables["tasks"][0]["status"] == "in_progress"
    assert any(e["action"] == "accepted" for e in db.tables["task_events"])


def test_accept_by_non_owner_forbidden():
    db = FakeDB(
        tasks=[{"id": "t1", "assigned_team": "IT", "status": "assigned", "owner_id": "s1"}],
        task_events=[],
    )
    with patch("main.get_supabase", return_value=db):
        with pytest.raises(HTTPException) as exc:
            accept_task("t1", user=_user("staff", "IT", uid="s2"))
    assert exc.value.status_code == 403


def test_accept_open_task_invalid_transition():
    db = FakeDB(
        tasks=[{"id": "t1", "assigned_team": "IT", "status": "open", "owner_id": "s1"}],
        task_events=[],
    )
    with patch("main.get_supabase", return_value=db):
        with pytest.raises(HTTPException) as exc:
            accept_task("t1", user=_user("staff", "IT", uid="s1"))
    assert exc.value.status_code == 400
```

- [ ] **Step 2: Chạy, xác nhận FAIL**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_task_lifecycle.py -k accept -q`
Expected: FAIL với `ImportError: cannot import name 'accept_task'`.

- [ ] **Step 3: Thêm endpoint**

Trong `pipeline/main.py`, ngay sau hàm `assign_task`, thêm:

```python
@app.post("/api/tasks/{task_id}/accept")
def accept_task(task_id: str, user: AuthUser = Depends(require_ops_staff)):
    """Nhân viên được giao bấm nhận việc: assigned -> in_progress."""
    try:
        db = get_supabase()
        rows = db.table("tasks").select("assigned_team,status,owner_id").eq("id", task_id).limit(1).execute().data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Task not found")
        task = rows[0]
        if task.get("owner_id") != user.id:
            raise HTTPException(status_code=403, detail="Chỉ người được giao mới nhận được task này.")
        cur_status = task.get("status")
        _assert_transition(cur_status, "in_progress")
        data = db.table("tasks").update({"status": "in_progress", "updated_at": "now()"}).eq("id", task_id).execute().data or []
        _log_task_event(
            db, task_id=task_id, actor=user, team=task.get("assigned_team"),
            action="accepted", from_status=cur_status, to_status="in_progress",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot accept task: {str(exc)[:300]}") from exc
    if not data:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "success", "data": data[0]}
```

- [ ] **Step 4: Chạy, xác nhận PASS**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_task_lifecycle.py -k accept -q`
Expected: PASS (3 test).

- [ ] **Step 5: Commit**

```bash
git add pipeline/main.py pipeline/tests/test_task_lifecycle.py
git commit -m "feat(tasks): endpoint nhận việc (assigned -> in_progress) + audit

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: `submit_completion_report` — `pending_review`, bỏ auto-resolve, ghi event

**Files:**
- Modify: `pipeline/main.py` (`submit_completion_report`, dòng 639-673)
- Modify: `pipeline/tests/test_task_lifecycle.py` (thêm test)

**Interfaces:**
- Consumes: `can_view_team`, `_assert_transition`, `_log_task_event`.
- Produces: báo `completed` → task `in_progress → pending_review`; `partial`/`blocked` → giữ nguyên; trả bản ghi báo cáo; ghi event `completion_submitted`.

- [ ] **Step 1: Thêm failing tests**

Trong `pipeline/tests/test_task_lifecycle.py`, thêm:

```python
def test_submit_completed_sets_pending_review():
    db = FakeDB(
        tasks=[{"id": "t1", "assigned_team": "IT", "status": "in_progress", "owner_id": "s1"}],
        task_completion_reports=[], task_events=[],
    )
    with patch("main.get_supabase", return_value=db):
        submit_completion_report(
            "t1", CompletionReportReq(note="đã xử lý xong", completion_level="completed"),
            user=_user("staff", "IT", uid="s1"),
        )
    assert db.tables["tasks"][0]["status"] == "pending_review"
    assert len(db.tables["task_completion_reports"]) == 1
    assert any(e["action"] == "completion_submitted" for e in db.tables["task_events"])


def test_submit_partial_keeps_in_progress():
    db = FakeDB(
        tasks=[{"id": "t1", "assigned_team": "IT", "status": "in_progress", "owner_id": "s1"}],
        task_completion_reports=[], task_events=[],
    )
    with patch("main.get_supabase", return_value=db):
        submit_completion_report(
            "t1", CompletionReportReq(note="mới một phần", completion_level="partial"),
            user=_user("staff", "IT", uid="s1"),
        )
    assert db.tables["tasks"][0]["status"] == "in_progress"
```

- [ ] **Step 2: Chạy, xác nhận FAIL**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_task_lifecycle.py -k submit -q`
Expected: FAIL — hiện `completed` set task `resolved` (không phải `pending_review`), chưa ghi event.

- [ ] **Step 3: Viết lại thân `submit_completion_report`**

Thay phần thân trong `try:` của `submit_completion_report` (từ `db = get_supabase()` tới hết khối, dòng 646-672) bằng:

```python
        db = get_supabase()
        rows = db.table("tasks").select("assigned_team,status").eq("id", task_id).limit(1).execute().data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Task not found")
        task_team = rows[0].get("assigned_team")
        cur_status = rows[0].get("status")
        if not can_view_team(user, task_team):
            raise HTTPException(status_code=403, detail="Bạn không thể báo cáo task của phòng ban khác.")
        record = {
            "task_id": task_id,
            "staff_id": user.id,
            "staff_email": user.email,
            "team": task_team,
            "completion_level": payload.completion_level,
            "note": payload.note,
            "status": "submitted",
        }
        inserted = db.table("task_completion_reports").insert(record).execute().data or []
        if not inserted:
            raise HTTPException(status_code=503, detail="Không tạo được báo cáo hoàn thành")
        report = inserted[0]
        # 'completed' -> chuyển task sang chờ duyệt (KHÔNG auto-resolve). partial/blocked giữ nguyên.
        new_status = cur_status
        if payload.completion_level == "completed":
            _assert_transition(cur_status, "pending_review")
            db.table("tasks").update({"status": "pending_review", "updated_at": "now()"}).eq("id", task_id).execute()
            new_status = "pending_review"
        _log_task_event(
            db, task_id=task_id, actor=user, team=task_team, action="completion_submitted",
            from_status=cur_status, to_status=new_status,
            completion_report_id=report.get("id"),
            note=f"{payload.completion_level}: {payload.note[:200]}",
        )
```

Sau khối `try/except`, đổi phần return cuối hàm thành:

```python
    return {"status": "success", "data": report}
```

(Xoá đoạn cũ `if not data: ... return {... data[0]}` vì biến `data` không còn dùng; nay trả `report`.)

- [ ] **Step 4: Chạy, xác nhận PASS**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_task_lifecycle.py -k submit -q`
Expected: PASS (2 test).

- [ ] **Step 5: Commit**

```bash
git add pipeline/main.py pipeline/tests/test_task_lifecycle.py
git commit -m "fix(tasks): báo cáo completed -> chờ duyệt thay vì auto-resolve + audit

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: `review_completion_report` — duyệt/​trả lại đổi trạng thái task + ghi event

**Files:**
- Modify: `pipeline/main.py` (`review_completion_report`, dòng 720-749)
- Modify: `pipeline/tests/test_task_lifecycle.py` (thêm test)

**Interfaces:**
- Consumes: `ALLOWED_TASK_TRANSITIONS`, `_log_task_event`, `can_view_team`.
- Produces: `approved` → task `pending_review → resolved` (event `completion_approved`); `rejected` → task `pending_review → in_progress` (event `completion_rejected`).

- [ ] **Step 1: Thêm failing tests**

Trong `pipeline/tests/test_task_lifecycle.py`, thêm:

```python
def _db_review():
    return FakeDB(
        tasks=[{"id": "t1", "assigned_team": "IT", "status": "pending_review", "owner_id": "s1"}],
        task_completion_reports=[{"id": "r1", "task_id": "t1", "team": "IT", "status": "submitted"}],
        task_events=[],
    )


def test_approve_resolves_task():
    db = _db_review()
    with patch("main.get_supabase", return_value=db):
        review_completion_report("r1", ReviewReportReq(status="approved"), user=_user("manager", "IT"))
    assert db.tables["tasks"][0]["status"] == "resolved"
    assert db.tables["task_completion_reports"][0]["status"] == "approved"
    assert any(e["action"] == "completion_approved" for e in db.tables["task_events"])


def test_reject_reopens_task():
    db = _db_review()
    with patch("main.get_supabase", return_value=db):
        review_completion_report("r1", ReviewReportReq(status="rejected", review_note="thiếu chi tiết"), user=_user("manager", "IT"))
    assert db.tables["tasks"][0]["status"] == "in_progress"
    assert any(e["action"] == "completion_rejected" for e in db.tables["task_events"])


def test_staff_cannot_review():
    db = _db_review()
    with patch("main.get_supabase", return_value=db):
        with pytest.raises(HTTPException) as exc:
            review_completion_report("r1", ReviewReportReq(status="approved"), user=_user("staff", "IT"))
    assert exc.value.status_code == 403
```

- [ ] **Step 2: Chạy, xác nhận FAIL**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_task_lifecycle.py -k review -q`
Expected: FAIL — review hiện không đổi trạng thái task, chưa ghi event.

- [ ] **Step 3: Viết lại thân `review_completion_report`**

Thay phần thân trong `try:` (từ `db = get_supabase()` tới hết khối, dòng 729-742) bằng:

```python
        db = get_supabase()
        rows = db.table("task_completion_reports").select("team,task_id").eq("id", report_id).limit(1).execute().data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Report not found")
        team = rows[0].get("team")
        rep_task_id = rows[0].get("task_id")
        if not can_view_team(user, team):
            raise HTTPException(status_code=403, detail="Không có quyền duyệt báo cáo phòng ban khác.")
        data = db.table("task_completion_reports").update({
            "status": payload.status,
            "review_note": payload.review_note,
            "reviewed_by": user.id,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": "now()",
        }).eq("id", report_id).execute().data or []
        # Lái trạng thái task theo kết quả duyệt.
        task_rows = db.table("tasks").select("status").eq("id", rep_task_id).limit(1).execute().data or []
        cur = task_rows[0].get("status") if task_rows else None
        target = "resolved" if payload.status == "approved" else "in_progress"
        action = "completion_approved" if payload.status == "approved" else "completion_rejected"
        to_status = cur
        if cur is not None and (cur, target) in ALLOWED_TASK_TRANSITIONS:
            db.table("tasks").update({"status": target, "updated_at": "now()"}).eq("id", rep_task_id).execute()
            to_status = target
        _log_task_event(
            db, task_id=rep_task_id, actor=user, team=team, action=action,
            from_status=cur, to_status=to_status, completion_report_id=report_id,
            note=payload.review_note,
        )
```

(Giữ nguyên kiểm tra `if user.role not in {"manager", "admin"}` ở đầu hàm và `if payload.status not in {"approved","rejected"}`.)

- [ ] **Step 4: Chạy, xác nhận PASS**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_task_lifecycle.py -k review -q`
Expected: PASS (3 test).

- [ ] **Step 5: Commit**

```bash
git add pipeline/main.py pipeline/tests/test_task_lifecycle.py
git commit -m "fix(tasks): duyệt báo cáo lái trạng thái task (resolved/reopen) + audit

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Endpoint `GET /api/tasks/{id}/events`

**Files:**
- Modify: `pipeline/main.py` (thêm endpoint sau `list_task_completion_reports`)
- Modify: `pipeline/tests/test_task_lifecycle.py` (thêm `list_task_events` vào import + test)

**Interfaces:**
- Consumes: `require_ops_staff`, `can_view_team`.
- Produces: `list_task_events(task_id, user)` — trả audit trail của task, scope theo phòng, order `created_at` desc.

- [ ] **Step 1: Thêm test**

Trong `pipeline/tests/test_task_lifecycle.py`, thêm `list_task_events` vào khối `from main import (...)` (thêm dòng `    list_task_events,`). Rồi thêm:

```python
def test_list_task_events_scoped():
    db = FakeDB(
        tasks=[{"id": "t1", "assigned_team": "IT", "status": "assigned"}],
        task_events=[
            {"id": "e1", "task_id": "t1", "team": "IT", "action": "assigned",
             "created_at": "2026-06-25T00:00:00Z"},
        ],
    )
    with patch("main.get_supabase", return_value=db):
        out = list_task_events("t1", user=_user("manager", "IT"))
    assert len(out["data"]) == 1
    assert out["data"][0]["action"] == "assigned"


def test_list_task_events_cross_team_forbidden():
    db = FakeDB(
        tasks=[{"id": "t1", "assigned_team": "IT", "status": "assigned"}],
        task_events=[],
    )
    with patch("main.get_supabase", return_value=db):
        with pytest.raises(HTTPException) as exc:
            list_task_events("t1", user=_user("manager", "CSKH"))
    assert exc.value.status_code == 403
```

- [ ] **Step 2: Chạy, xác nhận FAIL**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_task_lifecycle.py -k events -q`
Expected: FAIL với `ImportError: cannot import name 'list_task_events'`.

- [ ] **Step 3: Thêm endpoint**

Trong `pipeline/main.py`, ngay sau `list_task_completion_reports` (~dòng 693), thêm:

```python
@app.get("/api/tasks/{task_id}/events")
def list_task_events(task_id: str, user: AuthUser = Depends(require_ops_staff)):
    """Audit trail vòng đời của một task (scope theo phòng)."""
    try:
        db = get_supabase()
        rows = db.table("tasks").select("assigned_team").eq("id", task_id).limit(1).execute().data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Task not found")
        if not can_view_team(user, rows[0].get("assigned_team")):
            raise HTTPException(status_code=403, detail="Không có quyền xem nhật ký phòng ban khác.")
        data = db.table("task_events").select("*").eq("task_id", task_id) \
            .order("created_at", desc=True).execute().data or []
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot read task events: {str(exc)[:300]}") from exc
    return {"status": "success", "data": data}
```

- [ ] **Step 4: Chạy toàn bộ test lifecycle**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_task_lifecycle.py -q`
Expected: PASS toàn bộ (assignable, assign×3, accept×3, submit×2, review×3, events×2).

- [ ] **Step 5: Commit**

```bash
git add pipeline/main.py pipeline/tests/test_task_lifecycle.py
git commit -m "feat(tasks): endpoint xem audit trail vòng đời task

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: Frontend `tasks.tsx` — gating manager, nút Nhận việc, trạng thái mới

**Files:**
- Modify: `app/src/routes/_authenticated/tasks.tsx`

**Interfaces:**
- Consumes: `POST /api/tasks/{id}/accept`, `/api/users/assignable` (nay chỉ staff).

- [ ] **Step 1: Thêm trạng thái vào filter + nhãn**

Đổi (dòng 68):

```typescript
const STATUSES = ["All", "open", "in_progress", "resolved"] as const;
```

thành:

```typescript
const STATUSES = ["All", "open", "assigned", "in_progress", "pending_review", "resolved"] as const;
```

Đổi `STATUS_LABELS` (dòng 71-76) thành, và thêm `STATUS_BADGE` ngay sau:

```typescript
const STATUS_LABELS: Record<string, string> = {
  All: "Tất cả",
  open: "Đang mở",
  assigned: "Đã giao",
  in_progress: "Đang xử lý",
  pending_review: "Chờ duyệt",
  resolved: "Đã xong",
};

const STATUS_BADGE: Record<string, string> = {
  open: "bg-amber-100 text-amber-800",
  assigned: "bg-indigo-100 text-indigo-800",
  in_progress: "bg-blue-100 text-blue-800",
  pending_review: "bg-purple-100 text-purple-800",
  resolved: "bg-green-100 text-green-800",
};
```

- [ ] **Step 2: Thêm cờ `isManager`**

Sau dòng `const isAdmin = me?.role === "admin";` (dòng 118), thêm:

```typescript
  const isManager = me?.role === "admin" || me?.role === "manager";
```

- [ ] **Step 3: Thêm handler `acceptTask`**

Ngay sau hàm `assignTask` (kết thúc ~dòng 243), thêm:

```typescript
  async function acceptTask(taskId: string) {
    try {
      await apiFetch(`/api/tasks/${taskId}/accept`, { method: "POST" });
      toast.success("Đã nhận việc.");
      setTasks((prev) =>
        prev.map((t) => (t.id === taskId ? { ...t, status: "in_progress" } : t)),
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Lỗi khi nhận việc.");
    }
  }
```

- [ ] **Step 4: Sửa optimistic update của báo cáo hoàn thành**

Trong `submitCompletionReport` đổi (dòng 306-311):

```typescript
      // Nếu báo "completed", backend chuyển task -> resolved; cập nhật UI.
      if ((form.level || "completed") === "completed") {
        setTasks((prev) =>
          prev.map((t) => (t.id === taskId ? { ...t, status: "resolved" } : t)),
        );
      }
```

thành:

```typescript
      // Báo "completed" -> task chuyển sang chờ duyệt (manager sẽ duyệt).
      if ((form.level || "completed") === "completed") {
        setTasks((prev) =>
          prev.map((t) => (t.id === taskId ? { ...t, status: "pending_review" } : t)),
        );
      }
```

- [ ] **Step 5: Badge trạng thái dùng map mới**

Đổi className của badge trạng thái (dòng 517-523):

```typescript
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                          task.status === "open"
                            ? "bg-amber-100 text-amber-800"
                            : task.status === "in_progress"
                              ? "bg-blue-100 text-blue-800"
                              : "bg-green-100 text-green-800"
                        }`}
```

thành:

```typescript
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                          STATUS_BADGE[task.status] ?? "bg-muted text-muted-foreground"
                        }`}
```

- [ ] **Step 6: Thay khối nút trạng thái thủ công bằng hành động theo vai trò**

Đổi khối `{/* Status buttons */}` (dòng 605-627) thành:

```typescript
                    {/* Hành động theo vai trò & trạng thái */}
                    <div className="flex flex-wrap gap-2">
                      {mineTask && task.status === "assigned" && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            acceptTask(task.id);
                          }}
                          className="px-4 py-2 bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 rounded-lg text-xs font-semibold transition-colors"
                        >
                          Nhận việc
                        </button>
                      )}
                      {task.status === "pending_review" && (
                        <span className="px-4 py-2 bg-purple-50 text-purple-700 border border-purple-200 rounded-lg text-xs font-semibold">
                          Chờ quản lý duyệt
                        </span>
                      )}
                    </div>
```

- [ ] **Step 7: Gating "Gán task" chỉ cho manager/admin**

Đổi (dòng 629-630):

```typescript
                    {/* Assignment Section */}
                    <div className="rounded-xl border border-border bg-card p-4 space-y-3">
```

thành:

```typescript
                    {/* Assignment Section — chỉ manager/admin giao việc */}
                    {isManager && (
                    <div className="rounded-xl border border-border bg-card p-4 space-y-3">
```

Và đóng wrapper: đổi (dòng 734-738):

```typescript
                          Gán
                        </button>
                      </div>
                    </div>

                    {/* Báo cáo hoàn thành — chức năng RIÊNG, chỉ hiện cho nhân viên được giao */}
                    {mineTask && (
```

thành:

```typescript
                          Gán
                        </button>
                      </div>
                    </div>
                    )}

                    {/* Báo cáo hoàn thành — chỉ hiện cho nhân viên được giao khi đang xử lý */}
                    {mineTask && task.status === "in_progress" && (
```

- [ ] **Step 8: Người nhận chỉ là staff cùng phòng**

Đổi filter dropdown (dòng 693-698):

```typescript
                            {assignableUsers
                              .filter(
                                (user) =>
                                  user.role === "admin" ||
                                  user.department === task.assigned_team,
                              )
```

thành:

```typescript
                            {assignableUsers
                              .filter(
                                (user) =>
                                  user.role === "staff" &&
                                  user.department === task.assigned_team,
                              )
```

- [ ] **Step 9: Build, xác nhận không lỗi type**

Run: `cd app && npm run build`
Expected: build thành công, không lỗi TypeScript. (`updateTaskStatus` có thể trở thành unused — không sao vì `noUnusedLocals=false`.)

- [ ] **Step 10: Commit**

```bash
git add app/src/routes/_authenticated/tasks.tsx
git commit -m "feat(ui): giao việc manager-only, nút Nhận việc, trạng thái assigned/chờ duyệt

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: Frontend `completion-reports.tsx` — phản ánh trạng thái sau duyệt

**Files:**
- Modify: `app/src/routes/_authenticated/completion-reports.tsx` (hàm `review`, ~dòng 87-100)

**Interfaces:**
- Consumes: `PATCH /api/completion-reports/{id}/review` (nay đổi trạng thái task phía backend).

- [ ] **Step 1: Làm rõ thông báo theo kết quả duyệt**

Trong hàm `review`, đổi dòng toast (dòng 97):

```typescript
      toast.success(status === "approved" ? "Đã duyệt báo cáo." : "Đã trả lại báo cáo.");
```

thành:

```typescript
      toast.success(
        status === "approved"
          ? "Đã duyệt báo cáo — task chuyển sang Đã xong."
          : "Đã trả lại báo cáo — task quay lại Đang xử lý.",
      );
```

- [ ] **Step 2: Build, xác nhận không lỗi**

Run: `cd app && npm run build`
Expected: build thành công.

- [ ] **Step 3: Commit**

```bash
git add app/src/routes/_authenticated/completion-reports.tsx
git commit -m "feat(ui): thông báo duyệt báo cáo phản ánh trạng thái task

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: Apply migrations lên Supabase + verify

**Files:** none (vận hành DB).

> Lý do: triệu chứng "gửi báo cáo không lưu được" do bảng/cột chưa có trên Supabase thật.
> Cần apply cả `20260626000000_task_completion_reports.sql` (nếu chưa) và `20260628000000_...`.

- [ ] **Step 1: Kiểm tra tool DB có sẵn**

Run: `cd /Users/kenz_de/projects/C2-App-116 && scripts/bin/harness-cli query tools --capability database --status present 2>/dev/null || echo "no db capability"`
Nếu không có, dùng Supabase SQL editor / `supabase db push` theo quy trình của dự án.

- [ ] **Step 2: Apply migrations**

Dùng đường đã chuẩn của dự án (một trong số):
- `supabase db push` (nếu CLI link tới project), HOẶC
- dán nội dung 2 file migration vào Supabase SQL editor và chạy.

Thứ tự: `20260626000000_task_completion_reports.sql` trước, rồi `20260628000000_task_events_and_status.sql`.

- [ ] **Step 3: Verify schema trên DB thật**

Chạy SQL:

```sql
SELECT to_regclass('public.task_completion_reports') AS tcr,
       to_regclass('public.task_events') AS events;
SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'tasks_status_check';
```

Expected: `tcr` và `events` đều không NULL; constraint chứa `pending_review` và `assigned`.

- [ ] **Step 4: Smoke test luồng thật (tuỳ chọn, nếu có môi trường staging)**

Đăng nhập manager → giao 1 task cho staff → đăng nhập staff → Nhận việc → gửi báo cáo completed → đăng nhập manager → duyệt. Kiểm tra task = Đã xong và bảng `task_events` có 4 dòng (assigned, accepted, completion_submitted, completion_approved).

---

### Task 14: Regression toàn bộ + verify cuối

**Files:** none (kiểm thử).

- [ ] **Step 1: Toàn bộ test backend**

Run: `cd pipeline && .venv/bin/python -m pytest tests/ -q`
Expected: tất cả PASS, gồm các file mới (`test_task_lifecycle.py`, `test_task_transitions.py`, `test_auth_guard_manager.py`, `test_task_events_helper.py`, `test_migration_task_events.py`) và không regression test cũ (`test_report_endpoint.py`, `test_cockpit_overview.py`, `test_router_agent.py`, `test_classifier.py`...).

- [ ] **Step 2: Build frontend**

Run: `cd app && npm run build`
Expected: build thành công, không lỗi type.

- [ ] **Step 3: Rà gọi API cũ không vỡ**

Run: `cd /Users/kenz_de/projects/C2-App-116 && grep -rn "updateTaskStatus\|/api/tasks/.*/status" app/src/routes/_authenticated/tasks.tsx`
Kiểm tra: không còn nút thủ công gọi `updateTaskStatus` ngoài luồng mới (handler có thể còn định nghĩa nhưng không bị gọi — chấp nhận được).

- [ ] **Step 4: Commit (nếu có chỉnh nhỏ khi verify)**

```bash
cd /Users/kenz_de/projects/C2-App-116 && git add -A
git commit -m "test: verify E2E vòng khép kín giao việc & duyệt hoàn thành task

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Out of scope (tách spec sau)

- Hành động `reassign` chuyên biệt (hiện dùng lại `assign` để đổi owner).
- Timeline sự kiện hiển thị trực tiếp trên card task (endpoint `/events` đã sẵn cho lần sau).
- Endpoint audit tổng hợp toàn phòng `GET /api/task-events?team=`.
- Thông báo realtime/push mới (chỉ thêm bảng vào publication có sẵn).
</content>
