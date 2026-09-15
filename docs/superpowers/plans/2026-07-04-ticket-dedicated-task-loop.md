# Ticket → Dedicated Task Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** "Tiếp nhận & Giao việc" đẩy một task DÀNH RIÊNG (1:1) cho ticket (`source='ticket'`); duyệt hoàn thành tự resolve ticket; badge "Từ ticket" ở frontend.

**Architecture:** Backend FastAPI (`pipeline/`) + Supabase (shared cloud DB cho cả local lẫn Railway). Frontend React/TanStack (`app/`). Ticket = row bảng `alerts`; Task = row bảng `tasks`; liên kết qua `alerts.task_id`.

**Tech Stack:** Python 3.12 + FastAPI + supabase-py, pytest; React + Vite + TypeScript; Supabase Postgres.

## Global Constraints

- 6 phòng ban chuẩn (không đổi): IT, CSKH, Vận hành, Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận.
- Local và Railway **dùng chung 1 cloud Supabase** → migration/data áp 1 lần là live cả hai.
- Đẩy **thẳng `main`** (không qua branch); Railway auto-deploy từ main.
- Test backend chạy trong `pipeline/.venv` (đã có deps): `cd pipeline && source .venv/bin/activate`.
- Không đụng `find_or_create_cluster_task` và worker clustering (luồng `agent` cũ giữ nguyên).

---

### Task 1: Migration — cho phép `tasks.source = 'ticket'`

**Files:**
- Create: `supabase/migrations/20260704130000_tasks_source_ticket.sql`

**Interfaces:**
- Produces: bảng `tasks` chấp nhận `source IN ('agent','report','ticket')`.

- [ ] **Step 1: Viết migration**

`supabase/migrations/20260704130000_tasks_source_ticket.sql`:
```sql
-- Cho phép task đẩy trực tiếp từ Phân loại Ticket (source='ticket'), tách khỏi luồng
-- agent tự sinh và report dispatch.
ALTER TABLE public.tasks DROP CONSTRAINT IF EXISTS tasks_source_check;
ALTER TABLE public.tasks ADD CONSTRAINT tasks_source_check
  CHECK (source IN ('agent','report','ticket'));
```

- [ ] **Step 2: Áp migration lên cloud DB**

Áp bằng Supabase MCP `apply_migration` (name `tasks_source_ticket`, query = nội dung file trên), hoặc `supabase db push`, hoặc dán vào Supabase SQL editor. KHÔNG áp được qua PostgREST REST (không chạy DDL).

- [ ] **Step 3: Verify constraint đã mở**

```bash
cd /Users/kenz_de/projects/AI-Quality-Intelligence-Platform && set -a && . ./.env && set +a
BASE="$SUPABASE_URL/rest/v1"; H="apikey: $SUPABASE_SERVICE_ROLE_KEY"; A="Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"
# Lấy 1 user_id + insert thử task source='ticket' rồi xoá
UID=$(curl -s "$BASE/profiles?select=id&limit=1" -H "$H" -H "$A" | python3 -c "import sys,json;print(json.load(sys.stdin)[0]['id'])")
curl -s -X POST "$BASE/tasks" -H "$H" -H "$A" -H "Content-Type: application/json" -H "Prefer: return=representation" \
  -d '{"title":"__mig_test__","assigned_team":"CSKH","area":"HN-Cau-Giay","priority":"P3","status":"open","source":"ticket"}' \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('OK' if isinstance(d,list) and d else d)"
```
Expected: in ra `OK` (không lỗi constraint). Sau đó xoá row test:
```bash
curl -s -X DELETE "$BASE/tasks?title=eq.__mig_test__" -H "$H" -H "$A" -o /dev/null -w "deleted %{http_code}\n"
```

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/20260704130000_tasks_source_ticket.sql
git commit -m "feat(db): cho phép tasks.source='ticket' (task đẩy từ ticket)"
```

---

### Task 2: `create_ticket_task` — luôn tạo task riêng 1:1

**Files:**
- Modify: `pipeline/agents/task_agent.py` (thêm hàm mới, cạnh `find_or_create_cluster_task`)
- Test: `pipeline/tests/test_create_ticket_task.py`

**Interfaces:**
- Produces: `create_ticket_task(db, team, area, priority, title, summary="") -> str | None` — LUÔN insert task mới `source='ticket'`, trả `id`.

- [ ] **Step 1: Viết failing test**

`pipeline/tests/test_create_ticket_task.py`:
```python
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
    assert t1 and t2                      # luôn trả id
    assert len(db.sink) == 2              # LUÔN insert (không tái dùng cụm)
    assert all(r["source"] == "ticket" for r in db.sink)
    assert db.sink[0]["assigned_team"] == "CSKH" and db.sink[0]["status"] == "open"
```

- [ ] **Step 2: Chạy test để chắc nó fail**

Run: `cd pipeline && source .venv/bin/activate && python -m pytest tests/test_create_ticket_task.py -q`
Expected: FAIL — `ImportError: cannot import name 'create_ticket_task'`.

- [ ] **Step 3: Viết hàm**

Thêm vào `pipeline/agents/task_agent.py` ngay sau `find_or_create_cluster_task`:
```python
def create_ticket_task(db, team, area, priority, title, summary=""):
    """LUÔN tạo task MỚI dành riêng cho 1 ticket (source='ticket', gắn 1:1 với alert).
    Khác find_or_create_cluster_task: không tái dùng task cụm."""
    ins = db.table("tasks").insert({
        "title": title, "summary": summary, "assigned_team": team, "area": area,
        "topic": "General", "priority": priority or "P2", "status": "open",
        "source": "ticket",
    }).execute()
    return ins.data[0]["id"] if ins.data else None
```

- [ ] **Step 4: Chạy test để chắc pass**

Run: `python -m pytest tests/test_create_ticket_task.py -q`
Expected: PASS (2 assertions).

- [ ] **Step 5: Commit**

```bash
git add pipeline/agents/task_agent.py pipeline/tests/test_create_ticket_task.py
git commit -m "feat(task): create_ticket_task tạo task riêng 1:1 cho ticket (source='ticket')"
```

---

### Task 3: "Tiếp nhận" dùng `create_ticket_task`

**Files:**
- Modify: `pipeline/main.py` — block trong `update_alert_status` (hiện dòng ~522-530)

**Interfaces:**
- Consumes: `create_ticket_task` (Task 2).

- [ ] **Step 1: Đổi block tạo task khi Tiếp nhận**

Trong `pipeline/main.py`, tìm block hiện tại:
```python
        # Tiếp nhận (open→in_progress): tạo/gắn task cho cụm (phòng, khu vực) để manager giao việc.
        if new_status == "in_progress" and not alert.get("task_id"):
            from agents.task_agent import find_or_create_cluster_task
            team_for_task = team or "CSKH"
            title = (alert.get("title") or f"Xử lý sự cố {alert.get('topic') or ''}").strip()[:80]
            new_task_id = find_or_create_cluster_task(
                db, team_for_task, alert.get("area"), alert.get("priority"),
                title, (alert.get("description") or "")[:300])
            if new_task_id:
                patch["task_id"] = new_task_id
```
Thay bằng:
```python
        # Tiếp nhận (open→in_progress): tạo task DÀNH RIÊNG cho ticket (1:1) để manager giao việc.
        if new_status == "in_progress" and not alert.get("task_id"):
            from agents.task_agent import create_ticket_task
            team_for_task = team or "CSKH"
            title = (alert.get("title") or f"Xử lý sự cố {alert.get('topic') or ''}").strip()[:80]
            new_task_id = create_ticket_task(
                db, team_for_task, alert.get("area"), alert.get("priority"),
                title, (alert.get("description") or "")[:300])
            if new_task_id:
                patch["task_id"] = new_task_id
```

- [ ] **Step 2: Verify không hồi quy (import + suite alert/task)**

Run: `cd pipeline && source .venv/bin/activate && python -c "import main" && python -m pytest tests/test_alert_status.py tests/test_cluster_task_helper.py -q`
Expected: import OK, tests PASS (find_or_create_cluster_task cũ vẫn nguyên).

- [ ] **Step 3: Commit**

```bash
git add pipeline/main.py
git commit -m "feat(alerts): Tiếp nhận tạo task riêng cho ticket thay vì tái dùng task cụm"
```

---

### Task 4: Fix `review_completion_report` — duyệt → resolve ticket

**Files:**
- Modify: `pipeline/main.py` — `review_completion_report` (hiện ~1104-1124)
- Test: `pipeline/tests/test_review_report_resolves_alert.py`

**Interfaces:**
- Consumes: `_resolve_alerts_for_task(db, task_id, actor)` (đã có, `main.py:583`).

- [ ] **Step 1: Viết failing test**

`pipeline/tests/test_review_report_resolves_alert.py`:
```python
"""Duyệt (approved) báo cáo hoàn thành → task resolved → resolve luôn ticket liên kết."""
import types
import main


def test_approve_calls_resolve_alerts(monkeypatch):
    calls = {}

    # Spy _resolve_alerts_for_task
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
```

- [ ] **Step 2: Chạy test để chắc fail**

Run: `cd pipeline && source .venv/bin/activate && python -m pytest tests/test_review_report_resolves_alert.py -q`
Expected: `test_approve_calls_resolve_alerts` FAIL (assert resolved_task == 'task-9' nhưng chưa gọi).

- [ ] **Step 3: Thêm gọi `_resolve_alerts_for_task` khi approved**

Trong `pipeline/main.py` `review_completion_report`, ngay sau block cập nhật task status (sau `to_status = target`) và trước `_log_task_event`, thêm:
```python
        if payload.status == "approved" and to_status == "resolved":
            _resolve_alerts_for_task(db, rep_task_id, user)  # ticket liên kết tự tick 'Đã xong'
```
(Đặt trong khối `try`, cùng cấp thụt lề với các lệnh `db.table(...)` phía trên.)

- [ ] **Step 4: Chạy test để chắc pass**

Run: `python -m pytest tests/test_review_report_resolves_alert.py -q`
Expected: PASS (cả 2 test).

- [ ] **Step 5: Commit**

```bash
git add pipeline/main.py pipeline/tests/test_review_report_resolves_alert.py
git commit -m "fix(reports): duyệt hoàn thành → resolve ticket liên kết (khép kín loop)"
```

---

### Task 5: Frontend — badge "🎫 Từ ticket"

**Files:**
- Modify: `app/src/routes/_authenticated/tasks.tsx` (badge source, hiện dòng ~547)

**Interfaces:**
- Consumes: `task.source` (đã có trong type Task, `tasks.tsx:43`).

- [ ] **Step 1: Mở rộng badge cho source='ticket'**

Trong `app/src/routes/_authenticated/tasks.tsx`, thay:
```tsx
                      <span className="px-2 py-0.5 rounded bg-muted text-[10px] uppercase font-mono border border-border">
                        {task.source === "report" ? "Từ báo cáo" : "Từ cảnh báo"}
                      </span>
```
bằng:
```tsx
                      <span className="px-2 py-0.5 rounded bg-muted text-[10px] uppercase font-mono border border-border">
                        {task.source === "ticket"
                          ? "🎫 Từ ticket"
                          : task.source === "report"
                            ? "Từ báo cáo"
                            : "Từ cảnh báo"}
                      </span>
```

- [ ] **Step 2: Typecheck + build**

Run: `cd app && npx tsc --noEmit && npm run build`
Expected: tsc 0 lỗi, build thành công.

- [ ] **Step 3: Commit**

```bash
git add app/src/routes/_authenticated/tasks.tsx
git commit -m "feat(tasks-ui): badge 'Từ ticket' cho task source='ticket'"
```

---

### Task 6: Verify end-to-end thật (local + Railway) + push

**Files:** none (kịch bản kiểm thử trên DB thật)

- [ ] **Step 1: Push toàn bộ lên main**

```bash
cd /Users/kenz_de/projects/AI-Quality-Intelligence-Platform && git push origin main
```

- [ ] **Step 2: Chạy loop thật trên shared DB**

`cd pipeline && source .venv/bin/activate && python`:
```python
from agents.common import get_db
from agents.task_agent import create_ticket_task
import types, datetime
db = get_db()
uid = db.table("alerts").select("user_id").not_.is_("user_id","null").limit(1).execute().data[0]["user_id"]
# 1) tạo ticket open
a = db.table("alerts").insert({"user_id":uid,"title":"E2E ticket "+datetime.datetime.now().strftime("%H%M%S"),
    "description":"P3 test","area":"HN-Cau-Giay","assigned_team":"CSKH","topic":"Other","priority":"P3","severity":"P3","status":"open"}).execute().data[0]
# 2) Tiếp nhận: tạo task riêng + gắn task_id (mô phỏng endpoint)
tid = create_ticket_task(db,"CSKH",a["area"],a["priority"],a["title"],"E2E")
db.table("alerts").update({"status":"in_progress","task_id":tid,"in_progress_at":"now()","updated_at":"now()"}).eq("id",a["id"]).execute()
t = db.table("tasks").select("id,source,status").eq("id",tid).execute().data[0]
print("task:", t, "-> source=ticket?", t["source"]=="ticket")
# 3) mô phỏng duyệt: task resolved + resolve alert
import main
main._resolve_alerts_for_task(db, tid, types.SimpleNamespace(id=uid))
db.table("tasks").update({"status":"resolved","updated_at":"now()"}).eq("id",tid).execute()
al = db.table("alerts").select("status,task_id").eq("id",a["id"]).execute().data[0]
print("ticket sau duyệt:", al, "-> Đã xong?", al["status"]=="resolved")
# dọn
db.table("alerts").delete().eq("id",a["id"]).execute()
db.table("tasks").delete().eq("id",tid).execute()
print("cleaned up")
```
Expected: `source=ticket? True` và `Đã xong? True`.

- [ ] **Step 3: Verify Railway deploy + code mới live**

```bash
set -a && . /Users/kenz_de/projects/AI-Quality-Intelligence-Platform/.env && set +a
railway deployment list --service backend | head -2   # chờ SUCCESS cho commit mới
curl -s -m 15 https://backend-production-2f4d.up.railway.app/ -o /dev/null -w "health %{http_code}\n"
```
Expected: deploy mới SUCCESS, health 200. Frontend service cũng SUCCESS.

- [ ] **Step 4: Full backend suite (không hồi quy)**

Run: `cd pipeline && source .venv/bin/activate && python -m pytest -q`
Expected: all pass (191+ passed).

---

## Self-Review (đã chạy)

- **Spec coverage:** migration (T1) ✓, create_ticket_task 1:1 (T2) ✓, Tiếp nhận dùng hàm mới (T3) ✓, fix duyệt→resolve (T4) ✓, badge frontend (T5) ✓, verify local+Railway+push (T6) ✓.
- **Placeholder scan:** không có TBD/TODO; mọi step có code/command thật.
- **Type consistency:** `create_ticket_task(db, team, area, priority, title, summary)` khớp giữa T2 (định nghĩa) và T3 (gọi); `_resolve_alerts_for_task(db, task_id, actor)` khớp T4 với `main.py:583`.
