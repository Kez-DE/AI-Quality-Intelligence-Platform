# CSKH Close-Ticket Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Cho phép nhân viên CSKH đóng ticket trực tiếp ở trang `/support` (đang bị lỗi 403/400 sau task-completion-loop), kèm lưu câu phản hồi vào audit và hiện lỗi thật trên UI.

**Architecture:** Thêm endpoint backend riêng `POST /api/tasks/{id}/support-resolve` cho staff/manager/admin trong đúng phòng resolve trực tiếp (không đụng `update_task_status` của vòng duyệt nội bộ). Frontend `support.tsx` gọi endpoint mới và surface `e.message`.

**Tech Stack:** FastAPI + pydantic + Supabase (pipeline/), React + TanStack (app/), pytest.

**Spec:** `docs/superpowers/specs/2026-06-26-cskh-close-ticket-fix-design.md`
**Branch:** `fix/cskh-close-ticket` (đã tạo, đang đứng trên nhánh).
**Chạy test backend:** `cd pipeline && python -m pytest tests/ -q` (env: `set -a && source ../.env && set +a` nếu cần).

---

## Task 1: Backend — endpoint `support-resolve`

**Files:**
- Modify: `pipeline/main.py` (thêm `SupportResolveReq` cạnh các Req model ~line 44-70; thêm endpoint sau `update_task_status` ~line 414)
- Test: `pipeline/tests/test_support_resolve.py` (tạo)

**Step 1: Viết test thất bại** — tạo `pipeline/tests/test_support_resolve.py`:
```python
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
import main
from auth_guard import AuthUser


def _user(role="staff", dept="CSKH"):
    return AuthUser(id="u1", email="a@x.vn", role=role, department=dept)


def _db_with_task(status="open", team="CSKH"):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"assigned_team": team, "status": status}
    ]
    db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {"id": "t1", "status": "resolved"}
    ]
    return db


def test_support_resolve_staff_same_team_ok(monkeypatch):
    db = _db_with_task(status="open", team="CSKH")
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    out = main.support_resolve("t1", main.SupportResolveReq(reply="Đã xử lý cho khách"), user=_user())
    assert out["status"] == "success"
    assert out["data"]["status"] == "resolved"


def test_support_resolve_other_team_forbidden(monkeypatch):
    db = _db_with_task(status="open", team="Vận hành")
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    with pytest.raises(HTTPException) as ei:
        main.support_resolve("t1", main.SupportResolveReq(reply="x"), user=_user(dept="CSKH"))
    assert ei.value.status_code == 403


def test_support_resolve_already_resolved_conflict(monkeypatch):
    db = _db_with_task(status="resolved", team="CSKH")
    monkeypatch.setattr(main, "get_supabase", lambda: db)
    with pytest.raises(HTTPException) as ei:
        main.support_resolve("t1", main.SupportResolveReq(reply="x"), user=_user())
    assert ei.value.status_code == 409
```
> Lưu ý: kiểm tra chữ ký thật của `AuthUser` trong `pipeline/auth_guard.py` và chỉnh `_user(...)` cho khớp (field name role/department). `reply` rỗng được pydantic chặn (min_length=1) nên không cần test riêng ở tầng hàm.

**Step 2: Chạy, xác nhận FAIL:**
`cd pipeline && python -m pytest tests/test_support_resolve.py -v`
Expected: FAIL (`main.SupportResolveReq`/`main.support_resolve` chưa tồn tại).

**Step 3: Thêm model** — cạnh `CompletionReportReq` trong `pipeline/main.py`:
```python
class SupportResolveReq(BaseModel):
    reply: str = Field(..., min_length=1, max_length=5000)
```

**Step 4: Thêm endpoint** — sau `update_task_status` (sau dòng ~414):
```python
@app.post("/api/tasks/{task_id}/support-resolve")
def support_resolve(task_id: str, payload: SupportResolveReq, user: AuthUser = Depends(require_ops_staff)):
    """Bàn CSKH đóng ticket khách trực tiếp (staff/manager/admin trong phòng).
    Tách khỏi vòng duyệt nội bộ update_task_status."""
    try:
        db = get_supabase()
        rows = db.table("tasks").select("assigned_team,status").eq("id", task_id).limit(1).execute().data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Task not found")
        task_team = rows[0].get("assigned_team")
        cur_status = rows[0].get("status")
        if not can_view_team(user, task_team):
            raise HTTPException(status_code=403, detail="Bạn không thể đóng ticket của phòng ban khác.")
        if cur_status == "resolved":
            raise HTTPException(status_code=409, detail="Ticket đã được đóng.")
        if cur_status not in {"open", "assigned", "in_progress", "pending_review"}:
            raise HTTPException(status_code=400, detail=f"Không thể đóng ticket ở trạng thái {cur_status}.")
        data = db.table("tasks").update({"status": "resolved", "updated_at": "now()"}).eq("id", task_id).execute().data or []
        if not data:
            raise HTTPException(status_code=404, detail="Task not found")
        _log_task_event(
            db, task_id=task_id, actor=user, team=task_team, action="support_resolved",
            from_status=cur_status, to_status="resolved", note=payload.reply[:500],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot resolve ticket: {str(exc)[:300]}") from exc
    return {"status": "success", "data": data[0]}
```

**Step 5: Chạy test + full suite:**
```
cd pipeline && python -m pytest tests/test_support_resolve.py -v
cd pipeline && python -m pytest tests/ -q
```
Expected: test mới PASS; full suite vẫn xanh (hiện 116 passed → 119).

**Step 6: Commit:**
```
git add pipeline/main.py pipeline/tests/test_support_resolve.py
git commit -m "fix(api): thêm support-resolve cho bàn CSKH đóng ticket trực tiếp"
```

---

## Task 2: Frontend — gọi endpoint mới + hiện lỗi thật

**Files:**
- Modify: `app/src/routes/_authenticated/support.tsx` (`resolveTicket`, ~line 130-152)

**Step 1: Sửa `resolveTicket`** — đổi call và catch:
```tsx
      await apiFetch(`/api/tasks/${selectedTaskId}/support-resolve`, {
        method: "POST",
        body: JSON.stringify({ reply: cannedReply }),
      });
      toast.success("Đã phản hồi & đóng Ticket thành công!");
      setTasks((prev) => prev.filter((t) => t.id !== selectedTaskId));
      setSelectedTaskId(null);
      setCannedReply("");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Lỗi khi xử lý Ticket.");
    } finally {
```
(Giữ nguyên kiểm tra `cannedReply.trim()` rỗng ở đầu hàm.)

**Step 2: Typecheck:**
`cd app && npx tsc --noEmit`
Expected: không lỗi.

**Step 3: Commit:**
```
git add app/src/routes/_authenticated/support.tsx
git commit -m "fix(ui): bàn CSKH gọi support-resolve + hiện lỗi backend thật"
```

---

## Task 3: Verify & bàn giao

**Step 1:** `cd pipeline && python -m pytest tests/ -q` → tất cả PASS.
**Step 2:** `cd app && npx tsc --noEmit` → sạch.
**Step 3 (tùy chọn smoke thật):** chạy local, mở `/support` bằng tài khoản CSKH staff, nhập phản hồi, ấn Đóng → ticket biến mất khỏi hàng đợi; thử khác phòng → thấy toast 403.
**Step 4:** Merge `fix/cskh-close-ticket` → `main`, push (khi người dùng đồng ý) → Railway tự deploy (frontend + backend). Hoặc deploy thẳng `railway up --service frontend` + `--service backend` như lần trước.

---

## Thứ tự & lưu ý
1 → 2 → 3. Task 1 độc lập backend, Task 2 phụ thuộc Task 1 (endpoint). Chỉ deploy `frontend` + `backend` là đủ (không đụng worker). DRY/YAGNI/TDD, commit nhỏ.
