# Spec: Workflow Phân loại Ticket THẬT (bỏ timer tự hoàn thành)

**Date:** 2026-07-03
**Lane:** High-risk (đổi Existing behavior + Authorization + Data transitions + multi-component: worker/endpoint/frontend)

## Bối cảnh & bằng chứng

Trang "Phân loại Ticket" (`/alerts`) hiện GIẢ LẬP: `advance_ticket_workflow()` tự chuyển
alert theo **tuổi** — `open→in_progress` sau `AUTO_TICKET_IN_PROGRESS_AFTER_SECONDS` (mặc
định 10s), `in_progress→resolved` sau `AUTO_TICKET_RESOLVED_AFTER_SECONDS` (30s). Gọi bởi
`worker_ticket.py` + `worker.py`. UI còn hiển thị chính cái đồng hồ đếm giây này.

Hậu quả (DB thật): **500/500 alert = "resolved"** dù không ai xử lý; chỉ 49/500 có `task_id`
vì timer resolve trước khi `task_agent` kịp gom alert thành task. **Timer đang cướp việc của
workflow thật.**

Workflow người-thật đã có ở tầng TASK (open→assigned→in_progress→pending_review→resolved,
RBAC, event log) — nhưng alert thì không có nút/endpoint đổi status thủ công.

## Hướng chọn (B — nút thật trên alert; đã chọn khi user vắng, có thể đổi)

Bỏ timer; cho ops xử lý THẬT từng ticket ngay trên trang Phân loại Ticket. Tự chứa, không
phải re-architect `task_agent`. Giữ nguyên link `task_id` và workflow task.

### 1. Bỏ timer giả lập
- `advance_ticket_workflow()` KHÔNG còn auto-advance theo tuổi. Gỡ lời gọi định kỳ ở
  `worker_ticket.py` + `worker.py` (hoặc để hàm chỉ trả trạng thái đếm, không update). Alert
  sinh ra ở `open` và Ở NGUYÊN tới khi người thật xử lý (backlog thật).
- Bỏ cấu hình đếm giây + hiển thị đồng hồ ở UI `/alerts`.

### 2. Endpoint thật (backend)
- `PATCH /api/alerts/{id}/status` — body `{status}`. Transition hợp lệ:
  `open→in_progress`, `in_progress→resolved`, và `resolved→in_progress` (mở lại). Từ chối
  transition sai (400).
- **RBAC:** admin mọi alert; manager/staff chỉ alert thuộc phòng mình
  (`alert_department(alert) == user.department`, tái dùng helper sẵn có) — khác phòng → 403.
- Ghi audit vào bảng log sẵn có (`audit_logs`): ai đổi, alert id, status cũ→mới. KHÔNG
  migration (dùng cột `status` sẵn có).

### 3. Frontend `/alerts`
- Bỏ khối hiển thị timer (in_progress_after_seconds...).
- Mỗi alert có nút theo status + quyền: **"Nhận xử lý"** (open→in_progress),
  **"Đã xử lý"** (in_progress→resolved), **"Mở lại"** (resolved→in_progress). Nút ẩn nếu
  không đủ quyền (khác phòng) hoặc không hợp transition.
- Badge status thật; filter status phản ánh backlog thật (không còn toàn "resolved").
- (Giữ) hiển thị SLA quá hạn dựa `sla_due_at` vs now cho alert chưa resolved.

### 4. Giữ nguyên
- Live-stream ingest vẫn sinh alert `open`. `task_agent` vẫn gom alert `open`→task (giờ có
  thời gian để gom vì alert không bị resolve tức thì). Workflow task không đổi.

## Validation
- Timer tắt: tạo alert `open`, chờ > ngưỡng cũ → VẪN `open` (không auto-resolve).
- `PATCH status`: chuyển đúng open→in_progress→resolved; transition sai → 400; alert phòng
  khác (manager/staff) → 403; admin mọi phòng OK; có dòng audit_logs.
- Frontend: nút đúng theo status + quyền; sau bấm, status cập nhật (invalidate query).
- E2E thật: alert `open` của phòng X → staff X "Nhận xử lý"→in_progress→"Đã xử lý"→resolved;
  staff phòng Y không có nút / 403.
- Full pytest + tsc.

## Không đổi (ngoài phạm vi)
- Schema (không migration; dùng `status` sẵn có). Workflow task, report→task, chat/RAG, MCP.
- (Follow-up nếu cần báo cáo SLA sâu: thêm cột `resolved_at`/`resolved_by` — migration riêng.)

## Ghi chú quyết định
- Chọn B (nút trên alert) thay vì A (alert bám theo task) vì tự chứa + đúng nghĩa trang
  "Phân loại Ticket" + không phụ thuộc task_agent gom đủ. Nếu bạn muốn A (đóng alert khi task
  đóng) → đổi spec.
