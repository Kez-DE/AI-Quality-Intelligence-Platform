# Workflow Phân loại Ticket THẬT — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bỏ timer tự-resolve alert; cho ops xử lý ticket THẬT (open→in_progress→resolved) qua nút + endpoint có RBAC; ghi timing để báo cáo SLA sâu (MTTA/MTTR, đúng hạn/trễ).

**Architecture:** Backend: migration thêm cột timing vào `alerts`; endpoint `PATCH /api/alerts/{id}/status` (mirror `update_task_status`: `require_ops_staff` + `can_view_team` + transition + audit) và `GET /api/alerts/sla-summary`; gỡ lịch chạy `advance_ticket_workflow` ở worker. Frontend `/alerts`: bỏ đồng hồ timer, thêm nút thao tác + thẻ SLA.

**Tech Stack:** FastAPI, Supabase, React/TanStack, pytest, vitest.

**Spec:** `docs/superpowers/specs/2026-07-03-real-ticket-workflow-design.md`
**Nhánh:** `feat/real-ticket-workflow` (off main).

Đã xác minh: `alerts` cột hiện có (status, assigned_team, sla_due_at, task_id, created_at...) KHÔNG có timing; `audit_logs` tồn tại (action/actor_id/actor_email/target_id/details); `can_view_team`, `require_ops_staff`, `alert_department` sẵn có; `update_task_status` (main.py:390) là mẫu để mirror; `worker_ticket.py` + `worker.py` gọi `scheduler.add_job(advance_ticket_workflow,...)`.

---

## Task 1: Migration — cột timing cho alerts

**Files:**
- Create: `supabase/migrations/20260703120000_alerts_workflow_timing.sql`

**Step 1:** Viết migration:
```sql
-- Timing cho workflow ticket thật + báo cáo SLA sâu (MTTA/MTTR, đúng hạn/trễ).
alter table public.alerts
    add column if not exists in_progress_at timestamptz,
    add column if not exists resolved_at    timestamptz,
    add column if not exists resolved_by     uuid references auth.users(id) on delete set null,
    add column if not exists updated_at      timestamptz;

comment on column public.alerts.resolved_at is
    'Thời điểm ticket được người thật đóng (dùng so với sla_due_at để tính đúng hạn/trễ).';
```

**Step 2: Áp**
Run: `cd /Users/kenz_de/projects/C2-App-116 && supabase db push` (xác nhận Y).
Expected: "Applying migration 20260703120000_alerts_workflow_timing.sql".

**Step 3: Verify cột**
Run: `cd pipeline && .venv/bin/python -c "from ingest import get_supabase; print([c for c in ['in_progress_at','resolved_at','resolved_by','updated_at'] if c in (get_supabase().table('alerts').select('*').limit(1).execute().data or [{}])[0]])"`
Expected: in đủ 4 cột (nếu alerts rỗng → bỏ qua, tin migration).

**Step 4: Commit**
```bash
git add supabase/migrations/20260703120000_alerts_workflow_timing.sql
git commit -m "feat(db): cột timing cho alerts (in_progress_at/resolved_at/resolved_by/updated_at)"
```

---

## Task 2: Gỡ timer giả lập khỏi worker

**Files:**
- Modify: `pipeline/worker_ticket.py`
- Modify: `pipeline/worker.py`

**Step 1:** Trong `worker_ticket.py`: gỡ `scheduler.add_job(advance_ticket_workflow, ...)` (không lên lịch auto-advance nữa). Giữ scheduler chạy (nếu worker còn job khác) hoặc để worker log "ticket auto-advance disabled — dùng workflow thật". Trong `worker.py`: bỏ `advance_ticket_workflow` khỏi danh sách job định kỳ.

**Step 2:** Giữ hàm `advance_ticket_workflow` tồn tại (tránh vỡ import chỗ khác) nhưng KHÔNG được auto-update status theo tuổi nữa — an toàn nhất: comment phần update trong hàm, để nó chỉ trả trạng thái đếm (0). Hoặc thêm cờ `AUTO_TICKET_WORKFLOW_ENABLED=false` (mặc định tắt) và bọc phần update trong `if enabled`.

**Step 3: Verify không còn auto-resolve**
Run:
```bash
cd pipeline && .venv/bin/python -c "
from services.ticket_workflow import advance_ticket_workflow
r = advance_ticket_workflow()
print('moved_in_progress+resolved:', (r or {}).get('moved_to_in_progress'), (r or {}).get('moved_to_resolved'))
"
```
Expected: 0 và 0 (không chuyển gì). Không đổi alert nào.

**Step 4: Commit**
```bash
git add pipeline/worker_ticket.py pipeline/worker.py pipeline/services/ticket_workflow.py
git commit -m "feat(ticket): tắt timer tự-resolve alert (chuyển sang workflow thật)"
```

---

## Task 3: Endpoint PATCH /api/alerts/{id}/status (TDD)

**Files:**
- Modify: `pipeline/main.py`
- Test: `pipeline/tests/test_alert_status.py`

**Step 1: Viết test thất bại** (dùng fake DB kiểu `_fakedb` sẵn có trong tests, hoặc mock get_supabase). Tối thiểu kiểm logic transition + RBAC qua hàm thuần tách ra. Tách helper thuần để test dễ:

```python
# tests/test_alert_status.py
import pytest
from main import _assert_alert_transition   # helper mới, thuần

def test_valid_alert_transitions():
    _assert_alert_transition("open", "in_progress")
    _assert_alert_transition("in_progress", "resolved")
    _assert_alert_transition("resolved", "in_progress")  # mở lại

def test_invalid_alert_transitions():
    for a, b in [("open", "resolved"), ("resolved", "open"), ("open", "open")]:
        with pytest.raises(Exception):
            _assert_alert_transition(a, b)
```

**Step 2:** Run: `cd pipeline && .venv/bin/python -m pytest tests/test_alert_status.py -q` → FAIL (`_assert_alert_transition` chưa có).

**Step 3: Implement** trong `main.py`:
```python
_ALERT_TRANSITIONS = {
    "open": {"in_progress"},
    "in_progress": {"resolved"},
    "resolved": {"in_progress"},   # mở lại
}

def _assert_alert_transition(cur: str, new: str):
    if new not in _ALERT_TRANSITIONS.get(cur, set()):
        raise HTTPException(status_code=400, detail=f"Không thể chuyển ticket {cur} → {new}")


class AlertStatusReq(BaseModel):
    status: str


@app.patch("/api/alerts/{alert_id}/status")
def update_alert_status(alert_id: str, payload: AlertStatusReq,
                        user: AuthUser = Depends(require_ops_staff)):
    new_status = payload.status
    if new_status not in {"open", "in_progress", "resolved"}:
        raise HTTPException(status_code=400, detail="Invalid alert status")
    try:
        db = get_supabase()
        rows = db.table("alerts").select("*").eq("id", alert_id).limit(1).execute().data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Alert not found")
        alert = rows[0]
        team = alert_department(alert) or alert.get("assigned_team")
        if not can_view_team(user, team):
            raise HTTPException(status_code=403, detail="Bạn không có quyền xử lý ticket của phòng ban khác.")
        cur = alert.get("status") or "open"
        _assert_alert_transition(cur, new_status)

        patch = {"status": new_status, "updated_at": "now()"}
        if new_status == "in_progress" and not alert.get("in_progress_at"):
            patch["in_progress_at"] = "now()"
        if new_status == "resolved":
            patch["resolved_at"] = "now()"
            patch["resolved_by"] = user.id
        if new_status == "in_progress" and cur == "resolved":  # mở lại
            patch["resolved_at"] = None
            patch["resolved_by"] = None

        data = db.table("alerts").update(patch).eq("id", alert_id).execute().data or []
        # audit
        try:
            db.table("audit_logs").insert({
                "actor_id": user.id, "actor_email": user.email,
                "action": "alert_status_changed", "target_id": alert_id,
                "details": {"from": cur, "to": new_status, "team": team},
            }).execute()
        except Exception:
            pass
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot update alert: {str(exc)[:300]}") from exc
    return {"status": "success", "data": data[0] if data else None}
```
> Kiểm tra `BaseModel`, `alert_department`, `can_view_team`, `require_ops_staff`, `get_supabase` đã import ở main.py (có). `audit_logs.details` là JSON — truyền dict.

**Step 4:** Run test → PASS. Chạy thêm `-k "alert or feedback_scope"` không vỡ.

**Step 5: Commit**
```bash
git add pipeline/main.py pipeline/tests/test_alert_status.py
git commit -m "feat(alerts): PATCH /api/alerts/{id}/status — workflow thật + RBAC + audit + timing"
```

---

## Task 4: Endpoint GET /api/alerts/sla-summary (TDD)

**Files:**
- Modify: `pipeline/main.py`
- Test: `pipeline/tests/test_alert_sla_summary.py`

**Step 1: Viết test** cho hàm thuần tính SLA từ list alert (tách để test không cần DB):
```python
from main import _compute_sla_summary

def test_sla_summary_counts():
    alerts = [
        {"status": "resolved", "sla_due_at": "2026-07-01T10:00:00+00:00",
         "resolved_at": "2026-07-01T09:00:00+00:00", "created_at": "2026-07-01T08:00:00+00:00",
         "in_progress_at": "2026-07-01T08:30:00+00:00"},   # đúng hạn
        {"status": "resolved", "sla_due_at": "2026-07-01T10:00:00+00:00",
         "resolved_at": "2026-07-01T12:00:00+00:00", "created_at": "2026-07-01T08:00:00+00:00"},  # trễ
        {"status": "open", "sla_due_at": "2000-01-01T00:00:00+00:00", "created_at": "2026-07-01T08:00:00+00:00"},  # đang quá hạn
    ]
    s = _compute_sla_summary(alerts)
    assert s["on_time"] == 1 and s["late"] == 1 and s["overdue_open"] == 1
    assert s["mttr_seconds"] is not None
```

**Step 2:** Run → FAIL.

**Step 3: Implement** `_compute_sla_summary(alerts)` (parse ISO, so sánh; MTTA = mean(in_progress_at-created_at), MTTR = mean(resolved_at-created_at)) + endpoint:
```python
@app.get("/api/alerts/sla-summary")
def alert_sla_summary(user: AuthUser = Depends(require_ops_staff)):
    db = get_supabase()
    rows = db.table("alerts").select(
        "status,sla_due_at,created_at,in_progress_at,resolved_at,assigned_team,topic,severity,sentiment"
    ).order("created_at", desc=True).limit(1000).execute().data or []
    if user.role != "admin":
        rows = [a for a in rows if can_view_team(user, alert_department(a) or a.get("assigned_team"))]
    return {"status": "success", "data": _compute_sla_summary(rows)}
```
Dùng `parse_timestamp` từ `services.ticket_workflow` (đã có) để parse ISO.

**Step 4:** Run test → PASS.

**Step 5: Commit**
```bash
git add pipeline/main.py pipeline/tests/test_alert_sla_summary.py
git commit -m "feat(alerts): GET /api/alerts/sla-summary — MTTA/MTTR + đúng hạn/trễ/quá hạn"
```

---

## Task 5: Frontend /alerts — nút thao tác + thẻ SLA, bỏ đồng hồ timer

**Files:**
- Modify: `app/src/routes/_authenticated/alerts.tsx`
- Modify: `app/src/lib/api.ts` (nếu cần helper mutate)

**Step 1:** Đọc `alerts.tsx`. Gỡ khối hiển thị `TicketWorkflowStatus` (in_progress_after_seconds/resolved_after_seconds/moved_...) + fetch `/api/ticket-workflow/status` liên quan.

**Step 2:** Thêm mutation gọi `apiFetch(`/api/alerts/${id}/status`, {method:"PATCH", body: JSON.stringify({status})})`, invalidate query alerts sau khi xong (toast).

**Step 3:** Mỗi alert render nút theo `status` + quyền (dùng `useMe`: admin, hoặc `me.department === alert.assigned_team`/phòng của alert):
- status `open` → nút **"Nhận xử lý"** (→in_progress).
- status `in_progress` → nút **"Đã xử lý"** (→resolved).
- status `resolved` → nút **"Mở lại"** (→in_progress), mờ hơn.
- Ẩn nút nếu không đủ quyền phòng.

**Step 4:** Thêm thẻ tóm tắt SLA (fetch `/api/alerts/sla-summary`): Đúng hạn / Trễ / Đang quá hạn + MTTA/MTTR (đổi giây → giờ/phút) — đặt chỗ khối đồng hồ cũ.

**Step 5: Verify**
```bash
cd app && npx tsc --noEmit    # exit 0
npx vite build                # OK
```

**Step 6: Commit**
```bash
git add app/src/routes/_authenticated/alerts.tsx app/src/lib/api.ts
git commit -m "feat(alerts-ui): nút xử lý ticket thật + thẻ SLA, bỏ đồng hồ timer giả lập"
```

---

## Task 6: E2E thật + full verify + PR

**Step 1: E2E** (backend local 8000 chạy; hoặc gọi thẳng hàm). Tạo/ chọn 1 alert `open` của một phòng, dùng JWT staff phòng đó gọi PATCH →in_progress→resolved; kiểm `resolved_at`/`resolved_by` set; staff phòng khác → 403; gọi `/api/alerts/sla-summary` trả số hợp lệ.

**Step 2:** `cd pipeline && .venv/bin/python -m pytest -q` (xanh) + `cd app && npx tsc --noEmit` (0).

**Step 3: Push + PR**
```bash
git push -u origin feat/real-ticket-workflow
gh pr create --base main --title "feat(alerts): workflow Phân loại Ticket thật + SLA sâu (bỏ timer)" --body "<nguyên nhân timer giả lập; endpoint PATCH status + sla-summary; RBAC; migration timing; frontend nút+thẻ SLA; verify>"
```

## Thứ tự & phụ thuộc
1 (migration) → 2 (tắt timer) → 3 (endpoint status) → 4 (sla-summary) → 5 (frontend) → 6 (E2E+PR).

## Verify tổng
- Timer không auto-resolve (alert open ở nguyên).
- PATCH status: transition đúng, RBAC 403 phòng khác, timing set, audit ghi.
- sla-summary: đúng hạn/trễ/quá hạn + MTTA/MTTR đúng.
- Frontend: nút theo status+quyền; thẻ SLA thay đồng hồ; tsc+build sạch.
- Full pytest xanh.
