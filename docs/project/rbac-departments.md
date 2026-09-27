# RBAC theo phòng ban

> **Cập nhật 2026-06-27:** đồng bộ 6 phòng ban & phân tầng quyền chat.
>
> **Cập nhật 2026-09-27 (US-077 / decision 0017):** bỏ role `guest`, thay bằng `pending` (tài khoản chờ cấp quyền); chỉ admin tạo tài khoản.

Hệ thống có hai trục phân quyền: **role** (cấp độ quyền) và **department** (phòng ban, quyết định thấy dữ liệu của ai). Backend chạy bằng `SUPABASE_SERVICE_ROLE_KEY` nên bypass RLS của Postgres, vì vậy mọi kiểm tra quyền phải làm ở tầng API trong `pipeline/auth_guard.py`.

## 4 role

| Role | Nhãn UI | Quyền |
|------|---------|-------|
| `admin` | Quản trị viên | Toàn quyền, quản lý user, trigger ingest/streaming, xem mọi phòng |
| `manager` | Quản lý | Giám sát phòng mình: alerts, tasks, insights, reports, chat |
| `staff` | Nhân viên | Công việc hàng ngày phòng mình: feedback, tasks, chat |
| `pending` | Chờ cấp quyền | Không có quyền gì cho tới khi admin cấp role. Backend trả 403 ở mọi endpoint trừ `GET /api/me`, `POST /api/me/password` và `/health` |

`VALID_ROLES = {admin, manager, staff, pending}`. `OPS_ROLES = {admin, manager, staff}` là nhóm nhân sự vận hành. Profile thiếu hoặc role không hợp lệ đều rơi về `pending` (fail-closed).

Khách hàng (người ngoài công ty) **không có tài khoản** và không có role: họ gửi phản hồi qua Customer web (`/api/public/*`, không token). Xem [guest-account.md](guest-account.md).

## 6 phòng ban

`IT`, `CSKH`, `Vận hành`, `Tài chính & Thanh toán`, `Sản phẩm`, `Quản lý Rủi ro & Gian lận`. Định nghĩa ở `DEPARTMENTS` (`departments.py`), `DEPARTMENT_PERSONAS` (`analyst_agent.py`) và `valid_departments` (`users_admin.py`). Một ops user có thể chưa được gán phòng (`department = null`), khi đó không xem được dữ liệu phòng nào cho tới khi admin gán.

---

## Xác thực

`get_current_user` (`auth_guard.py`) lấy Bearer token từ header, gọi `db.auth.get_user(token)` để Supabase verify chữ ký JWT, rồi đọc `role` và `department` từ bảng `profiles`, và `must_change_password` từ `app_metadata` của user (chỉ service role ghi được). Các dependency gate:

- `get_current_user` — xác thực user đã đăng nhập. Tài khoản `pending` qua được bước này nhưng chỉ dùng được `GET /api/me` và `POST /api/me/password`; mọi endpoint khác trả 403.
- `require_ops_staff` — chỉ `OPS_ROLES`, chặn `pending` (403).
- `require_manager` — chỉ manager hoặc admin (403 nếu khác).
- `require_admin` — chỉ admin (403 nếu khác).

Ba role guard trên còn trả 403 "Bạn cần đổi mật khẩu tạm trước khi tiếp tục" khi tài khoản còn cờ `must_change_password`. `GET /api/me` (trả cả `must_change_password`) và `POST /api/me/password` là hai route duy nhất chỉ cần danh tính.

---

## Hai helper scope phòng ban

`can_view_team(user, team)` — kiểm tra user có được xem một phòng cụ thể không:

- admin → luôn True.
- ops chưa gán phòng → False.
- ops đã gán phòng → True nếu `user.department == team`.

`scoped_team(user, requested_team)` — trả về team mà query nên lọc theo:

- admin → tôn trọng `requested_team` (None nghĩa là xem tất cả).
- ops chưa gán phòng → raise 403 ("Bạn chưa được gán phòng ban").
- ops đã gán phòng → luôn ép về `user.department`, bỏ qua `requested_team`.

Khác biệt: `scoped_team` dùng cho endpoint **list** (ép phạm vi truy vấn), `can_view_team` dùng cho endpoint **thao tác trên một record** (chặn ghi/đọc chéo phòng).

---

## Endpoint áp scope

Endpoint dùng `scoped_team` để ép manager/staff chỉ thấy dữ liệu phòng mình, admin thấy tất cả:

| Endpoint | Lọc theo |
|----------|----------|
| `GET /api/tasks` | `assigned_team` |
| `GET /api/reports` | `team` |
| `GET /api/agent/ai-log` | team (admin tôn trọng `?team`) |
| `GET /api/insights/departments` | chỉ giữ phòng được phép |

Endpoint dùng `can_view_team` để chặn thao tác chéo phòng:

| Endpoint | Kiểm tra |
|----------|----------|
| `PATCH /api/tasks/{id}/status` | team của task |
| `PATCH /api/tasks/{id}/assign` | team của task |
| `PATCH /api/alerts/{id}/status` | team (qua `task_id → assigned_team`) |
| `PATCH /api/reports/{id}/approve` | team của report — **`require_manager`**; 409 nếu báo cáo còn Draft Task (dùng approve-and-dispatch) |
| `PUT /api/reports/{id}/draft-tasks` | team của report — **`require_manager`**; 409 nếu đã duyệt |
| `POST /api/reports/{id}/approve-and-dispatch` | team của report — **`require_manager`**; 409 nếu đã duyệt |
| `PATCH /api/feedback/{id}/label` | team suy ra từ routing của feedback |
| `PATCH /api/feedback/{id}/review` | team suy ra từ routing của feedback |
| `POST /api/tasks/{id}/completion-report` | team của task + `owner_id` phải là chính user |
| `POST /api/tasks/{id}/support-resolve` | team của task + task phải có `source='ticket'` |
| `GET /api/insights/departments/{team}` | team trong path |

Endpoint admin-only (qua `require_admin`): `GET /api/agent/stats`, `POST /api/ingest-real-dataset`, `POST /api/live-stream/start|stop`, `POST /api/run-real-pipeline`, `POST /api/trigger-spike-detect`, `POST /api/feedback/reclassify`, và toàn bộ quản lý user (gồm tạo tài khoản `POST /api/admin/users`).

`POST /api/feedback/submit` giờ yêu cầu ops staff (trước đây mọi user đăng nhập đều gọi được).

## Quản lý user — `users_admin.py`

- `PATCH /api/users/{id}/role` — đổi role; chặn admin tự đổi quyền chính mình; ghi `audit_logs` action `role_change`.
- `PATCH /api/users/{id}/department` — gán phòng; `valid_departments = [null, IT, CSKH, Vận hành, Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận]`; ghi audit.
- `POST /api/admin/users` — admin tạo tài khoản `{email, full_name, role: admin|manager|staff, department?, temp_password}`. Mật khẩu tạm đạt 5 tiêu chí (≥ 8 ký tự, chữ hoa, chữ thường, chữ số, ký tự đặc biệt). Tạo bằng `auth.admin.create_user` (email xác nhận sẵn, `app_metadata.must_change_password = true`), trả 201; 400 chỉ nêu tên field sai; 409 nếu trùng email; ghi audit, không bao giờ log hay trả mật khẩu.
- `POST /api/me/password` — chính chủ đổi mật khẩu `{new_password}` (cùng 5 tiêu chí). Backend gọi `auth.admin.update_user_by_id` với mật khẩu mới và `app_metadata {must_change_password: false}`; lỗi 400/503 không bao giờ lặp lại mật khẩu. Không cần role, nên tài khoản còn mật khẩu tạm hoặc `pending` đều gọi được.
- `POST /api/users/bulk-approve` — duyệt hàng loạt tài khoản `pending` thành staff/manager.

Bootstrap: profile **đầu tiên** của hệ thống thành admin; mọi tài khoản tạo ngoài form của admin (ví dụ qua Supabase Dashboard) mặc định `pending`. Staff web không còn form tự đăng ký.

---

## Chat agent scope theo phòng

Endpoint `POST /api/agent/chat` chỉ dành cho ops staff (`pending` → 403) và phân hai luồng:

**Tầng công khai** (khi client gửi `public_only`, ví dụ widget trang chủ) dùng `PUBLIC_SYSTEM_PROMPT` — trợ lý CSKH chỉ trả lời về dùng app, đặt xe, thanh toán, khuyến mãi, khiếu nại. Tuyệt đối không truy cập dữ liệu nội bộ. RAG lấy từ `data/public_kb/` (chỉ file có `audience: public`). Rate limit riêng.

**Ops (staff/manager/admin)** dùng `AGENT_SYSTEM_PROMPT` + RAG nội bộ. Trong `agent_chat`, `scope_team = user.department` nếu role khác admin và có phòng, ngược lại None (admin xem toàn hệ thống). `scope_team` được truyền xuống `run_chat_agent`, rồi `execute_tool` ép mọi tool lọc về đúng phòng đó để chống rò rỉ dữ liệu chéo phòng.

RAG nội bộ (`knowledge_base.py`) lọc chunk theo `department` trong frontmatter: phòng không có tài liệu thì trả rỗng, **không** fallback sang phòng khác. KB nội bộ hiện chỉ có doc cho IT, CSKH, Vận hành (và nhóm SOP Safety); ba phòng Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận chưa có tài liệu nên trả rỗng là đúng thiết kế.

Cả hai luồng đều mask PII (`mask_pii`) ở input và output trước/sau khi gọi LLM.

---

## Phía frontend

`app/src/components/AppShell.tsx` render nav lọc theo role; `DepartmentBadge.tsx` hiển thị phòng (admin → "Toàn hệ thống"; ops có phòng → tên phòng; ops chưa gán → ẩn). Layout `_authenticated` chặn theo thứ tự: tài khoản có cờ `app_metadata.must_change_password` chỉ thấy màn đổi mật khẩu (gọi `POST /api/me/password`, rồi `supabase.auth.refreshSession()`); tài khoản `pending` chỉ thấy màn "Tài khoản đang chờ admin cấp quyền" (không nav, không tải dữ liệu). Route guard còn chặn staff/manager khỏi `/admin` và staff khỏi `/insights`, `/reports`, `/completion-reports`. Đây là lớp bảo vệ UX; quyền thật vẫn được kiểm ở backend.

Xem thêm [guest-account.md](guest-account.md) về Khách hàng, tài khoản `pending` và cách tạo tài khoản.
