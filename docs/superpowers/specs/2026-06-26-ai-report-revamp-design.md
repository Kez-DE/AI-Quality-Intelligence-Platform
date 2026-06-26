# Thiết kế: Nâng cấp Báo cáo AI (giữ 4 phòng ban)

- Ngày: 2026-06-26
- Nhánh: `feat/ai-report-revamp`
- Nguồn: tích hợp chọn lọc commit `d2d38f7` ("sửa báo cáo AI") trên `origin/docs`
- Lane (FEATURE_INTAKE): **High-risk** — chạm data model (migration), đổi hành vi
  báo cáo hiện có, đa miền (backend agent + frontend), proof còn yếu.

## 1. Mục tiêu

Áp dụng phần **logic báo cáo tự động AI** từ nhánh `docs` vào `main`, đồng thời:

1. **Giữ 4 phòng ban** (IT, CSKH, Vận hành, Marketing). Không áp dụng đổi 4→6 phòng.
2. Sửa lỗi UI: trang "Báo cáo hoàn thành" không hiển thị **tên task** mà báo cáo
   đang nói tới — quản lý không biết đang duyệt báo cáo của task nào.
3. Điều chỉnh prompt + cách dựng báo cáo AI để nhìn vào là biết: **vấn đề là gì**,
   **cần giải quyết gì**, **đề xuất giải quyết**.
4. Cập nhật tài liệu tổng quan cơ chế cho khớp.

## 2. Quyết định đã chốt

- **Cơ chế báo cáo**: theo `docs` — cho phép **nhiều báo cáo/ngày** (bỏ unique
  constraint `(team, report_date)`, bỏ khoá "báo cáo đã duyệt", dùng `insert`),
  tách worker: alert chạy mỗi chu kỳ (cửa sổ 1h), báo cáo sinh theo lịch cron
  **09:00 & 14:00**.
- **Nội dung báo cáo**: 3 khối — *Vấn đề ghi nhận* → *Phân tích & nguyên nhân* →
  *Đề xuất giải quyết*, kèm tiêu đề `prominent_theme`.
- **Chiến lược tích hợp**: áp dụng thủ công theo từng hunk (KHÔNG cherry-pick cả
  commit), để loại bỏ phần 6 phòng ban, file rác, refactor `chat.tsx`, và migration
  trùng.

## 3. Phạm vi áp dụng từ `d2d38f7`

### Áp dụng (đã bỏ phần phòng ban)

| File | Thay đổi giữ lại |
| --- | --- |
| `pipeline/agents/schemas.py` | Thêm `prominent_theme`, `feedback_summary`, `detailed_analysis` vào `AnalystAnalysis` — **optional + default `""`** để response LLM/mock thiếu trường không làm vỡ parse. |
| `pipeline/agents/analyst_agent.py` | Prompt mới (tiêu đề danh từ trang trọng + 3 trường mới) và nhánh fallback. **Giữ persona Marketing**, KHÔNG thêm persona Tài chính/Sản phẩm/Rủi ro. |
| `pipeline/agents/report_builder.py` | Tiêu đề thêm hậu tố `prominent_theme`; đổi `store_department_report` từ `upsert`→`insert` (nhiều báo cáo/ngày); dựng body 3 khối (xem WS3). |
| `pipeline/agents/task_agent.py` | Truyền `suggested_tasks` + `root_cause_summary` vào `store_department_report`. |
| `pipeline/agents/orchestrator.py` | Thêm cờ `run_alert` / `run_report` cho `run_agent_pipeline`. |
| `pipeline/worker_agent.py` | Tách `run_alert_pipeline` (mỗi `INTERVAL`, 1h) + `run_report_pipeline` (cron 09:00, 14:00). |
| `app/src/routes/_authenticated/reports.tsx` | Tiêu đề báo cáo lấy từ dòng đầu nội dung; hiển thị `created_at` (thêm `created_at` vào type `Report`). |
| `pipeline/tests/test_report_approval.py`, `pipeline/tests/test_report_builder.py` | Lấy các test mới (đã chỉnh cho 4 phòng ban). |

### Loại trừ

- `pipeline/departments.py`, `data/taxonomy/routing_table.json`,
  `app/src/components/DepartmentBadge.tsx`, `app/src/lib/api.ts` (Department type),
  `app/src/routes/_authenticated/insights.tsx` — tất cả là đổi 4→6 phòng ban.
- `app/src/routes/_authenticated/chat.tsx` — refactor không liên quan.
- `scratch/fix.py`, `scratch/fix2.py` — file rác.
- Root `IMPLEMENTATION_PLAN.md`, `co_che.md` — `main` đã chủ động dời/xoá.
- `supabase/migrations/20260626000000_suggested_tasks_and_report_link.sql` — **trùng**;
  `main` đã có `20260627000000_suggested_tasks_and_report_link.sql` (cùng nội dung cột).

## 4. Workstream chi tiết

### WS1 — Logic báo cáo (4 phòng ban)
Áp dụng các hunk ở bảng trên. Lưu ý quan trọng:
- `feedback_summary` / `detailed_analysis` để **optional, default `""`** (khác với
  docs để required) nhằm tránh `ValidationError` khi LLM trả thiếu trường.
- Persona `Marketing` giữ nguyên; `DEPARTMENT_PERSONAS` không thêm khoá mới.

### WS2 — Tên task trong "Báo cáo hoàn thành" (ask B)
- Backend `GET /api/completion-reports` và `GET /api/tasks/{id}/completion-reports`:
  bổ sung `task_title` cho mỗi bản ghi. Cách: Supabase select FK-embed
  `select("*, tasks(title)")` (FK `task_completion_reports.task_id → tasks.id` đã có
  index `idx_tcr_task_id`); nếu embed không khả dụng thì batch-fetch title theo
  `task_id` rồi map. Trả thêm field `task_title` (string|null).
- Frontend `completion-reports.tsx`: thêm `task_title` vào type `CompletionReport`,
  hiển thị làm tiêu đề thẻ (đậm, phía trên ô ghi chú). Để trống → fallback "Task".

### WS3 — Cấu trúc nội dung báo cáo (ask C)
`build_department_report_markdown` dựng lại body:

```
# Báo cáo Vận hành - Phòng {team}: {prominent_theme}
> Kỳ dữ liệu … | (giữ dòng meta hiện tại)

## Vấn đề ghi nhận
{feedback_summary}

## Phân tích & nguyên nhân
{detailed_analysis}
Nguyên nhân (cần xác minh): {root_cause_summary}
Mức rủi ro: {risk_level}
Bằng chứng:
- {evidence[i]}

## Đề xuất giải quyết
- [{priority}] {action} — hạn {deadline}

## Số liệu (giữ bảng KPI + top topics hiện tại)
```

- Khi thiếu `feedback_summary`/`detailed_analysis` (mock/LLM lỗi) → hiển thị câu
  fallback đã có trong `_fallback_analysis`, không để khối trống vô nghĩa.

### WS4 — Tài liệu cơ chế
- So sánh nội dung `co_che.md` trên `origin/docs` (root) với
  `docs/project/co_che.md` của `main`; gộp phần mô tả cơ chế báo cáo mới (nhiều
  báo cáo/ngày, lịch 09:00/14:00, 3 khối nội dung) vào file của `main`. KHÔNG tạo
  lại file ở root. Cập nhật dòng tính năng báo cáo trong `README.md` nếu cần.

## 5. Migration & Supabase
- **Migration mới**: `supabase/migrations/2026XXXXmmss_remove_unique_department_reports.sql`
  → `ALTER TABLE public.department_reports DROP CONSTRAINT IF EXISTS
  department_reports_team_date_unique;` (đặt timestamp sau migration unique cũ).
- **Thứ tự bắt buộc**: drop unique constraint phải áp **trước** khi `report_builder`
  chạy `insert`, nếu không insert bản thứ hai trong ngày sẽ vi phạm constraint.
- **Gotcha đã biết**: migration cột `suggested_tasks` / `report_id`
  (`20260627000000`) cần được **áp thật lên Supabase remote** thì
  `suggested_tasks` và liên kết `report_id` mới hoạt động. Kế hoạch bao gồm bước áp
  các migration đang chờ.

## 6. Kiểm thử
- Lấy `test_report_approval.py`, bổ sung `test_report_builder.py` (4 phòng ban).
- Thêm test: markdown báo cáo chứa đủ 3 tiêu đề khối; `prominent_theme` vào tiêu đề.
- Thêm test: `GET /api/completion-reports` trả về `task_title`.
- Chạy `pytest pipeline/tests`, build frontend (`npx vite build` / typecheck).

## 7. Bàn giao
- Verify trên nhánh (test backend + typecheck frontend + thử luồng báo cáo).
- PR `feat/ai-report-revamp` → `main`; sau merge thì pull về local `main`.
- Commit/push chỉ thực hiện khi người dùng yêu cầu.

## 8. Rủi ro & giảm thiểu
| Rủi ro | Giảm thiểu |
| --- | --- |
| Insert báo cáo thứ 2/ngày vi phạm unique | Áp migration drop constraint trước |
| Trường schema required làm vỡ parse response cũ | Để optional + default `""` |
| FK-embed `tasks(title)` không khả dụng | Fallback batch-fetch title theo id |
| Migration cột chưa áp trên remote | Bước áp migration trong kế hoạch |
| Lẫn phần 6 phòng ban khi áp hunk | Áp thủ công từng file, review diff trước commit |

## 9. Ngoài phạm vi
- Đổi 4→6 phòng ban (cố ý loại trừ).
- Refactor `chat.tsx`.
- Thay đổi cơ chế phân loại/định tuyến ngoài báo cáo.
