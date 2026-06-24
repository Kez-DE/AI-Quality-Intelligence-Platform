# Thiết kế: Luồng khép kín HI-Loop Approval (Report → Manager → Tasks)

Ngày: 2026-06-25. Phạm vi: AI Quality Intelligence Platform (xanhSM/greenSM).

Tài liệu này hiệu chỉnh và chốt bản `IMPLEMENTATION_PLAN.md` do team đề xuất. Phần lớn plan gốc giữ nguyên (vertical slices, acceptance criteria, RBAC, lock 409). Bản này ghi lại 4 điều chỉnh đã thống nhất và lý do, để dùng làm nguồn khi viết implementation plan.

## 1. Bài toán và mục tiêu

Hệ thống đã có luồng tự động Feedback → Ticket → Phân tích → Báo cáo Markdown. Báo cáo AI hiện là văn bản tĩnh: Manager đọc rồi tự tạo task tay, không có cầu nối tự động từ báo cáo sang việc giao cho nhân viên.

Mục tiêu: thêm cơ chế Manager-in-the-Loop. AI đề xuất danh sách Draft Task có cấu trúc trong báo cáo, Manager sửa rồi bấm một nút để biến chúng thành Task chính thức, gán cho phòng, có liên kết ngược về báo cáo gốc.

## 2. Phạm vi

Trong phạm vi: luồng HI-Loop cho 4 phòng ban hiện tại (IT, CSKH, Vận hành, Marketing). Bảy task của plan gốc (DB migration, agent ghi JSONB, 2 API, 2 màn UI, test).

Ngoài phạm vi (tách spec sau): mục 9 của plan gốc. Mở rộng 4 lên 6 phòng ban (thêm Tài chính, Sản phẩm, Rủi ro/Gian lận) đụng `routing_table.json`, persona, `valid_departments`, KB. Báo cáo tổng hợp chéo phòng ("Global Report", một spike sinh task song song nhiều phòng) phá vỡ model report-per-team của spec này nên cần thiết kế riêng.

## 3. Nền tảng đã có sẵn (đã verify trong code)

- `ActionItem` (`pipeline/agents/schemas.py:23`) đã đúng schema cần dùng: `action`, `priority`, `deadline`, `owner`, `success_metric`.
- `analyst_agent.py` đã sinh `action_items` với deadline dạng `"24h"`/`"48h"`/`"1w"`, đã slice `[:5]` và điền default deadline 48h. Không phải viết lại agent.
- `department_reports` đã có `approved`, `approved_by`, `approved_at`.
- `tasks` đã có đủ field; `alerts.task_id` đã liên kết alert vào task.
- `task_agent.cluster_alerts_into_tasks()` đã tự gom alert thành task (orchestrator Step 5).

## 4. Bốn điều chỉnh so với plan gốc

### 4.1 Sống chung hai nguồn task (gắn nguồn để phân biệt)

Sau khi thêm luồng này sẽ có hai đường tạo task cho cùng một vấn đề gốc, dễ trùng. Giải pháp đã chốt: giữ cả hai, phân biệt bằng nguồn, dedup thủ công.

- Thêm cột `tasks.source TEXT NOT NULL DEFAULT 'agent'` với `CHECK (source IN ('agent','report'))`.
- `task_agent` (Step 5) vẫn auto tạo task từ alert, `source='agent'`.
- `approve-and-dispatch` tạo task từ báo cáo, `source='report'` kèm `report_id`.
- Task Board hiển thị badge phân biệt: "Từ cảnh báo" (agent) và "Từ báo cáo" (report).
- Khi Manager chuẩn bị dispatch, `reports.tsx` hiển thị danh sách task `open` hiện có của phòng để Manager thấy và tránh đặt trùng. Đây là dedup thủ công, hệ thống không tự gộp.

### 4.2 Sửa xung đột số migration

Plan gốc đặt `20260626000000_suggested_tasks_and_report_link.sql`, nhưng repo đã có `20260626000000_task_completion_reports.sql`. Đổi tên migration mới thành `20260627000000_suggested_tasks_and_report_link.sql`. Gộp luôn cột `tasks.source` vào migration này.

### 4.3 Atomic bằng Postgres RPC, không phải try/except ở app

Supabase PostgREST client không chạy transaction nhiều câu. Cách "rollback bằng UPDATE approved=False" của plan gốc để lại cửa sổ lỗi (crash giữa loop để lại task tạo dở và trạng thái approved sai). Thay bằng một Postgres function chạy trong một transaction DB thật:

```
approve_report_and_dispatch(p_report_id uuid, p_tasks jsonb, p_approver uuid)
  → UPDATE department_reports SET approved=true, approved_by=p_approver,
       approved_at=now(), suggested_tasks=p_tasks WHERE id=p_report_id AND approved=false
  → INSERT INTO tasks (title, priority, assigned_team, due_at, status, source, report_id)
       SELECT ... FROM jsonb_to_recordset(p_tasks)
  → RETURN số task đã tạo
```

Nếu report đã approved hoặc không tồn tại, function trả lỗi để API map sang 409/404. Cùng pattern `match_graph_nodes` đã dùng cho RAG.

Việc parse deadline (`"1h"/"24h"/"48h"/"1w"` sang `due_at` tuyệt đối) giữ ở Python (`_parse_deadline`, có default 48h, testable), API tính `due_at` trước rồi nhét vào `p_tasks` để RPC chỉ việc insert.

### 4.4 Tách mục 9 ra khỏi spec này

Như mục 2. Mục 9 không nằm trong bảy task.

## 5. Thay đổi data model

```
department_reports
  + suggested_tasks  JSONB NOT NULL DEFAULT '[]'   -- danh sách Draft Task
  + root_cause_summary TEXT                          -- tách khỏi Markdown để query riêng

tasks
  + report_id  UUID REFERENCES department_reports(id) ON DELETE SET NULL
  + source     TEXT NOT NULL DEFAULT 'agent' CHECK (source IN ('agent','report'))
  + index idx_tasks_report_id
```

Migration: `supabase/migrations/20260627000000_suggested_tasks_and_report_link.sql`. Kèm RPC `approve_report_and_dispatch` (có thể tách file migration riêng cùng ngày nếu rõ hơn).

## 6. Backend

- `report_builder.store_department_report(..., suggested_tasks, root_cause_summary)` ghi 2 cột mới. `orchestrator.py` truyền `action_items` (đã chuẩn hóa) và `root_cause_summary` từ analyst xuống. Giữ nguyên logic lock báo cáo đã approved.
- `PUT /api/reports/{id}/draft-tasks`: chỉ `manager`/`admin` của phòng (`can_view_team(user, report.team)`). Body `{suggested_tasks: [...]}`. Nếu `approved=true` trả 409, không tồn tại trả 404, hợp lệ thì UPDATE và trả 200.
- `POST /api/reports/{id}/approve-and-dispatch`: cùng RBAC. Python parse deadline thành `due_at`, build `p_tasks`, gọi RPC `approve_report_and_dispatch`. Trả `{status, tasks_created, report}`. RPC lo atomicity. Đã approved trả 409.
- Giữ `PATCH /api/reports/{id}/approve` cũ cho backward compatibility.

## 7. Frontend

- `reports.tsx`: type `Report` thêm `suggested_tasks: DraftTask[]` và `root_cause_summary: string | null`. Khi `approved=false` hiện Draft Task Editor (add/edit/delete từng field action/priority/deadline/owner/success_metric), nút "Lưu nháp" gọi PUT, nút "Duyệt và triển khai" gọi approve-and-dispatch. Hiển thị danh sách task open của phòng để Manager tránh trùng (mục 4.1). Sau khi duyệt chuyển view-only, badge "Đã duyệt" kèm người và thời điểm.
- `tasks.tsx`: type `Task` thêm `report_id: string | null` và `source`. Card task hiện badge nguồn; nếu `report_id != null` hiện link "Xem báo cáo gốc" sang `/reports`. Task cũ (source agent, report_id null) hiển thị bình thường.

## 8. RBAC

Cả hai endpoint mới kiểm `can_view_team(user, report.team)` để chặn Manager phòng A duyệt báo cáo phòng B. Backend vẫn chạy bằng service role nên đây là gate quyết định. Lưu ý: RLS hiện vẫn `USING(true)` (gap P0 trong co_che.md), nên frontend đọc cột mới qua Supabase realtime sẽ thấy. Spec này không sửa RLS.

## 9. Rủi ro và giảm thiểu

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Task trùng giữa hai nguồn | Trung bình | Cột `source` + hiện task open lúc dispatch (mục 4.1) |
| Atomicity khi dispatch nhiều task | Cao | RPC transaction (mục 4.3), bỏ try/except bù trừ |
| `suggested_tasks` null khi analyst không chạy | Trung bình | Default `'[]'` trong migration + fallback report_builder |
| Manager duyệt chéo phòng | Cao | `can_view_team` ở cả hai endpoint |
| Deadline string lạ từ LLM | Thấp | `_parse_deadline` default 48h |

## 10. Kiểm thử

- Unit: `_parse_deadline` với `"1h"/"24h"/"1w"` và string lạ. PUT draft-tasks (happy + 409 khi approved). approve-and-dispatch (tạo task có `report_id`, `source='report'`, `due_at` đúng; 409 khi đã approved).
- RPC: gọi 2 lần liên tiếp chỉ tạo task một lần (idempotent qua điều kiện `approved=false`).
- E2E: chạy pipeline sinh báo cáo có suggested_tasks, Manager sửa, duyệt, task hiện trên Task Board với badge nguồn và link báo cáo.

## 11. Task breakdown

Giữ 7 task của plan gốc, cập nhật theo 4 điều chỉnh:

1. Migration `20260627000000_...`: thêm `suggested_tasks`, `root_cause_summary`, `tasks.report_id`, `tasks.source`, index, và RPC `approve_report_and_dispatch`.
2. `report_builder` + `orchestrator` ghi `suggested_tasks` và `root_cause_summary`.
3. `PUT /api/reports/{id}/draft-tasks`.
4. `POST /api/reports/{id}/approve-and-dispatch` qua RPC.
5. `reports.tsx`: Draft Task Editor + duyệt + hiện task open của phòng.
6. `tasks.tsx`: badge nguồn + link báo cáo gốc.
7. Test cho 2 API + `_parse_deadline` + RPC.

Thứ tự: Task 1 trước, rồi 2/3 song song, 4 sau 3, 5 sau 3+4, 6 sau 5, 7 song song sau 4.
