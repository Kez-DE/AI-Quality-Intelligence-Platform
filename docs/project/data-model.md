# Mô hình dữ liệu Supabase (Data Dictionary)

> **Cập nhật 2026-06-27:** đồng bộ với migrations Supabase (6 phòng, task/report/correction).
>
> **Cập nhật 2026-09-27:** cột phản hồi ẩn danh của US-076 (`public_ref`, `submitter_hash`,
> `retention_until`) và của US-077 (`redacted_at`); role `guest` đổi thành `pending`.

Tài liệu này mô tả toàn bộ bảng, cột, kiểu dữ liệu và ý nghĩa nghiệp vụ của cơ sở dữ liệu
Postgres trên Supabase. Đây là tài liệu tra cứu chính cho ai cần hiểu dữ liệu chảy qua hệ
thống: từ lúc khách gửi phản hồi, qua phân loại AI, sinh cảnh báo, gom thành công việc, cho
tới khi quản lý duyệt báo cáo.

Nguồn sự thật là các file trong `supabase/migrations/`. Khi schema thay đổi, sửa migration
trước rồi cập nhật lại tài liệu này.

Lưu ý về quyền: backend FastAPI chạy bằng `SERVICE_ROLE_KEY` nên bỏ qua Row Level Security
(RLS). Quyền truy cập thực sự được kiểm tra ở tầng API (`pipeline/auth_guard.py`). Các policy
RLS mô tả bên dưới chỉ áp dụng khi frontend gọi Supabase trực tiếp (chat, realtime, một số
thao tác đọc), và đóng vai trò lớp phòng thủ.

## 1. Bản đồ quan hệ

```
                         auth.users (Supabase Auth, quản lý sẵn)
                              │ 1:1
                              ▼
                          profiles ──────────── role, department
                              │
        ┌─────────────────────┼───────────────────────────────┐
        │ user_id              │ corrected_by / actor          │ owner_id / actor_id
        ▼                      ▼                                ▼
     feedback            correction_logs                     tasks ──── report_id ──┐
        │  (1 feedback         (sửa nhãn AI)            │  source: agent|report     │
        │   nhiều correction)                          │                           │
        │                                              │  task_id                  │
        ▼  gom cụm (spike)                             ▼                           │
     alerts ──── task_id ──────────────────────────► (nhóm alert vào task)         │
        │                                              │                           │
        │                                       ┌──────┴───────┐                   │
        │                                       ▼              ▼                   │
        │                          task_completion_reports   task_events           │
        │                          (staff báo cáo,           (audit vòng đời:       │
        │                           manager duyệt)            giao→nhận→duyệt)      │
        │                                                                          │
        └───────────── tổng hợp ──────────────► department_reports ◄───────────────┘
                                                 (báo cáo phân tích + suggested_tasks)

   Tri thức (Graph RAG, độc lập với luồng trên):
     graph_nodes ──< graph_edges >── graph_nodes        (SOP, taxonomy, quan hệ)

   Quan sát hệ thống:
     agent_run_logs (mỗi lần gọi LLM/agent)      audit_logs (admin đổi quyền/xoá user)
     chat_messages (hội thoại trợ lý)
```

## 2. Danh tính và phân quyền

### `profiles`
Hồ sơ người dùng, mở rộng từ `auth.users`. Mỗi user Supabase có đúng một dòng ở đây, tạo tự
động bằng trigger `handle_new_user` khi tài khoản được tạo (admin tạo qua `POST /api/admin/users`,
hoặc tạo trong Supabase Dashboard). Staff web không còn form tự đăng ký.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `id` | UUID, PK | Trỏ tới `auth.users(id)`. Xoá user là xoá profile (CASCADE). |
| `email` | TEXT | Email, sao chép từ auth lúc tạo tài khoản. |
| `full_name` | TEXT | Tên hiển thị. Mặc định lấy phần trước `@` của email nếu không khai báo. |
| `role` | TEXT | Vai trò RBAC: `admin`, `manager`, `staff`, `pending`. Mặc định `pending` (cả DEFAULT của cột lẫn trigger; xem mục 10). `pending` là tài khoản chờ cấp quyền, không có quyền gì. |
| `department` | TEXT | Phòng ban: `IT`, `CSKH`, `Vận hành`, `Tài chính & Thanh toán`, `Sản phẩm`, `Quản lý Rủi ro & Gian lận`. `NULL` nghĩa là chưa được gán phòng, khi đó ops user chưa xem được dữ liệu phòng nào. |
| `created_at` / `updated_at` | TIMESTAMPTZ | Thời điểm tạo và cập nhật. |

Ứng dụng: quyết định một người thấy gì và làm được gì. `role` chia theo bậc quyền, `department`
chia theo phạm vi phòng. User thường chỉ tự sửa được `full_name` (đã thu hồi quyền UPDATE toàn
bảng để không ai tự nâng quyền qua REST). Từ migration `20260927000000`, `authenticated` cũng
không còn quyền `INSERT`, `DELETE`, `TRUNCATE` trên bảng này: profile chỉ do trigger tạo và chỉ
đổi qua backend.

Cờ bắt đổi mật khẩu ở lần đăng nhập đầu (`must_change_password`) không nằm trong bảng này mà
nằm trong `app_metadata` của `auth.users` (chỉ service role ghi được). `POST /api/admin/users` đặt
cờ; chỉ `POST /api/me/password` xoá cờ, cùng lúc đặt mật khẩu mới. Trong database, hàm
`password_is_current()` đọc cờ này từ JWT (xem mục 10).

### `audit_logs`
Nhật ký hành động quản trị nhạy cảm: admin đổi quyền hoặc xoá user.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `id` | UUID, PK | |
| `actor_id` | UUID | Admin thực hiện hành động. |
| `actor_email` | TEXT | Email admin (lưu lại để hiển thị kể cả khi user bị xoá). |
| `action` | TEXT | Loại hành động: `role_change`, `user_delete`, `bulk_approve`, `user_create` (admin tạo tài khoản; không bao giờ lưu mật khẩu). |
| `target_id` | UUID | User bị tác động. |
| `target_email` | TEXT | Email user bị tác động. |
| `details` | JSONB | Chi tiết, ví dụ `{"old_role":"pending","new_role":"staff"}`. |
| `created_at` | TIMESTAMPTZ | |

Ứng dụng: truy vết ai đổi quyền cho ai, lúc nào. Chỉ admin đọc được; chỉ backend ghi.

## 3. Tiếp nhận phản hồi

### `feedback`
Bảng trung tâm của khâu tiếp nhận. Mỗi dòng là một phản hồi của khách, kèm nhãn do tầng phân
loại (ML + rule) gán.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `id` | UUID, PK | |
| `user_id` | UUID, nullable | Người gửi (hoặc tài khoản nhập liệu). `NULL` với phản hồi ẩn danh từ Customer web. |
| `source` | TEXT | Nguồn dữ liệu: `manual` (gửi trong Staff web), `chat` (tool chat), `public` (khách hàng gửi từ Customer web, không tài khoản), hoặc tên dataset khi nạp hàng loạt. Mặc định `manual`. |
| `channel` | TEXT | Kênh: `app`, `ch_play`, `app_store`... Mặc định `app`. |
| `text` | TEXT | Nội dung phản hồi (đã làm sạch PII trước khi lưu). |
| `topic` | TEXT | Chủ đề do phân loại gán: `Safety`, `Driver Behavior`, `App Issue`, `Payment`, `Pricing`, `Delay`, `Other`. |
| `sentiment` | TEXT | Cảm xúc: `positive`, `neutral`, `negative`. |
| `severity` | TEXT | Mức nghiêm trọng `P1`..`P5` (P5 nặng nhất). |
| `area` | TEXT | Khu vực địa lý suy ra từ nội dung (ví dụ tỉnh/thành). |
| `confidence` | NUMERIC | Độ tự tin của nhãn (0..1). Thấp thì gắn cờ cần duyệt. |
| `needs_review` | BOOLEAN | AI đánh dấu cần người duyệt (lưới Safety, severity cao, confidence thấp). |
| `reviewed` | BOOLEAN | Đã có người xử lý (duyệt hoặc sửa nhãn). |
| `review_reason` | TEXT | Lý do cần duyệt, hiển thị trên hàng đợi duyệt. |
| `risk_safety` | INTEGER | Điểm 0..10: đe doạ tính mạng, tai nạn. |
| `risk_fraud` | INTEGER | Điểm 0..10: chiếm đoạt, gian lận cước. |
| `risk_attitude` | INTEGER | Điểm 0..10: cư xử không chuẩn mực. |
| `risk_vehicle` | INTEGER | Điểm 0..10: xe hỏng, mất vệ sinh. |
| `risk_compliance` | INTEGER | Điểm 0..10: sai đường, trễ giờ, không tuân thủ quy trình. |
| `overall_risk` | INTEGER | Điểm rủi ro tổng hợp 1..5 từ thuật toán Max-Pooling Waterfall. `NULL` nghĩa là chưa chấm. |
| `public_ref` | TEXT | Mã tra cứu của phản hồi ẩn danh (72 bit ngẫu nhiên). Unique khi khác `NULL`. Là credential duy nhất để khách xem trạng thái. |
| `submitter_hash` | TEXT | Hash SHA-256 có salt của IP người gửi, chỉ để rate limit và điều tra lạm dụng. Bị xoá (`NULL`) khi hết hạn lưu trữ. |
| `retention_until` | TIMESTAMPTZ | Hạn lưu trữ nội dung của phản hồi ẩn danh: ngày gửi + 180 ngày. |
| `redacted_at` | TIMESTAMPTZ | Thời điểm job retention đã xoá nội dung. `NULL` nghĩa là chưa xoá. |
| `created_at` | TIMESTAMPTZ | |

Ràng buộc `feedback_identity_chk`: mỗi dòng phải có `user_id` hoặc `public_ref`.

Ứng dụng: vừa là nguồn cho dashboard và hàng đợi duyệt, vừa là đầu vào cho bộ phát hiện cụm
bất thường (spike) sinh ra `alerts`. Năm cột `risk_*` là ma trận rủi ro chi tiết; `overall_risk`
là điểm gộp dùng để xếp ưu tiên nhanh.

Phản hồi ẩn danh (`source = 'public'`): khách tra cứu bằng `public_ref` và chỉ nhận
`public_ref`, trạng thái và `created_at`. Trạng thái không lưu mà suy ra: `reviewed` khi
`reviewed = true`, `under_review` khi `needs_review = true`, còn lại `received`. Mỗi ngày lúc
03:00 (giờ Việt Nam), `backend-worker` chạy `redact_expired_public_feedback`: với các dòng
`public` đã quá `retention_until` và chưa xoá, thay `text` bằng "[Đã xoá theo hạn lưu trữ]",
đặt `submitter_hash = NULL`, ghi `redacted_at`, và xoá `correction_logs.note` của dòng đó. Các nhãn, `area`, `channel`, `created_at` và
`overall_risk` được giữ nguyên nên dashboard và xu hướng không đổi. Mã tra cứu đã hết hạn hoặc đã
xoá trả 404 như mã không tồn tại.

### `correction_logs`
Nhật ký người duyệt sửa nhãn AI (human-in-the-loop). Mỗi lần ai đó sửa `topic`, `sentiment`
hoặc `severity`, ghi một dòng.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `id` | UUID, PK | |
| `feedback_id` | UUID | Phản hồi được sửa. |
| `corrected_by` | UUID | Người sửa. |
| `field` | TEXT | Trường được sửa: `topic`, `sentiment`, `severity`. |
| `old_value` | TEXT | Nhãn cũ (AI gán). |
| `new_value` | TEXT | Nhãn mới (người sửa). |
| `note` | TEXT | Ghi chú tuỳ chọn. |
| `created_at` | TIMESTAMPTZ | |

Ứng dụng: phục vụ audit và về sau dùng làm dữ liệu retrain model từ nhãn người đã sửa.

## 4. Cảnh báo và ticket

### `alerts`
Ticket sinh ra khi bộ phát hiện gom được một cụm phản hồi bất thường theo `(phòng, khu vực,
chủ đề)`.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `id` | UUID, PK | |
| `user_id` | UUID | Người liên quan tới phản hồi gốc. |
| `title` | TEXT | Tiêu đề ticket. |
| `description` | TEXT | Mô tả, có thể chứa các trường định tuyến ở dạng văn bản. |
| `severity` | TEXT | `P1`..`P5`. Mặc định `P2`. |
| `area` | TEXT | Khu vực. |
| `status` | TEXT | `open`, `in_progress`, hoặc trạng thái đã xử lý. Mặc định `open`. |
| `assigned_team` | TEXT | Phòng nhận ticket: `IT`, `CSKH`, `Vận hành`, `Tài chính & Thanh toán`, `Sản phẩm`, `Quản lý Rủi ro & Gian lận`. |
| `topic` | TEXT | Chủ đề định tuyến. |
| `priority` | TEXT | Ưu tiên xử lý. |
| `ticket_type` | TEXT | `incident` cho rủi ro vận hành, `opportunity` cho cụm tích cực của Sản phẩm. Mặc định `incident`. |
| `routing_source` | TEXT | Nguồn quyết định định tuyến (rule nào, bảng nào). |
| `sla_due_at` | TIMESTAMPTZ | Hạn SLA. |
| `task_id` | UUID | Trỏ tới `tasks` khi alert đã được gom vào một công việc. |
| `created_at` | TIMESTAMPTZ | |

Ứng dụng: là cầu nối giữa phản hồi rời rạc và công việc xử lý. Nhiều alert cùng `(phòng, khu
vực)` sẽ được gom vào một `task`.

## 5. Công việc và vòng đời xử lý

### `tasks`
Đầu việc để phòng ban nhận và xử lý. Sinh theo hai đường: tự động từ alert (`source=agent`)
hoặc do manager duyệt báo cáo rồi triển khai (`source=report`).

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `id` | UUID, PK | |
| `owner_id` | UUID | Nhân viên (staff) được giao. `NULL` khi chưa giao. Xoá user thì về `NULL`. |
| `title` | TEXT | Tên việc. |
| `summary` | TEXT | Mô tả ngắn. |
| `assigned_team` | TEXT | Phòng phụ trách: `IT`, `CSKH`, `Vận hành`, `Tài chính & Thanh toán`, `Sản phẩm`, `Quản lý Rủi ro & Gian lận`. |
| `topic` | TEXT | Chủ đề. |
| `area` | TEXT | Khu vực. |
| `priority` | TEXT | `P1`..`P5`. Mặc định `P2`. |
| `status` | TEXT | Vòng đời: `open` → `assigned` → `in_progress` → `pending_review` → `resolved` (xem mục 9). Mặc định `open`. |
| `source` | TEXT | Nguồn gốc: `agent` (máy gom alert) hoặc `report` (manager duyệt báo cáo). |
| `report_id` | UUID | Trỏ về `department_reports` khi task đến từ báo cáo, để nhân viên biết ngữ cảnh. |
| `due_at` | TIMESTAMPTZ | Hạn hoàn thành. |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

Ứng dụng: hiển thị trên Task Board. Quản lý/admin giao việc cho staff cùng phòng; staff nhận,
xử lý, rồi gửi báo cáo hoàn thành.

### `task_completion_reports`
Báo cáo hoàn thành do nhân viên gửi cho quản lý sau khi xử lý một task. Tách biệt với
`department_reports` (vốn là báo cáo phân tích của AI).

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `id` | UUID, PK | |
| `task_id` | UUID | Task được báo cáo. Xoá task thì xoá báo cáo (CASCADE). |
| `staff_id` | UUID | Nhân viên gửi. |
| `staff_email` | TEXT | Email nhân viên (lưu sẵn để hiển thị). |
| `team` | TEXT | Phòng của task. |
| `completion_level` | TEXT | Mức tự đánh giá: `completed`, `partial`, `blocked`. Mặc định `completed`. |
| `note` | TEXT | Mô tả đã xử lý gì, kết quả, vướng mắc. Bắt buộc. |
| `status` | TEXT | Trạng thái duyệt: `submitted`, `approved`, `rejected`. Mặc định `submitted`. |
| `reviewed_by` | UUID | Quản lý đã duyệt. |
| `reviewed_at` | TIMESTAMPTZ | Thời điểm duyệt. |
| `review_note` | TEXT | Ghi chú khi duyệt hoặc trả lại. |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

Ứng dụng: đóng vòng giao việc. Khi staff báo `completed`, task chuyển sang `pending_review`;
quản lý duyệt thì task thành `resolved`, trả lại thì task quay về `in_progress`.

### `task_events`
Nhật ký audit cho toàn bộ vòng đời của một task. Ghi ở tầng API nên luôn biết ai thao tác.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `id` | UUID, PK | |
| `task_id` | UUID | Task liên quan. Xoá task thì xoá event (CASCADE). |
| `actor_id` | UUID | Người thực hiện. |
| `actor_email` / `actor_role` | TEXT | Ảnh chụp danh tính lúc thao tác. |
| `team` | TEXT | Phòng của task. |
| `action` | TEXT | Mốc: `assigned`, `accepted`, `completion_submitted`, `completion_approved`, `completion_rejected`, `reopened`, `status_changed`. |
| `from_status` / `to_status` | TEXT | Trạng thái trước và sau. |
| `completion_report_id` | UUID | Trỏ tới báo cáo liên quan (khi mốc là gửi/duyệt báo cáo). |
| `note` | TEXT | Ghi chú. |
| `created_at` | TIMESTAMPTZ | |

Ứng dụng: trả lời câu hỏi "task này đã đi qua những bước nào, ai làm, lúc nào". Phục vụ trang
audit và đối soát.

## 6. Báo cáo phân tích

### `department_reports`
Báo cáo do nhóm agent phân tích sinh cho từng phòng, kèm danh sách hành động đề xuất để manager
duyệt và triển khai thành task.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `id` | UUID, PK | |
| `team` | TEXT | Phòng của báo cáo. |
| `report_date` | DATE | Ngày báo cáo. Mặc định hôm nay. |
| `content` | TEXT | Nội dung Markdown đầy đủ. |
| `approved` | BOOLEAN | Đã được manager duyệt chưa. Mặc định `false`. |
| `approved_by` | UUID | Manager duyệt. |
| `approved_at` | TIMESTAMPTZ | Thời điểm duyệt. |
| `suggested_tasks` | JSONB | Danh sách hành động đề xuất (mỗi phần tử có `action`, `priority`, `success_metric`, `due_at`...). Mặc định `[]`. |
| `root_cause_summary` | TEXT | Tóm tắt nguyên nhân gốc, tách riêng khỏi Markdown để query được. |
| `created_at` | TIMESTAMPTZ | |

Nhiều báo cáo trong ngày cho cùng một phòng là hợp lệ; ràng buộc duy nhất `(team, report_date)` đã bỏ từ migration `20260629000000`.

Ứng dụng: là nơi luồng HI-Loop Approval diễn ra. Manager sửa `suggested_tasks` rồi bấm duyệt;
hàm `approve_report_and_dispatch` biến từng hành động thành `tasks` với `source=report`.

## 7. Tri thức và Graph RAG

Hai bảng này phục vụ trợ lý hỏi đáp và định tuyến dựa trên tri thức (SOP, taxonomy). Dùng
pgvector với embedding Cohere `embed-multilingual-v3.0` (1024 chiều).

### `graph_nodes`
| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `id` | UUID, PK | |
| `node_type` | TEXT | Loại nút: `Topic`, `Department`, `SOPSection`, `Severity`... |
| `canonical_key` | TEXT | Khoá chuẩn hoá, ví dụ `topic:refund`, `dept:Safety`. |
| `name` | TEXT | Tên hiển thị. |
| `content` | TEXT | Nội dung văn bản để nhúng vector và làm ngữ cảnh. |
| `metadata` | JSONB | Thông tin kèm theo, ví dụ `{"department": "CSKH"}`. |
| `embedding` | vector(1024) | Vector ngữ nghĩa của `content`. Có index HNSW cosine. |
| `created_at` | TIMESTAMPTZ | |

Ràng buộc: `UNIQUE(node_type, canonical_key)`.

### `graph_edges`
| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `source_id` | UUID | Nút nguồn. |
| `target_id` | UUID | Nút đích. |
| `relationship_type` | TEXT | Quan hệ: `ROUTES_TO`, `HAS_SLA`, `REQUIRES_SOP`... |
| `weight` | FLOAT | Trọng số quan hệ. Mặc định 1.0. |
| `metadata` | JSONB | Thông tin kèm theo. |
| `created_at` | TIMESTAMPTZ | |

Khoá chính tổ hợp `(source_id, target_id, relationship_type)`.

Ứng dụng: tìm kiếm lai (vector + từ khoá) để lấy SOP và quan hệ định tuyến làm ngữ cảnh cho
LLM, qua hàm `match_graph_nodes`.

## 8. Quan sát hệ thống

### `agent_run_logs`
Mỗi lần một agent chạy hoặc gọi LLM, ghi một dòng để theo dõi chi phí và độ trễ.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `id` | UUID, PK | |
| `run_id` | TEXT | Mã một lần chạy pipeline. |
| `agent_name` | TEXT | Tên agent. |
| `input_hash` | TEXT | Hash đầu vào (gộp log trùng, cache). |
| `output_summary` | TEXT | Tóm tắt kết quả. |
| `status` | TEXT | `success`, `failed`, `fallback`. |
| `latency_ms` | INTEGER | Độ trễ mili giây. |
| `error_message` | TEXT | Thông báo lỗi nếu có. |
| `provider` / `model` | TEXT | Nhà cung cấp LLM và model. |
| `token_usage` | JSONB | Số token vào/ra. Mặc định `{}`. |
| `cost_estimate` | NUMERIC | Ước tính chi phí. Mặc định 0. |
| `created_at` | TIMESTAMPTZ | |

Ứng dụng: bảng theo dõi chi phí LLM và sức khoẻ pipeline. Chỉ admin/manager đọc.

### `chat_messages`
Lịch sử hội thoại giữa người dùng và trợ lý.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `id` | UUID, PK | |
| `user_id` | UUID | Chủ hội thoại. |
| `role` | TEXT | `user`, `assistant`, `system`. |
| `content` | TEXT | Nội dung tin nhắn. |
| `created_at` | TIMESTAMPTZ | |

## 9. Bảng từ vựng (enum) dùng chung

Các giá trị này lặp lại ở nhiều bảng; gom về một chỗ để tra nhanh.

| Khái niệm | Giá trị hợp lệ | Xuất hiện ở |
|---|---|---|
| Vai trò (role) | `admin`, `manager`, `staff`, `pending` | `profiles.role` |
| Nguồn phản hồi | `manual`, `chat`, `public`, tên dataset | `feedback.source` |
| Trạng thái phản hồi (suy ra, không lưu) | `received`, `under_review`, `reviewed` | `GET /api/public/feedback/{public_ref}` |
| Phòng ban | `IT`, `CSKH`, `Vận hành`, `Tài chính & Thanh toán`, `Sản phẩm`, `Quản lý Rủi ro & Gian lận` | `profiles.department`, `alerts.assigned_team`, `tasks.assigned_team`, `department_reports.team`, `task_completion_reports.team` |
| Chủ đề (topic) | `Safety`, `Driver Behavior`, `App Issue`, `Payment`, `Pricing`, `Delay`, `Other` | `feedback.topic`, `tasks.topic` |
| Cảm xúc | `positive`, `neutral`, `negative` | `feedback.sentiment` |
| Mức nghiêm trọng | `P1`..`P5` (P5 nặng nhất) | `feedback.severity`, `alerts.severity`, `*.priority` |
| Trạng thái task | `open`, `assigned`, `in_progress`, `pending_review`, `resolved` | `tasks.status` |
| Nguồn task | `agent`, `report` | `tasks.source` |
| Mức hoàn thành | `completed`, `partial`, `blocked` | `task_completion_reports.completion_level` |
| Trạng thái duyệt báo cáo hoàn thành | `submitted`, `approved`, `rejected` | `task_completion_reports.status` |
| Mốc audit task | `assigned`, `accepted`, `completion_submitted`, `completion_approved`, `completion_rejected`, `reopened`, `status_changed` | `task_events.action` |

Ghi chú lịch sử: trước đây hệ thống có thêm phòng `Safety` và `Pricing` (bỏ ở migration
`20260625000000`) và `Marketing` (bỏ ở migration `20260630000000`, reassign user + dữ liệu
lịch sử về `Sản phẩm`). Các topic vẫn được định tuyến: topic `Safety` về `Vận hành`, topic
`Pricing` về `Quản lý Rủi ro & Gian lận`. `Safety` và `Pricing` vẫn tồn tại như topic định
tuyến, nhưng không gán user vào đó nữa.

## 10. Hàm và trigger trong database

| Tên | Loại | Tác dụng |
|---|---|---|
| `handle_new_user()` | Trigger trên `auth.users` | Tạo profile khi có user mới. Profile đầu tiên thành `admin`, còn lại mặc định `pending`. `POST /api/admin/users` gán role thật ngay sau đó. |
| `current_user_role()` | SQL, SECURITY DEFINER | Đọc role của user hiện tại mà không gây đệ quy RLS. |
| `password_is_current()` | SQL | `true` trừ khi JWT hiện tại có `app_metadata.must_change_password = true` (tài khoản còn mật khẩu tạm). Đọc từ `auth.jwt()`, nên sau khi đổi mật khẩu client phải refresh session để có JWT mới. |
| `is_admin()` | SQL | `true` nếu user hiện tại là admin **và** `password_is_current()`. Dùng trong policy. |
| `is_ops_staff()` | SQL | `true` nếu role thuộc `admin/manager/staff` (không gồm `pending`) **và** `password_is_current()`. Dùng trong policy. |
| `match_graph_nodes(query_embedding, match_count, department_filter)` | plpgsql | Tìm các `SOPSection` gần nhất theo cosine similarity, lọc theo phòng. Trả về id, tiêu đề, nội dung, phòng, độ tương đồng. |
| `approve_report_and_dispatch(p_report_id, p_tasks, p_approver)` | plpgsql | Duyệt báo cáo và sinh task trong một thao tác nguyên tử: cập nhật `department_reports` rồi INSERT từng phần tử `suggested_tasks` thành `tasks` (`source=report`). Báo lỗi nếu báo cáo đã duyệt. |

## 11. Tóm tắt RLS theo bảng

Nhắc lại: backend dùng service role nên bỏ qua RLS; bảng dưới đây là quyền khi gọi Supabase
trực tiếp từ client.

"Ops staff" và "admin" ở đây là `is_ops_staff()` / `is_admin()`, cả hai đều đòi
`password_is_current()`. Tài khoản còn mật khẩu tạm vì vậy không có quyền ops hay admin qua
PostgREST và realtime cho tới khi đổi mật khẩu và refresh session.

| Bảng | Đọc | Ghi |
|---|---|---|
| `profiles` | Chính chủ hoặc admin | Không ai tự insert/delete (đã thu hồi `INSERT`, `DELETE`, `TRUNCATE`); UPDATE chỉ cột `full_name`. Role và phòng đổi qua backend |
| `feedback` | Ops staff xem hết; tài khoản khác chỉ dòng của mình; dòng ẩn danh chỉ ops | Chỉ ops staff insert, đúng `user_id` của mình; update/delete chỉ qua backend (service role) |
| `alerts` | Ops staff xem hết; tài khoản khác chỉ dòng của mình | Chỉ qua backend (service role) |
| `tasks` | Ops staff | INSERT chỉ service role; UPDATE ops; DELETE admin |
| `department_reports` | Admin và manager | Chỉ service role |
| `task_completion_reports` | Authenticated (gate phòng ở API) | Service role; cho phép authenticated insert dự phòng |
| `task_events` | Authenticated (gate phòng ở API) | Service role; cho phép authenticated insert dự phòng |
| `correction_logs` | Ops staff | Ops staff, đúng danh tính người sửa |
| `agent_run_logs` | Admin và manager | Chỉ service role |
| `audit_logs` | Chỉ admin | Chỉ service role |
| `graph_nodes`, `graph_edges` | Chỉ ops staff ("Graph nodes select ops" / "Graph edges select ops") | Chỉ service role |
| `chat_messages` | Chính chủ | Chính chủ |

## 12. Bảng nào bật Realtime

Frontend subscribe được thay đổi tức thời ở: `feedback`, `tasks`, `department_reports`,
`task_completion_reports`, `task_events`. Nhờ vậy dashboard, Task Board và hàng đợi duyệt cập
nhật ngay khi backend ghi dữ liệu.

## 13. Thứ tự migration

Schema được dựng tăng dần qua các file trong `supabase/migrations/` (đặt tên theo dấu thời
gian, chạy theo thứ tự). Xem `supabase/README.md` để biết cách áp dụng và một lưu ý về drift
giữa lịch sử migration và bảng thật trên remote.
</content>
