# HI-Loop Approval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho phép Manager biến danh sách action item trong báo cáo AI thành Task chính thức bằng một nút duyệt, có liên kết ngược về báo cáo gốc.

**Architecture:** Thêm 2 cột vào `department_reports` (`suggested_tasks` JSONB, `root_cause_summary`) và 2 cột vào `tasks` (`report_id`, `source`). Một Postgres RPC `approve_report_and_dispatch` làm việc duyệt + tạo task trong một transaction. Hai endpoint mới (`PUT draft-tasks`, `POST approve-and-dispatch`) và UI editor trên `reports.tsx`.

**Tech Stack:** FastAPI (Python), Supabase (PostgREST client + plpgsql RPC), React 19 + TanStack Start, pytest/unittest.

## Global Constraints

- Migration mới PHẢI là `20260627000000_suggested_tasks_and_report_link.sql`. KHÔNG dùng `20260626000000` (đã có `task_completion_reports.sql`).
- 4 phòng ban hợp lệ: `IT`, `CSKH`, `Vận hành`, `Marketing`.
- Backend chạy bằng service role (bypass RLS). Gate quyền ở API bằng `can_view_team(user, report.team)`. KHÔNG sửa RLS trong plan này.
- `tasks.source` chỉ nhận `'agent'` hoặc `'report'`, default `'agent'`. Task cũ giữ `'agent'`.
- Atomicity của duyệt + tạo task PHẢI qua RPC `approve_report_and_dispatch`, KHÔNG dùng try/except bù trừ ở app.
- Parse deadline ở Python (`parse_deadline`), token hợp lệ: `Nh`, `Nd`, `Nw` (vd `1h`, `24h`, `48h`, `7d`, `1w`); không khớp → default 48h.
- Giữ nguyên `PATCH /api/reports/{id}/approve` cũ (backward compatibility).
- RBAC import có sẵn: `from auth_guard import AuthUser, can_view_team, get_current_user, require_admin, require_ops_staff, scoped_team`.
- Endpoint pattern: fetch row → kiểm `can_view_team` → thao tác trong try/except → raise `HTTPException(503, ...)` khi lỗi DB.
- Frontend gọi API qua `apiFetch` (`@/lib/api`), toast qua `sonner`.
- Mọi commit kết thúc bằng `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Test chạy: `cd pipeline && python -m pytest tests/ -q` (các test hiện dùng `unittest`, pytest chạy được).

---

### Task 1: DB migration + RPC

**Files:**
- Create: `supabase/migrations/20260627000000_suggested_tasks_and_report_link.sql`

**Interfaces:**
- Produces: cột `department_reports.suggested_tasks` (jsonb), `department_reports.root_cause_summary` (text), `tasks.report_id` (uuid fk), `tasks.source` (text), và RPC `approve_report_and_dispatch(p_report_id uuid, p_tasks jsonb, p_approver uuid) RETURNS integer`.

- [ ] **Step 1: Viết file migration**

Create `supabase/migrations/20260627000000_suggested_tasks_and_report_link.sql`:

```sql
-- HI-Loop Approval: liên kết báo cáo -> task có cấu trúc.
-- Lưu ý: 20260626000000 đã dùng cho task_completion_reports nên file này là 20260627000000.

ALTER TABLE public.department_reports
  ADD COLUMN IF NOT EXISTS suggested_tasks JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS root_cause_summary TEXT;

ALTER TABLE public.tasks
  ADD COLUMN IF NOT EXISTS report_id UUID REFERENCES public.department_reports(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'agent';

ALTER TABLE public.tasks DROP CONSTRAINT IF EXISTS tasks_source_check;
ALTER TABLE public.tasks ADD CONSTRAINT tasks_source_check CHECK (source IN ('agent','report'));

CREATE INDEX IF NOT EXISTS idx_tasks_report_id ON public.tasks(report_id);

-- Duyệt báo cáo + tạo task trong MỘT transaction (atomic).
-- p_tasks: jsonb array, mỗi item có {action, priority, success_metric, due_at(ISO|null)}.
CREATE OR REPLACE FUNCTION public.approve_report_and_dispatch(
  p_report_id uuid,
  p_tasks jsonb,
  p_approver uuid
) RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
  v_team text;
  v_updated int;
  v_created int := 0;
BEGIN
  UPDATE public.department_reports
    SET approved = true,
        approved_by = p_approver,
        approved_at = now(),
        suggested_tasks = p_tasks
    WHERE id = p_report_id AND approved = false
    RETURNING team INTO v_team;

  GET DIAGNOSTICS v_updated = ROW_COUNT;
  IF v_updated = 0 THEN
    RAISE EXCEPTION 'report_not_found_or_already_approved';
  END IF;

  INSERT INTO public.tasks
    (title, summary, assigned_team, priority, status, source, report_id, due_at)
  SELECT
    COALESCE(NULLIF(t->>'action', ''), 'Hành động chưa đặt tên'),
    t->>'success_metric',
    v_team,
    COALESCE(NULLIF(t->>'priority', ''), 'P3'),
    'open',
    'report',
    p_report_id,
    CASE WHEN COALESCE(t->>'due_at','') <> '' THEN (t->>'due_at')::timestamptz ELSE NULL END
  FROM jsonb_array_elements(p_tasks) AS t;

  GET DIAGNOSTICS v_created = ROW_COUNT;
  RETURN v_created;
END;
$$;
```

- [ ] **Step 2: Apply migration lên Supabase**

Run: `supabase db push` (hoặc dán file SQL vào Supabase SQL editor nếu CLI chưa link).
Expected: chạy không lỗi.

- [ ] **Step 3: Verify schema**

Run (Supabase SQL editor hoặc psql):
```sql
SELECT column_name FROM information_schema.columns
WHERE table_name='department_reports' AND column_name IN ('suggested_tasks','root_cause_summary');
SELECT column_name FROM information_schema.columns
WHERE table_name='tasks' AND column_name IN ('report_id','source');
SELECT proname FROM pg_proc WHERE proname='approve_report_and_dispatch';
```
Expected: thấy đủ 2 + 2 cột và 1 function.

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/20260627000000_suggested_tasks_and_report_link.sql
git commit -m "feat(db): suggested_tasks, report_id, source + approve_report_and_dispatch RPC

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Agent ghi suggested_tasks + root_cause_summary vào DB

**Files:**
- Modify: `pipeline/agents/report_builder.py` (hàm `store_department_report`)
- Modify: `pipeline/agents/orchestrator.py` (chỗ gọi `store_department_report`, quanh dòng 124-130)

**Interfaces:**
- Consumes: `analysis_res` (dict từ `analyze_root_cause`) có shape `{"status", "analysis": {"root_cause_summary", "action_items": [ {action, deadline, owner, success_metric, priority} ]}}`.
- Produces: `store_department_report(db, *, team, report_date, content, suggested_tasks=None, root_cause_summary=None)`.

- [ ] **Step 1: Sửa `store_department_report` nhận 2 tham số mới**

Trong `pipeline/agents/report_builder.py`, đổi signature và payload:

```python
def store_department_report(
    db,
    *,
    team: str,
    report_date: str,
    content: str,
    suggested_tasks: list | None = None,
    root_cause_summary: str | None = None,
) -> dict[str, Any]:
    """Store one daily report without overwriting a manager-approved snapshot."""
    existing = (
        db.table("department_reports")
        .select("id,approved")
        .eq("team", team)
        .eq("report_date", report_date)
        .limit(1)
        .execute()
        .data
        or []
    )
    if existing and existing[0].get("approved"):
        return {"stored": False, "reason": "approved_report_locked", "id": existing[0].get("id")}

    payload = {
        "team": team,
        "report_date": report_date,
        "content": content,
        "approved": False,
        "approved_by": None,
        "approved_at": None,
        "suggested_tasks": suggested_tasks or [],
        "root_cause_summary": root_cause_summary,
    }
    result = db.table("department_reports").upsert(
        payload,
        on_conflict="team,report_date",
    ).execute()
    return {"stored": True, "data": result.data or []}
```

- [ ] **Step 2: Truyền data từ analyst tại call site trong orchestrator**

Trong `pipeline/agents/orchestrator.py`, tìm dòng gọi `store_department_report(` (khoảng dòng 126). Ngay TRƯỚC lời gọi đó, trích action_items + root_cause từ `analysis_res`, rồi thêm 2 tham số vào lời gọi:

```python
            _analysis = (analysis_res.get("analysis") or {}) if isinstance(analysis_res, dict) else {}
            _suggested = _analysis.get("action_items") or []
            _root_cause = _analysis.get("root_cause_summary") or None
            store_result = store_department_report(
                db,
                team=team,
                report_date=report_date,
                content=md,
                suggested_tasks=_suggested,
                root_cause_summary=_root_cause,
            )
```

Giữ nguyên tên biến `db`, `report_date`, `md` đang dùng tại call site (chỉ thêm 3 dòng trích xuất + 2 tham số). Nếu call site dùng tên biến khác cho db handle, dùng đúng tên đó.

- [ ] **Step 3: Verify import không vỡ**

Run: `cd pipeline && python -c "from agents.report_builder import store_department_report; from agents import orchestrator; print('ok')"`
Expected: in `ok`, không traceback.

- [ ] **Step 4: Verify pipeline ghi JSONB (cần backend + LLM key local, hoặc mock)**

Run: gọi `POST /api/agent/run` (token admin) HOẶC `cd pipeline && python -m agents.orchestrator`.
Then (Supabase SQL editor):
```sql
SELECT team, jsonb_typeof(suggested_tasks) AS t, root_cause_summary IS NOT NULL AS has_rc
FROM department_reports ORDER BY created_at DESC LIMIT 4;
```
Expected: `t='array'`; với phòng có feedback và analyst chạy, `has_rc=true`.

- [ ] **Step 5: Commit**

```bash
git add pipeline/agents/report_builder.py pipeline/agents/orchestrator.py
git commit -m "feat(agent): persist suggested_tasks + root_cause_summary vào department_reports

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: API — PUT /api/reports/{id}/draft-tasks

**Files:**
- Modify: `pipeline/main.py` (thêm request model gần các class `*Req` dòng ~33-56, và endpoint gần `approve_report` dòng ~458)

**Interfaces:**
- Produces: `PUT /api/reports/{report_id}/draft-tasks`, body `{"suggested_tasks": [...]}`.

- [ ] **Step 1: Thêm request model**

Trong `pipeline/main.py`, cạnh các class `*Req` (sau `ReviewReportReq`):

```python
class DraftTasksReq(BaseModel):
    suggested_tasks: list[dict]
```

- [ ] **Step 2: Thêm endpoint (đặt ngay sau `approve_report`)**

```python
@app.put("/api/reports/{report_id}/draft-tasks")
def update_draft_tasks(
    report_id: str,
    payload: DraftTasksReq,
    user: AuthUser = Depends(require_ops_staff),
):
    """Manager lưu nháp danh sách Draft Task. 409 nếu báo cáo đã duyệt."""
    db = get_supabase()
    existing = db.table("department_reports").select("team,approved").eq("id", report_id).limit(1).execute().data or []
    if not existing:
        raise HTTPException(status_code=404, detail="Report not found")
    if not can_view_team(user, existing[0].get("team")):
        raise HTTPException(status_code=403, detail="Bạn không có quyền sửa báo cáo của phòng ban khác.")
    if existing[0].get("approved"):
        raise HTTPException(status_code=409, detail="Báo cáo đã duyệt, không thể sửa.")
    try:
        data = db.table("department_reports").update(
            {"suggested_tasks": payload.suggested_tasks}
        ).eq("id", report_id).eq("approved", False).execute().data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot save draft: {str(exc)[:300]}") from exc
    if not data:
        raise HTTPException(status_code=409, detail="Báo cáo đã duyệt, không thể sửa.")
    return {"status": "success", "data": data[0]}
```

- [ ] **Step 3: Verify endpoint nạp được**

Run: `cd pipeline && python -c "import main; print([r.path for r in main.app.routes if 'draft-tasks' in getattr(r,'path','')])"`
Expected: in `['/api/reports/{report_id}/draft-tasks']`.

- [ ] **Step 4: Verify thủ công bằng curl (backend chạy local, token manager)**

```bash
curl -s -X PUT "http://127.0.0.1:8000/api/reports/<REPORT_ID>/draft-tasks" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"suggested_tasks":[{"action":"Test","priority":"P2","deadline":"24h"}]}'
```
Expected: `200` với `data.suggested_tasks` = mảng vừa gửi. Gọi lại sau khi report `approved=true` → `409`.

- [ ] **Step 5: Commit**

```bash
git add pipeline/main.py
git commit -m "feat(api): PUT /api/reports/{id}/draft-tasks (lock 409 khi approved)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: API — POST /api/reports/{id}/approve-and-dispatch (qua RPC) + parse_deadline

**Files:**
- Create: `pipeline/dispatch_utils.py`
- Modify: `pipeline/main.py` (import + request model + endpoint)
- Test: `pipeline/tests/test_dispatch_utils.py`

**Interfaces:**
- Consumes: RPC `approve_report_and_dispatch` (Task 1).
- Produces: `parse_deadline(deadline: str | None) -> datetime`; `POST /api/reports/{report_id}/approve-and-dispatch`, body `{"suggested_tasks": [...]}`.

- [ ] **Step 1: Viết test thất bại cho `parse_deadline`**

Create `pipeline/tests/test_dispatch_utils.py`:

```python
import os, sys, unittest
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dispatch_utils import parse_deadline


class TestParseDeadline(unittest.TestCase):
    def _hours_from_now(self, dt: datetime) -> float:
        return (dt - datetime.now(timezone.utc)).total_seconds() / 3600

    def test_hours(self):
        self.assertAlmostEqual(self._hours_from_now(parse_deadline("24h")), 24, delta=0.1)

    def test_days(self):
        self.assertAlmostEqual(self._hours_from_now(parse_deadline("7d")), 168, delta=0.1)

    def test_weeks(self):
        self.assertAlmostEqual(self._hours_from_now(parse_deadline("1w")), 168, delta=0.1)

    def test_none_defaults_48h(self):
        self.assertAlmostEqual(self._hours_from_now(parse_deadline(None)), 48, delta=0.1)

    def test_garbage_defaults_48h(self):
        self.assertAlmostEqual(self._hours_from_now(parse_deadline("ngay mai")), 48, delta=0.1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd pipeline && python -m pytest tests/test_dispatch_utils.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'dispatch_utils'`).

- [ ] **Step 3: Viết `dispatch_utils.py`**

Create `pipeline/dispatch_utils.py`:

```python
import re
from datetime import datetime, timedelta, timezone

_DEFAULT = timedelta(hours=48)


def parse_deadline(deadline: str | None) -> datetime:
    """Đổi token '1h'/'24h'/'7d'/'1w' thành thời điểm tuyệt đối. Không khớp -> +48h."""
    now = datetime.now(timezone.utc)
    if not deadline:
        return now + _DEFAULT
    m = re.fullmatch(r"\s*(\d+)\s*([hdw])\s*", deadline.strip().lower())
    if not m:
        return now + _DEFAULT
    n, unit = int(m.group(1)), m.group(2)
    if unit == "h":
        return now + timedelta(hours=n)
    if unit == "d":
        return now + timedelta(days=n)
    return now + timedelta(weeks=n)
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `cd pipeline && python -m pytest tests/test_dispatch_utils.py -q`
Expected: 5 passed.

- [ ] **Step 5: Thêm import + request model + endpoint vào `main.py`**

Thêm import (cạnh các import đầu file):
```python
from dispatch_utils import parse_deadline
```

Thêm request model (cạnh `DraftTasksReq`):
```python
class ApproveDispatchReq(BaseModel):
    suggested_tasks: list[dict]
```

Thêm endpoint (sau `update_draft_tasks`):
```python
@app.post("/api/reports/{report_id}/approve-and-dispatch")
def approve_and_dispatch(
    report_id: str,
    payload: ApproveDispatchReq,
    user: AuthUser = Depends(require_ops_staff),
):
    """Duyệt báo cáo + tạo task chính thức (atomic qua RPC)."""
    db = get_supabase()
    existing = db.table("department_reports").select("team,approved").eq("id", report_id).limit(1).execute().data or []
    if not existing:
        raise HTTPException(status_code=404, detail="Report not found")
    if not can_view_team(user, existing[0].get("team")):
        raise HTTPException(status_code=403, detail="Bạn không có quyền duyệt báo cáo của phòng ban khác.")
    if existing[0].get("approved"):
        raise HTTPException(status_code=409, detail="Báo cáo đã được duyệt.")

    enriched = []
    for t in payload.suggested_tasks:
        item = dict(t)
        item["due_at"] = parse_deadline(item.get("deadline")).isoformat()
        enriched.append(item)

    try:
        res = db.rpc("approve_report_and_dispatch", {
            "p_report_id": report_id,
            "p_tasks": enriched,
            "p_approver": user.id,
        }).execute()
        tasks_created = res.data if isinstance(res.data, int) else (res.data or 0)
    except Exception as exc:
        if "report_not_found_or_already_approved" in str(exc):
            raise HTTPException(status_code=409, detail="Báo cáo đã được duyệt.") from exc
        raise HTTPException(status_code=503, detail=f"Cannot dispatch: {str(exc)[:300]}") from exc

    report = db.table("department_reports").select("*").eq("id", report_id).limit(1).execute().data or []
    return {"status": "success", "tasks_created": tasks_created, "report": report[0] if report else None}
```

- [ ] **Step 6: Verify endpoint nạp được + curl E2E**

Run: `cd pipeline && python -c "import main; print(any('approve-and-dispatch' in getattr(r,'path','') for r in main.app.routes))"`
Expected: `True`.

Curl (backend local, token manager, report chưa duyệt):
```bash
curl -s -X POST "http://127.0.0.1:8000/api/reports/<REPORT_ID>/approve-and-dispatch" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"suggested_tasks":[{"action":"Rà soát ticket","priority":"P2","deadline":"24h"}]}'
```
Expected: `200`, `tasks_created>=1`. Kiểm DB:
```sql
SELECT title, source, report_id, due_at FROM tasks WHERE report_id='<REPORT_ID>';
```
Expected: task có `source='report'`, `report_id` đúng, `due_at` ~ +24h. Gọi POST lần 2 → `409`.

- [ ] **Step 7: Commit**

```bash
git add pipeline/dispatch_utils.py pipeline/tests/test_dispatch_utils.py pipeline/main.py
git commit -m "feat(api): POST approve-and-dispatch qua RPC + parse_deadline (TDD)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: UI — reports.tsx Draft Task Editor + Approve-and-Dispatch

**Files:**
- Modify: `app/src/routes/_authenticated/reports.tsx`

**Interfaces:**
- Consumes: `PUT /api/reports/{id}/draft-tasks`, `POST /api/reports/{id}/approve-and-dispatch`, `GET /api/tasks?team=<team>&status=open`.

- [ ] **Step 1: Đọc file hiện tại để biết cấu trúc**

Run: đọc `app/src/routes/_authenticated/reports.tsx` (299 dòng). Xác định: type `Report`, nơi render Markdown, nơi có nút Duyệt cũ, cách dùng `apiFetch` và `toast`.

- [ ] **Step 2: Mở rộng type `Report` + thêm type `DraftTask`**

Thêm/sửa trong reports.tsx:
```tsx
type DraftTask = {
  action: string;
  priority?: string;
  deadline?: string;
  owner?: string;
  success_metric?: string;
};
// Trong type Report, thêm:
//   suggested_tasks?: DraftTask[];
//   root_cause_summary?: string | null;
//   approved?: boolean;
//   approved_by?: string | null;
//   approved_at?: string | null;
```

- [ ] **Step 3: Thêm component editor (cùng file, trên component trang)**

```tsx
import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";

function DraftTaskEditor({
  report,
  onApproved,
}: {
  report: { id: string; team: string; suggested_tasks?: DraftTask[]; approved?: boolean };
  onApproved: () => void;
}) {
  const [tasks, setTasks] = useState<DraftTask[]>(report.suggested_tasks ?? []);
  const [openTasks, setOpenTasks] = useState<{ title: string }[]>([]);
  const [busy, setBusy] = useState(false);

  // Hiện task open hiện có của phòng để Manager tránh đặt trùng.
  async function loadOpenTasks() {
    try {
      const j = await apiFetch<{ data: { title: string }[] }>(
        `/api/tasks?team=${encodeURIComponent(report.team)}&status=open&limit=50`,
      );
      setOpenTasks(j.data ?? []);
    } catch {
      /* không chặn editor nếu lỗi */
    }
  }

  function update(i: number, field: keyof DraftTask, value: string) {
    setTasks((prev) => prev.map((t, idx) => (idx === i ? { ...t, [field]: value } : t)));
  }
  function remove(i: number) {
    setTasks((prev) => prev.filter((_, idx) => idx !== i));
  }
  function add() {
    setTasks((prev) => [...prev, { action: "", priority: "P3", deadline: "48h" }]);
  }

  async function saveDraft() {
    setBusy(true);
    try {
      await apiFetch(`/api/reports/${report.id}/draft-tasks`, {
        method: "PUT",
        body: JSON.stringify({ suggested_tasks: tasks }),
      });
      toast.success("Đã lưu nháp");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Lỗi lưu nháp");
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (tasks.length === 0) {
      toast.error("Chưa có hành động nào để triển khai");
      return;
    }
    setBusy(true);
    try {
      const r = await apiFetch<{ tasks_created: number }>(
        `/api/reports/${report.id}/approve-and-dispatch`,
        { method: "POST", body: JSON.stringify({ suggested_tasks: tasks }) },
      );
      toast.success(`Đã duyệt, tạo ${r.tasks_created} task`);
      onApproved();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Lỗi khi duyệt");
    } finally {
      setBusy(false);
    }
  }

  if (report.approved) {
    return (
      <div className="rounded-xl border border-green-300 bg-green-50 p-4 text-sm text-green-800">
        Đã duyệt. Các task đã được tạo trên Task Board.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-3" onClick={() => openTasks.length === 0 && loadOpenTasks()}>
      <h4 className="font-semibold text-sm text-xanh-deep">Dự thảo kế hoạch hành động</h4>
      {openTasks.length > 0 && (
        <p className="text-[11px] text-muted-foreground">
          Phòng đang có {openTasks.length} task mở. Tránh tạo trùng: {openTasks.slice(0, 5).map((t) => t.title).join("; ")}
        </p>
      )}
      {tasks.map((t, i) => (
        <div key={i} className="flex flex-wrap gap-2 items-center border-b border-border pb-2">
          <input className="flex-1 min-w-[200px] px-2 py-1 text-xs border border-border rounded"
            value={t.action} placeholder="Hành động" onChange={(e) => update(i, "action", e.target.value)} />
          <input className="w-16 px-2 py-1 text-xs border border-border rounded"
            value={t.priority ?? ""} placeholder="P3" onChange={(e) => update(i, "priority", e.target.value)} />
          <input className="w-20 px-2 py-1 text-xs border border-border rounded"
            value={t.deadline ?? ""} placeholder="48h" onChange={(e) => update(i, "deadline", e.target.value)} />
          <button className="text-xs text-red-600" onClick={() => remove(i)}>Xóa</button>
        </div>
      ))}
      <button className="text-xs font-semibold text-xanh-deep" onClick={add}>+ Thêm hành động</button>
      <div className="flex gap-2 justify-end">
        <button disabled={busy} className="px-3 py-1.5 text-xs rounded border border-border" onClick={saveDraft}>Lưu nháp</button>
        <button disabled={busy} className="px-3 py-1.5 text-xs rounded bg-xanh-deep text-white font-semibold" onClick={approve}>
          Duyệt và triển khai task
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Gắn editor vào trang, dưới phần Markdown của mỗi report**

Tại nơi render từng report trong reports.tsx, thêm dưới Markdown:
```tsx
<DraftTaskEditor report={report} onApproved={() => reload()} />
```
Dùng đúng tên hàm reload/refetch có sẵn của trang (hàm load lại danh sách report). Nếu trang chưa có, thêm một state version + gọi lại fetch.

- [ ] **Step 5: Build kiểm tra**

Run: `cd app && npx tsc --noEmit && npx vite build`
Expected: không lỗi type, build pass.

- [ ] **Step 6: Verify thủ công**

Mở `/reports` bằng tài khoản manager: thấy editor, sửa, Lưu nháp (reload thấy giữ), Duyệt → toast tạo N task → trạng thái chuyển "Đã duyệt". Mở `/tasks` thấy task mới.

- [ ] **Step 7: Commit**

```bash
git add app/src/routes/_authenticated/reports.tsx
git commit -m "feat(ui): Draft Task editor + approve-and-dispatch trên reports.tsx

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: UI — tasks.tsx badge nguồn + link báo cáo gốc

**Files:**
- Modify: `app/src/routes/_authenticated/tasks.tsx`

**Interfaces:**
- Consumes: field `report_id`, `source` trên Task (từ Task 1).

- [ ] **Step 1: Mở rộng type `Task`**

Trong tasks.tsx, thêm vào type `Task` (quanh dòng 29):
```tsx
  report_id?: string | null;
  source?: string;
```

- [ ] **Step 2: Thêm badge nguồn + link, cạnh badge "Phòng: {assigned_team}"**

Tại chỗ render các badge của task (quanh dòng 535, sau badge "Phòng: {task.assigned_team}"):
```tsx
<span className="px-2 py-0.5 rounded bg-muted text-[10px] uppercase font-mono border border-border">
  {task.source === "report" ? "Từ báo cáo" : "Từ cảnh báo"}
</span>
{task.report_id && (
  <a
    href="/reports"
    onClick={(e) => e.stopPropagation()}
    className="text-[11px] text-xanh-deep underline font-mono"
  >
    Xem báo cáo gốc
  </a>
)}
```

- [ ] **Step 3: Build kiểm tra**

Run: `cd app && npx tsc --noEmit && npx vite build`
Expected: không lỗi, build pass.

- [ ] **Step 4: Verify thủ công**

Task tạo từ approve-and-dispatch hiện badge "Từ báo cáo" + link "Xem báo cáo gốc". Task cũ (source agent, report_id null) hiện "Từ cảnh báo", không có link, không lỗi.

- [ ] **Step 5: Commit**

```bash
git add app/src/routes/_authenticated/tasks.tsx
git commit -m "feat(ui): badge nguồn task + link báo cáo gốc trên Task Board

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Verify E2E + regression

**Files:**
- (không tạo file mới; chạy test + E2E)

- [ ] **Step 1: Chạy toàn bộ test backend**

Run: `cd pipeline && python -m pytest tests/ -q`
Expected: tất cả pass (gồm `test_dispatch_utils.py` + các test cũ, không regression).

- [ ] **Step 2: Build frontend**

Run: `cd app && npx tsc --noEmit && npx vite build`
Expected: pass.

- [ ] **Step 3: E2E thủ công đầy đủ**

Chạy pipeline (`POST /api/agent/run` hoặc `python -m agents.orchestrator`) → mở `/reports` (manager) → sửa Draft Task → Lưu nháp → reload giữ data → Duyệt → toast tạo N task → report view-only → `/tasks` thấy task `source=report` + link. Gọi lại approve-and-dispatch → 409. Manager phòng khác mở report này → 403.

- [ ] **Step 4: Commit (nếu có chỉnh nhỏ trong lúc verify)**

```bash
git add -A
git commit -m "test: verify E2E HI-Loop approval, fix nhỏ phát sinh

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Out of scope (tách spec sau)

Mở rộng 4 → 6 phòng ban (Tài chính, Sản phẩm, Rủi ro/Gian lận) và báo cáo tổng hợp chéo phòng ("Global Report") không nằm trong plan này. Xem mục 9 của `IMPLEMENTATION_PLAN.md` gốc và spec `docs/superpowers/specs/2026-06-25-hiloop-approval-design.md`.
