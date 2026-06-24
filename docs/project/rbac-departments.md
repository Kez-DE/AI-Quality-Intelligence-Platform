# RBAC theo phòng ban

Hệ thống có hai trục phân quyền: **role** (cấp độ quyền) và **department** (phòng ban, quyết định thấy dữ liệu của ai). Backend chạy bằng `SUPABASE_SERVICE_ROLE_KEY` nên bypass RLS của Postgres, vì vậy mọi kiểm tra quyền phải làm ở tầng API trong `pipeline/auth_guard.py`.

## 4 role

| Role | Nhãn UI | Quyền |
|------|---------|-------|
| `admin` | Quản trị viên | Toàn quyền, quản lý user, trigger ingest/streaming, xem mọi phòng |
| `manager` | Quản lý | Giám sát phòng mình: alerts, tasks, insights, reports, chat |
| `staff` | Nhân viên | Công việc hàng ngày phòng mình: feedback, tasks, chat |
| `guest` | Khách | Dashboard, gửi feedback, chat hỗ trợ CSKH |

`VALID_ROLES = {admin, manager, staff, guest}`. `OPS_ROLES = {admin, manager, staff}` là nhóm nhân sự vận hành (phân biệt với guest).

## 4 phòng ban

`IT`, `CSKH`, `Vận hành`, `Marketing`. Định nghĩa ở `DEPARTMENTS` (`departments.py`), `DEPARTMENT_PERSONAS` (`analyst_agent.py`) và `valid_departments` (`users_admin.py`). Một ops user có thể chưa được gán phòng (`department = null`), khi đó không xem được dữ liệu phòng nào cho tới khi admin gán.

---

## Xác thực

`get_current_user` (`auth_guard.py`) lấy Bearer token từ header, gọi `db.auth.get_user(token)` để Supabase verify chữ ký JWT, rồi đọc `role` và `department` từ bảng `profiles`. Ba dependency gate:

- `get_current_user` — cho mọi user đã đăng nhập (gồm guest).
- `require_ops_staff` — chỉ `OPS_ROLES`, chặn guest (403).
- `require_admin` — chỉ admin (403 nếu khác).

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
| `PATCH /api/reports/{id}/approve` | team của report |
| `PUT /api/reports/{id}/draft-tasks` | team của report (409 nếu đã duyệt) |
| `POST /api/reports/{id}/approve-and-dispatch` | team của report (409 nếu đã duyệt) |
| `GET /api/insights/departments/{team}` | team trong path |

Endpoint admin-only (qua `require_admin`): `GET /api/agent/stats`, `POST /api/ingest-real-dataset`, `POST /api/live-stream/start|stop`, `POST /api/run-real-pipeline`, `POST /api/trigger-spike-detect`, `POST /api/feedback/reclassify`, và toàn bộ quản lý user.

## Quản lý user — `users_admin.py`

- `PATCH /api/users/{id}/role` — đổi role; chặn admin tự đổi quyền chính mình; ghi `audit_logs` action `role_change`.
- `PATCH /api/users/{id}/department` — gán phòng; `valid_departments = [null, IT, CSKH, Vận hành, Marketing]`; ghi audit.

Bootstrap: user đăng ký **đầu tiên** thành admin (migration RBAC), các user sau mặc định guest.

---

## Chat agent scope theo phòng

Endpoint `POST /api/agent/chat` phân hai luồng:

**Guest** dùng `GUEST_SYSTEM_PROMPT` — trợ lý CSKH chỉ trả lời về dùng app, đặt xe, thanh toán, khuyến mãi, khiếu nại. Tuyệt đối không truy cập dữ liệu nội bộ. RAG lấy từ `data/public_kb/` (chỉ file có `audience: public`). Rate limit riêng.

**Ops (staff/manager/admin)** dùng `AGENT_SYSTEM_PROMPT` + RAG nội bộ. Trong `agent_chat`, `scope_team = user.department` nếu role khác admin và có phòng, ngược lại None (admin xem toàn hệ thống). `scope_team` được truyền xuống `run_chat_agent`, rồi `execute_tool` ép mọi tool lọc về đúng phòng đó để chống rò rỉ dữ liệu chéo phòng.

RAG nội bộ (`knowledge_base.py`) lọc chunk theo `department` trong frontmatter: phòng không có tài liệu thì trả rỗng, **không** fallback sang phòng khác. KB hiện chỉ có doc cho 4 phòng (Safety, CSKH, Vận hành, IT); Pricing và Marketing trả rỗng là đúng thiết kế.

Cả hai luồng đều mask PII (`mask_pii`) ở input và output trước/sau khi gọi LLM.

---

## Phía frontend

`app/src/components/AppShell.tsx` render nav lọc theo role; `DepartmentBadge.tsx` hiển thị phòng (admin → "Toàn hệ thống"; ops có phòng → tên phòng; ops chưa gán → ẩn). Route `_authenticated/route.tsx` guard guest khỏi các trang nghiệp vụ (`/alerts`, `/insights`, `/admin`, `/tasks`, `/reports`, `/support`, `/health`, `/agent-control`), redirect về `/dashboard`. Đây là lớp bảo vệ UX; quyền thật vẫn được kiểm ở backend.

Xem thêm [guest-account.md](guest-account.md) về cơ chế tài khoản khách.
