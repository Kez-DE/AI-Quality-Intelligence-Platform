# Thiết kế: Vòng khép kín giao việc & duyệt hoàn thành task

> Spec cho luồng top-down: manager/admin giao task → staff nhận & xử lý → gửi báo cáo
> hoàn thành → manager duyệt. Kèm bảng audit log ghi lại toàn bộ vòng đời.
> Ngày: 2026-06-25. Nhánh đề xuất triển khai: tách từ `main`.

## 1. Bối cảnh & vấn đề

Hệ thống đã có Task Board (`tasks`), báo cáo phân tích (`department_reports`), và một phần
luồng "Báo cáo hoàn thành" (`task_completion_reports` + endpoint + UI `completion-reports.tsx`).
Tuy nhiên luồng giao việc từ trên xuống đang sai ở ba chỗ, đã xác nhận với người dùng:

1. **RBAC sai.** Endpoint `PATCH /api/tasks/{id}/assign` gate bằng `require_ops_staff` nên
   **staff cũng giao được task**, và `/api/users/assignable` trả về cả `manager`/`admin` nên
   task **gán được cho quản lý**. Trái với `docs/project/co_che.md`: việc giao là của
   manager/admin, staff chỉ xử lý và gửi báo cáo.

2. **State machine duyệt bị hỏng.** Khi staff gửi báo cáo `completed`, code lập tức set task
   `resolved` (`pipeline/main.py:665`) — *trước khi* quản lý duyệt. Còn khi quản lý duyệt/trả
   lại (`review_completion_report`), code **không đổi trạng thái task**. Hệ quả: phê duyệt chỉ
   mang tính trang trí, vòng lặp không đóng đúng.

3. **Báo cáo hoàn thành không lưu được.** Người dùng thấy "gửi báo cáo bị lỗi / không vào DB".
   Nguyên nhân nhiều khả năng: migration `20260626000000_task_completion_reports.sql` **chưa
   được apply lên Supabase thật**, nên INSERT trả 503. Ngoài ra hệ thống **chưa có bảng audit
   log** ghi lại vòng đời task như người dùng yêu cầu.

### Mục tiêu

- Chỉ manager/admin được giao task; người nhận **bắt buộc là staff** cùng phòng.
- Vòng đời task khép kín có bước nhận việc tường minh và cổng duyệt thật:
  `open → assigned → in_progress → pending_review → resolved` (reject → `in_progress`).
- Có bảng `task_events` ghi lại mọi mốc: giao → nhận → gửi báo cáo → duyệt/trả lại, kèm actor.
- Đảm bảo bảng `task_completion_reports` tồn tại trên Supabase thật để báo cáo lưu được.

### Ngoài phạm vi (YAGNI)

- Không thêm hành động `reassign` (giao lại) trong vòng này — manager có thể đổi `owner_id`
  qua `assign` hiện có; ghi log `assigned` lần nữa là đủ.
- Không làm thông báo realtime/push mới ngoài việc thêm bảng vào publication có sẵn.
- Không đụng luồng sinh task tự động (`task_agent`) hay HI-Loop Approval (`approve-and-dispatch`).
- Không mở rộng 6 phòng ban. Giữ đúng 4 phòng: IT, CSKH, Vận hành, Marketing.

## 2. Mô hình vai trò (đã chốt)

| Vai trò | Quyền trong luồng này |
|---|---|
| `admin` | Giao task xuyên phòng; nhận thay không áp dụng (admin không phải người nhận); duyệt báo cáo mọi phòng. |
| `manager` | Giao task trong phòng mình cho staff phòng mình; duyệt báo cáo phòng mình. |
| `staff` | Là người nhận hợp lệ: nhận việc, xử lý, gửi báo cáo hoàn thành. **Không** được giao task cho người khác. |
| `guest` | Không truy cập. |

Người nhận task (`owner_id`) **chỉ được là `staff`** thuộc đúng phòng của task.

## 3. State machine

```
        manager/admin assign (owner=staff)
  open ─────────────────────────────────────▶ assigned
                                                  │ staff (owner) bấm "Nhận việc"
                                                  ▼
                                            in_progress ◀───────────┐
                                                  │                 │ manager reject
              staff gửi báo cáo completed         │                 │ (kèm review_note)
                                                  ▼                 │
                                            pending_review ─────────┘
                                                  │ manager approve
                                                  ▼
                                              resolved
```

Chuyển trạng thái hợp lệ (validator `_assert_transition` ở backend):

| from | to | tác nhân/sự kiện |
|---|---|---|
| `open` | `assigned` | manager/admin assign |
| `assigned` | `in_progress` | staff (owner) accept |
| `assigned` | `assigned` | manager đổi owner (re-assign) — hợp lệ |
| `in_progress` | `pending_review` | staff gửi báo cáo `completed` |
| `pending_review` | `resolved` | manager approve |
| `pending_review` | `in_progress` | manager reject |

Báo cáo `partial`/`blocked`: task giữ `in_progress` (không vào `pending_review`); chỉ ghi event.
`update_task_status` thủ công (nếu còn dùng) phải đi qua validator; chuyển không hợp lệ → 400.

## 4. Data model

### 4.1 `tasks.status` — mở rộng

- Thêm CHECK: `status IN ('open','assigned','in_progress','pending_review','resolved')`.
- Hiện `tasks.status` là `TEXT DEFAULT 'open'` không có CHECK (migration `20260616120000`),
  nên thêm CHECK là không phá dữ liệu cũ (open/in_progress/resolved đều nằm trong tập mới).
- Migration phải `DROP CONSTRAINT IF EXISTS` trước khi `ADD CONSTRAINT` để chạy lại idempotent.

### 4.2 Bảng mới `task_events` (audit log)

```sql
CREATE TABLE IF NOT EXISTS public.task_events (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  task_id UUID NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
  actor_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  actor_email TEXT,
  actor_role TEXT,
  team TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN (
    'assigned','accepted','completion_submitted',
    'completion_approved','completion_rejected','reopened','status_changed'
  )),
  from_status TEXT,
  to_status TEXT,
  completion_report_id UUID REFERENCES public.task_completion_reports(id) ON DELETE SET NULL,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_task_events_task_id ON public.task_events(task_id);
CREATE INDEX IF NOT EXISTS idx_task_events_team ON public.task_events(team, created_at DESC);
```

- Grants & RLS giống `task_completion_reports`: SELECT cho `authenticated` (gate phòng ở API),
  ALL cho `service_role`; thêm policy INSERT `authenticated` dự phòng. Bật RLS.
- `ALTER PUBLICATION supabase_realtime ADD TABLE public.task_events;`
- `actor_*` lưu snapshot để hiển thị mà không cần join sang `profiles`/`auth.users`.

### 4.3 `task_completion_reports`

Bảng đúng rồi, không đổi schema. Yêu cầu vận hành: **apply migration lên Supabase thật** và
verify bằng `information_schema`. Migration đã `CREATE TABLE IF NOT EXISTS` nên an toàn chạy lại.

## 5. Backend

File: `pipeline/auth_guard.py`, `pipeline/main.py`. Backend chạy `service_role` (bypass RLS),
quyền gate ở tầng API — giữ nguyên nguyên tắc này.

### 5.1 `auth_guard.py`

- Thêm `require_manager(user) -> AuthUser`: cho qua nếu `role in {'manager','admin'}`, ngược lại 403.

### 5.2 Helper trong `main.py`

- `_assert_transition(from_status: str, to_status: str) -> None`: raise `HTTPException(400)` nếu
  cặp chuyển không nằm trong bảng mục 3.
- `_log_task_event(db, *, task_id, actor, team, action, from_status=None, to_status=None,
  completion_report_id=None, note=None) -> None`: INSERT một dòng `task_events`. Lỗi ghi log
  **không được** làm hỏng thao tác chính (bọc try/except, log cảnh báo) — audit là phụ trợ.

### 5.3 Endpoint thay đổi / thêm

| Method & path | Guard | Hành vi |
|---|---|---|
| `PATCH /api/tasks/{id}/assign` | `require_manager` | `can_view_team` cho task; owner phải tồn tại, `role='staff'`, `department == task.assigned_team`; set `status='assigned'`, `owner_id`; ghi event `assigned`. |
| `POST /api/tasks/{id}/accept` *(mới)* | `require_ops_staff` | Chỉ `owner_id == user.id` (staff) được nhận; `assigned → in_progress`; ghi event `accepted`. Sai owner → 403; sai trạng thái → 400. |
| `POST /api/tasks/{id}/completion-report` | `require_ops_staff` | Giữ `can_view_team`; **bỏ auto-resolve**. `completed` → task `in_progress → pending_review`; `partial`/`blocked` → giữ `in_progress`. Ghi event `completion_submitted` kèm `completion_report_id`. |
| `PATCH /api/completion-reports/{id}/review` | `require_ops_staff` + chặn role | Giữ chặn `manager`/`admin`. `approved` → task `pending_review → resolved`, event `completion_approved`. `rejected` → task `pending_review → in_progress`, event `completion_rejected`. |
| `GET /api/users/assignable` | `require_ops_staff` | Lọc `role = 'staff'` (bỏ manager/admin khỏi danh sách người nhận); giữ scope phòng ban. |
| `PATCH /api/tasks/{id}/status` | `require_ops_staff` | Mọi chuyển trạng thái đi qua `_assert_transition`; ghi event `status_changed`. |
| `GET /api/tasks/{id}/events` *(mới)* | `require_ops_staff` | Trả audit trail của task, `can_view_team` theo `assigned_team`, order `created_at` desc. |

Ghi chú nhất quán: `review` đổi trạng thái task bên trong cùng thao tác duyệt; nếu task không
ở `pending_review` (vd báo cáo cũ) thì duyệt vẫn cập nhật bản ghi báo cáo nhưng không ép
chuyển trạng thái không hợp lệ (bỏ qua transition, vẫn ghi event).

## 6. Frontend

### 6.1 `app/src/routes/_authenticated/tasks.tsx`

- Nút "Giao việc" + dropdown người nhận **chỉ render khi** `me.role` là `manager`/`admin`.
  Dropdown chỉ liệt kê staff (API đã lọc; FE cũng lọc phòng thủ).
- Với `staff` là owner: task `assigned` hiện nút **"Nhận việc"** → `POST .../accept`.
- Form "Gửi báo cáo hoàn thành" chỉ hiện khi task `in_progress` và là việc của mình.
- Badge trạng thái bổ sung `assigned` ("Đã giao"), `pending_review` ("Chờ duyệt").
- (Tuỳ chọn, giữ nếu nhanh) timeline sự kiện lấy từ `GET /api/tasks/{id}/events`.

### 6.2 `app/src/routes/_authenticated/completion-reports.tsx`

- Giữ luồng duyệt hiện có; sau approve/reject hiển thị đúng trạng thái task tương ứng
  (resolved / quay lại in_progress). Cập nhật state cục bộ theo response.

## 7. Migrations & vận hành

1. Migration mới `supabase/migrations/<ts>_task_events_and_status.sql`:
   tạo `task_events` (mục 4.2) + mở rộng CHECK `tasks.status` (mục 4.1), idempotent.
2. Apply lên Supabase thật: `20260626000000_task_completion_reports.sql` (nếu chưa) và migration mới.
3. Verify:
   - `SELECT to_regclass('public.task_completion_reports');` và `('public.task_events');` khác NULL.
   - `information_schema.check_constraints` có ràng buộc status mới.

## 8. Kiểm thử (pytest, `pipeline/tests/`)

RBAC:
- staff gọi `/assign` → 403.
- manager gán owner là manager/admin → 400.
- `/users/assignable` không chứa manager/admin.
- manager phòng A gán task phòng B → 403.

State machine:
- assign(open→assigned) → accept(assigned→in_progress) → submit completed(→pending_review)
  → approve(→resolved). Đường reject: pending_review → in_progress.
- accept khi không phải owner → 403; accept task `open` (chưa giao) → 400.
- submit `partial` giữ in_progress.
- chuyển trạng thái không hợp lệ qua `/status` → 400.

Audit log:
- mỗi bước sinh đúng một dòng `task_events` với `action`, `actor_id`, `from_status`,`to_status`
  đúng; `completion_submitted`/`completion_approved` có `completion_report_id`.

Hồi quy:
- completion-report insert thành công (chống lại lỗi "không lưu được").
- không phá `test_router_agent`, `test_classifier`, các test report hiện có.

## 9. Phân loại rủi ro (FEATURE_INTAKE)

Cờ rủi ro: Authorization (đổi RBAC giao việc), Data model (bảng mới + CHECK), Audit/security
(audit log), Existing behavior (đổi state machine duyệt). → **High-risk**. Plan sẽ lập story
folder high-risk và ghi decision cho thay đổi RBAC + state machine + bảng audit.

## 10. Câu hỏi mở

- Timeline sự kiện trên UI task: làm ngay trong vòng này hay để sau? (mặc định: làm nếu rẻ,
  cắt nếu phình.)
- Có cần endpoint tổng hợp audit toàn phòng (`GET /api/task-events?team=`) cho trang giám sát
  của manager không, hay chỉ cần per-task `GET /api/tasks/{id}/events` là đủ ở bước này.
</content>
</invoke>
