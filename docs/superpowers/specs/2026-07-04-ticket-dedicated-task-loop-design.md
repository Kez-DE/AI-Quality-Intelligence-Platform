# Spec: Tách luồng ticket→task riêng + khép kín loop hoàn thành

Date: 2026-07-04
Status: approved (brainstorming)
Lane: high-risk (data model + API behavior + đa domain ticket/task/report)

## Vấn đề (đã xác minh trong code + DB thật)

1. **Loop gãy ở bước duyệt**: `review_completion_report` (manager duyệt 'approved') đặt task
   → `resolved` nhưng KHÔNG gọi `_resolve_alerts_for_task` (hai path khác — `update_task_status`
   dòng 486, `support_resolve` dòng 635 — thì có). Hệ quả: duyệt hoàn thành xong, ticket bên
   Phân loại Ticket **không tự tick 'Đã xong'**.
2. **Hai luồng dính nhau**: `tasks.source` chỉ có `'agent'`/`'report'`. Nút "Tiếp nhận & Giao việc"
   gọi `find_or_create_cluster_task(team, area)` → **tái dùng task cụm có sẵn** (source `agent`)
   thay vì đẩy task mới của ticket → không phân biệt được "task đẩy từ ticket" vs "agent tự sinh".

Auto/live-stream chỉ tạo alert (`detect_spikes`), KHÔNG tạo task. Worker clustering
(`cluster_alerts_into_tasks`) không được schedule.

## Target workflow

```
Data review → spike_detector → TICKET (alert, Phân loại Ticket)
   → manager "Tiếp nhận & Giao việc"
   → TASK RIÊNG (source='ticket', alert.task_id = task.id 1:1) sang Quản lý công việc
   → manager giao NV → NV làm → submit_completion_report (task pending_review)
   → manager DUYỆT (approved)
       → task resolved + vào Báo cáo hoàn thành
       → _resolve_alerts_for_task → ticket tự tick 'Đã xong'
```
Luồng nội bộ (`source='agent'`/`'report'`) chạy song song, độc lập.

## Quyết định thiết kế

- **Liên kết 1:1**: mỗi lần Tiếp nhận tạo 1 task DÀNH RIÊNG cho ticket (không gom cụm).
  Hoàn thành task → tick đúng ticket đó.

## Thay đổi

### 1. Migration
`supabase/migrations/<ts>_tasks_source_ticket.sql`: drop + tạo lại `tasks_source_check`
cho phép `source IN ('agent','report','ticket')`. Áp lên shared cloud DB.

### 2. Backend (`pipeline/`)
- `agents/task_agent.py`: thêm `create_ticket_task(db, team, area, priority, title, summary)`
  — LUÔN insert task mới, `source='ticket'`, trả `id`. (Không tái dùng cụm.)
- `main.py` `update_alert_status` (Tiếp nhận): thay `find_or_create_cluster_task` bằng
  `create_ticket_task`; giữ guard `if new_status=='in_progress' and not alert.task_id`
  (mỗi ticket đẩy đúng 1 task). Gắn `alert.task_id = new_task_id`.
- `main.py` `review_completion_report`: sau khi approve → task `resolved`, gọi
  `_resolve_alerts_for_task(db, rep_task_id, user)` (chỉ khi approved) → resolve ticket liên kết.
- `find_or_create_cluster_task` giữ nguyên (luồng `agent` cũ + worker không đổi).

### 3. Frontend (`app/src`)
- Task list Quản lý công việc: badge "🎫 Từ ticket" khi `task.source === 'ticket'`
  (phân biệt với task agent/report tự sinh). Thêm `source` vào type Task + hiển thị badge.

### 4. Test
- `create_ticket_task`: luôn tạo mới (2 lần gọi → 2 task khác nhau), `source='ticket'`.
- `review_completion_report` approve → `_resolve_alerts_for_task` được gọi với đúng task_id
  (dùng fake DB / spy như test_task_resolve_syncs_alert).
- Không hồi quy: `find_or_create_cluster_task` vẫn find-or-create như cũ.

### 5. Verify thật (local + Railway, shared DB)
Tạo 1 alert open → PATCH status in_progress (Tiếp nhận) → xác nhận task mới `source='ticket'`
+ `alert.task_id` set → submit completion → approve → xác nhận task `resolved`, có completion
report, và **alert → resolved** (ticket 'Đã xong'). Dọn dữ liệu test.

## Không làm (YAGNI)
- Không migrate task `agent` cũ sang `ticket`.
- Không đụng worker clustering / find_or_create_cluster_task.
- Không thêm filter mới ở frontend (chỉ badge).

## Rủi ro
- Migration đổi CHECK constraint: task cũ đều hợp lệ (agent/report) nên an toàn; chỉ mở rộng.
- `review_completion_report` non-atomic (đã ghi chú sẵn trong code) — resolve alert best-effort.
- Đẩy thẳng `main` theo yêu cầu (không qua branch); Railway auto-deploy.
