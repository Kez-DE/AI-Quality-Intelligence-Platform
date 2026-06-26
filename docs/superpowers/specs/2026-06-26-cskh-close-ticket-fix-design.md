# Thiết kế: Sửa lỗi "Đóng ticket" ở bàn Hỗ trợ CSKH

- Ngày: 2026-06-26
- Nhánh: `fix/cskh-close-ticket`
- Loại: Change request (sửa regression)
- Lane: Normal-strong (chạm authorization + existing behavior + public contract API)

## 1. Triệu chứng

Trang `/support` (Bảng điều phối Hỗ trợ CSKH): nhập câu phản hồi rồi ấn "Đóng" trong
hộp xác nhận "Xác nhận đóng ticket này?" — ticket **không đóng**, không có phản hồi gì.

## 2. Nguyên nhân gốc (đã xác minh)

Regression từ feature task-completion-loop (PR #15). `support.tsx > resolveTicket`
gọi `PATCH /api/tasks/{id}/status {status:"resolved"}`, nhưng:

1. **RBAC**: `update_task_status` yêu cầu manager/admin (`require_manager` + check role)
   → CSKH **staff** bị **403**.
2. **Transition**: ticket ở trạng thái `open`; `ALLOWED_TASK_TRANSITIONS` không có
   `(open, resolved)` (đường hợp lệ: open→assigned→in_progress→pending_review→resolved)
   → **400** kể cả với manager.
3. **UI nuốt lỗi**: `resolveTicket` dùng `catch {}` chung chung, không hiện `e.message`
   (mà `apiFetch` đã ném `Error(detail)` từ backend).
4. **Phản hồi không được lưu**: câu trả lời khách hàng chỉ là text UI, không gửi backend.

## 3. Quyết định

**Option A — đóng trực tiếp ở bàn CSKH.** Đây là quy trình khách-hàng-đối-mặt, khác
vòng duyệt nội bộ (staff gửi báo cáo → manager duyệt) ở trang Tasks. Nhân viên CSKH
được đóng ticket khách trực tiếp, không cần manager duyệt. KHÔNG đụng `update_task_status`
để giữ nguyên vòng duyệt nội bộ.

## 4. Thiết kế

### Backend — endpoint mới
`POST /api/tasks/{task_id}/support-resolve`
- Auth: `require_ops_staff` (staff/manager/admin).
- Body: `SupportResolveReq { reply: str }` — `reply` bắt buộc, không rỗng (min_length sau strip).
- Scope: `can_view_team(user, task.assigned_team)` — khác phòng → 403.
- Transition cho phép: `open|assigned|in_progress|pending_review → resolved`. Nếu task
  đã `resolved` → trả 409 (đã đóng). Trạng thái khác → 400.
- Hành động: `update tasks set status='resolved', updated_at=now()`; ghi
  `_log_task_event(action="support_resolved", from_status=cur, to_status="resolved",
  note=reply[:500])`.
- Trả `{"status":"success","data": <task>}`.

> Vì sao endpoint riêng thay vì nới `update_task_status`: tách quy trình CSKH (đóng
> trực tiếp) khỏi quy trình duyệt nội bộ; không làm yếu validation/RBAC của luồng task.

### Frontend — `app/src/routes/_authenticated/support.tsx`
- `resolveTicket`: đổi sang `POST /api/tasks/{id}/support-resolve` với body
  `{ reply: cannedReply }`.
- Giữ kiểm tra `cannedReply.trim()` rỗng (đã có) → báo nhập phản hồi.
- `catch (e)`: `toast.error(e instanceof Error ? e.message : "Lỗi khi xử lý Ticket.")`
  để hiện lỗi thật từ backend.
- Sau thành công: giữ logic hiện tại (xoá khỏi danh sách, clear chọn, clear reply).

## 5. Kiểm thử
- `pipeline/tests/test_support_resolve.py` (mock supabase client):
  - staff cùng phòng + task open → resolved thành công, có ghi task_event.
  - staff khác phòng → 403.
  - reply rỗng → 422 (pydantic) hoặc 400.
  - task đã resolved → 409.
- Frontend: typecheck sạch (`npx tsc --noEmit`).
- Full backend suite vẫn xanh (hiện 116 passed).

## 6. Ngoài phạm vi
- Không đổi `update_task_status` / vòng duyệt nội bộ ở trang Tasks.
- Không lưu phản hồi như tin nhắn gửi khách thật (chỉ ghi audit note) — có thể nâng cấp sau.

## 7. Rủi ro & giảm thiểu
| Rủi ro | Giảm thiểu |
| --- | --- |
| Mở quá rộng quyền đóng task | Endpoint riêng, scope theo phòng, chỉ resolve (không sửa lung tung) |
| Lệch state machine | Chỉ cho các trạng thái mở → resolved; đã resolved trả 409 |
| Vẫn nuốt lỗi UI | Hiện `e.message` từ apiFetch |
