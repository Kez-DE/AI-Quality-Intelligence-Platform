# Điều phối Ticket → Giao việc — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Manager/Admin bấm "Tiếp nhận & Giao việc" ở Phân loại Ticket → tạo/gắn task (gom theo phòng+khu vực) đẩy về Quản lý công việc; task resolved → alert tự đóng. Phân loại Ticket chỉ admin+manager.

**Architecture:** Trích helper `find_or_create_cluster_task` từ `task_agent` (DRY); endpoint `PATCH /api/alerts/{id}/status` đổi `require_manager` + tạo/gắn task khi open→in_progress; task-resolve paths đóng alert liên kết; frontend đổi nav roles + nhãn nút + gate staff.

**Tech Stack:** FastAPI, Supabase, React/TanStack, pytest, vitest.

**Spec:** `docs/superpowers/specs/2026-07-03-ticket-dispatch-to-task-design.md`
**Nhánh:** `feat/real-ticket-workflow` (mở rộng PR #24 — commit tiếp trên nhánh này).

Đã xác minh: `task_agent.cluster_alerts_into_tasks` có logic tìm task `open` theo (team,area) rồi tạo mới (LLM title) + gán task_id (agents/task_agent.py:64-125); endpoint `update_alert_status` (main.py:442, `require_ops_staff`) + task-resolve `update_task_status`/`support_resolve`; nav `/alerts` roles `AUTHENTICATED_ROLES` (AppShell.tsx:64); `require_manager`, `can_view_team`, `alert_department`, `_log_task_event` sẵn có.

---

## Task 1: Trích helper find_or_create_cluster_task (DRY, TDD)

**Files:**
- Modify: `pipeline/agents/task_agent.py` (trích helper, dùng lại trong cluster loop)
- Test: `pipeline/tests/test_cluster_task_helper.py`

**Step 1: Viết test** (fake db: không có open task → insert; có → reuse):
```python
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
```

**Step 2:** Run → FAIL (helper chưa có).

**Step 3: Implement** trong `task_agent.py` (không LLM — nhận title/summary sẵn):
```python
def find_or_create_cluster_task(db, team, area, priority, title, summary=""):
    """Tìm task 'open' cho (team, area) → trả id; chưa có → tạo mới (status open). Không LLM."""
    try:
        res = db.table("tasks").select("id").eq("assigned_team", team).eq("area", area).eq("status", "open").limit(1).execute()
        if res.data:
            return res.data[0]["id"]
    except Exception:
        pass
    ins = db.table("tasks").insert({
        "title": title, "summary": summary, "assigned_team": team, "area": area,
        "topic": "General", "priority": priority or "P2", "status": "open",
    }).execute()
    return ins.data[0]["id"] if ins.data else None
```
Refactor `cluster_alerts_into_tasks` dùng helper cho nhánh tạo mới (giữ LLM title: gọi `find_or_create_cluster_task(db, team, area, prio, llm_title, llm_summary)`).

**Step 4:** Run → PASS. `pytest -k "task or cluster or worker_agent" -q` không vỡ.

**Step 5: Commit**
```bash
git add pipeline/agents/task_agent.py pipeline/tests/test_cluster_task_helper.py
git commit -m "refactor(task): trích find_or_create_cluster_task (DRY, dùng cho endpoint tiếp nhận)"
```

---

## Task 2: Endpoint tiếp nhận → tạo/gắn task + require_manager

**Files:**
- Modify: `pipeline/main.py` (endpoint `update_alert_status`)
- Test: `pipeline/tests/test_alert_status.py` (bổ sung)

**Step 1:** Đổi dependency của `update_alert_status`: `require_ops_staff` → `require_manager`. Trong nhánh transition `open → in_progress`, nếu `not alert.get("task_id")`:
```python
        if new_status == "in_progress" and not alert.get("task_id"):
            from agents.task_agent import find_or_create_cluster_task
            team_for_task = team or "CSKH"
            title = (alert.get("title") or f"Xử lý sự cố {alert.get('topic') or ''}").strip()[:80]
            new_task_id = find_or_create_cluster_task(
                db, team_for_task, alert.get("area"), alert.get("priority"), title,
                alert.get("description", "")[:300])
            if new_task_id:
                patch["task_id"] = new_task_id
```
(Chèn trước khi `db.table("alerts").update(patch)`.)

**Step 2: Test** (bổ sung): transition helper vẫn pass; thêm test khẳng định `update_alert_status` dùng `require_manager` (kiểm signature/deps) — hoặc để E2E Task 5 phủ. Tối thiểu: giữ 2 test transition cũ pass.

**Step 3:** Run `pytest tests/test_alert_status.py -q` + `python -c "import main"`.

**Step 4: Commit**
```bash
git add pipeline/main.py pipeline/tests/test_alert_status.py
git commit -m "feat(alerts): 'Tiếp nhận' (manager/admin) tạo-hoặc-gắn task theo cụm + set task_id"
```

---

## Task 3: Task resolved → tự đóng alert liên kết

**Files:**
- Modify: `pipeline/main.py` (`update_task_status` + `support_resolve`)
- Test: `pipeline/tests/test_task_resolve_syncs_alert.py`

**Step 1:** Viết helper thuần + test (fake db): `_resolve_alerts_for_task(db, task_id, actor)` update alerts `task_id=task_id, status != resolved` → set `status=resolved, resolved_at=now(), resolved_by=actor.id, updated_at=now()`. Test: sink nhận đúng patch + filter.

**Step 2:** Run → FAIL.

**Step 3: Implement** `_resolve_alerts_for_task` + gọi trong `update_task_status` (khi `new_status == "resolved"`) và `support_resolve` (sau khi task→resolved). Bọc try/except (không chặn resolve task nếu sync lỗi).

**Step 4:** Run test + `pytest -k "task or alert" -q`.

**Step 5: Commit**
```bash
git add pipeline/main.py pipeline/tests/test_task_resolve_syncs_alert.py
git commit -m "feat(alerts): task resolved → tự đóng các alert liên kết (đồng bộ đóng)"
```

---

## Task 4: Frontend — RBAC + nhãn nút + gate

**Files:**
- Modify: `app/src/components/AppShell.tsx` (nav `/alerts` roles → `["admin","manager"]`)
- Modify: `app/src/routes/_authenticated/alerts.tsx`

**Step 1:** AppShell.tsx: dòng `{ to: "/alerts", ... roles: AUTHENTICATED_ROLES ... }` → `roles: ["admin", "manager"]`.

**Step 2:** alerts.tsx:
- Gate đầu component: nếu `me?.role` không thuộc `["admin","manager"]` → render "Không đủ quyền" (giống trang admin).
- Nút status `open`: đổi nhãn **"Nhận xử lý" → "Tiếp nhận & Giao việc"**; onClick giữ `updateStatus(id,"in_progress")`.
- Toast sau khi in_progress: đổi thành *"Đã tạo việc cho phòng — xem ở Quản lý công việc"*; thêm link/nút điều hướng `/tasks` (dùng `Link` hoặc `router.navigate`).
- Giữ nút `in_progress→resolved` nhãn "Đóng ticket".

**Step 3: Verify**
```bash
cd app && npx tsc --noEmit && npx vite build
```

**Step 4: Commit**
```bash
git add app/src/components/AppShell.tsx app/src/routes/_authenticated/alerts.tsx
git commit -m "feat(alerts-ui): Phân loại Ticket chỉ admin+manager; nút 'Tiếp nhận & Giao việc' + link Quản lý công việc"
```

---

## Task 5: E2E thật + full verify + cập nhật PR #24

**Step 1: E2E** (TestClient + JWT admin): tạo alert open (phòng CSKH, có user_id) → PATCH in_progress → có `task_id`; GET /api/tasks thấy task status open đúng team; PATCH task→resolved → alert thành resolved (resolved_at set). Alert thứ 2 cùng (team,area) → gắn CÙNG task. Cleanup.

**Step 2:** `pytest -q` xanh; `cd app && npx tsc --noEmit` + build.

**Step 3:** `git push`; `gh pr edit 24 --title/--body` cập nhật: PR #24 giờ là "workflow ticket thật + điều phối→giao việc".

## Thứ tự
1 (helper) → 2 (endpoint tiếp nhận) → 3 (task→alert sync) → 4 (frontend) → 5 (E2E+PR).

## Verify tổng
- Staff: 403 khi PATCH alert status + không thấy nav /alerts.
- Manager "Tiếp nhận" → alert in_progress + task_id; task ở Quản lý công việc (open) đúng cụm; alert cùng cụm gắn cùng task.
- Resolve task → alert đóng.
- pytest + tsc + build sạch.
