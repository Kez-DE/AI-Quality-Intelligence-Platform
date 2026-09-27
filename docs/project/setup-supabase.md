# Hướng dẫn thiết lập Supabase

> Dự án sử dụng **Supabase Cloud** (remote project) làm database chính.
> Supabase Local (Docker) là tuỳ chọn cho dev offline.

> **Cập nhật 2026-06-27:** rà soát khớp với migrations & schema 6 phòng hiện tại; nội dung kỹ thuật giữ nguyên.

> **Cập nhật 2026-09-27 (US-077 / decision 0017):** thêm bước tay tắt tự đăng ký và OAuth (8.1); admin đầu tiên tạo trong Dashboard vì Staff web không còn form đăng ký (8.4); role `guest` đổi thành `pending`.

---

## 1. Tạo project trên Supabase Cloud

1. Truy cập [supabase.com](https://supabase.com) → Sign in / Sign up.
2. Nhấn **New Project**.
3. Điền:
  - **Name:** `ai-quality-intelligence-platform` (hoặc tuỳ chọn)
  - **Database Password:** ghi nhớ (cần cho CLI link)
  - **Region:** Singapore hoặc gần nhất
4. Chờ project khởi tạo (~2 phút).

## 2. Lấy thông tin kết nối

Vào **Settings → API** của project vừa tạo, copy:


| Biến                        | Giá trị lấy từ                                                   |
| --------------------------- | ---------------------------------------------------------------- |
| `SUPABASE_URL`              | Project URL ([https://xxx.supabase.co](https://xxx.supabase.co)) |
| `SUPABASE_PUBLISHABLE_KEY`  | anon / public key                                                |
| `SUPABASE_SERVICE_ROLE_KEY` | service_role key (⚠️ bí mật, chỉ dùng server)                    |
| `SUPABASE_PROJECT_ID`       | phần `xxx` trong URL                                             |


## 3. Điền vào `.env`

```bash
cp .env.example .env
```

Mở `.env` và điền:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_PUBLISHABLE_KEY=eyJhbGciOi...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...

VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=eyJhbGciOi...
```

> ⚠️ `SUPABASE_SERVICE_ROLE_KEY` KHÔNG BAO GIỜ commit lên Git hoặc để trong frontend code.

## 4. Cài Supabase CLI

### macOS

```bash
brew install supabase/tap/supabase
```

### Windows

```powershell
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase
```

### Hoặc dùng npm (cả 2 OS)

```bash
npm install -g supabase
```

Kiểm tra:

```bash
supabase --version
```

## 5. Liên kết project

```bash
cd AI-Quality-Intelligence-Platform/supabase

# Đăng nhập (mở browser xác thực)
supabase login

# Link project (nhập database password khi được hỏi)
supabase link --project-ref <project-id>
```

`<project-id>` là phần đầu URL: nếu URL là `https://fktdsfacyuejxddzzfgtau.supabase.co` thì project-ref = `fktdsfacyuejxddzzfgtau`.

## 6. Áp migration (tạo bảng)

```bash
supabase db push
```

Lệnh này sẽ chạy tất cả file SQL trong `supabase/migrations/` lên remote project:

- `20260606100321_*.sql` — Bảng feedback, alerts, profiles, chat_messages
- `20260606100342_*.sql` — Index và constraints
- `20260606183000_enable_feedback_realtime.sql` — Bật realtime cho feedback
- `20260612120000_rbac_roles.sql` — Thêm cột role vào profiles
- `20260612140000_correction_logs.sql` — Bảng audit sửa nhãn
- `20260612160000_feedback_review_flags.sql` — Cột needs_review, reviewed

## 7. Bật Realtime

Vào Supabase Dashboard → **Database → Replication**:

- Bật Realtime cho bảng `feedback` và `alerts`.

Hoặc migration đã tự bật (file `enable_feedback_realtime.sql`).

## 8. Cấu hình Authentication

### 8.1 Tắt tự đăng ký và đăng nhập Google/Facebook (thao tác tay, bắt buộc)

Từ US-077 (decision 0017), chỉ admin tạo tài khoản và Staff web đã bỏ form đăng ký cùng nút Google/Facebook. Nhưng Supabase Auth vẫn nhận đăng ký trực tiếp qua API và qua OAuth cho tới khi chủ dự án tắt trong Dashboard. Không có code nào trong repo làm hoặc kiểm tra được việc này, nên đây là bước tay, làm trên **đúng project production**.

Nhãn có thể khác nhau giữa các phiên bản Dashboard:

1. Vào **Authentication → Sign In / Providers** (bản cũ: **Authentication → Providers**).
2. Ở mục **User Signups**, tắt **Allow new users to sign up**. Theo tài liệu Supabase, khi tắt thì chỉ user đã tồn tại mới đăng nhập được.
3. Trong danh sách provider, tắt **Google** và **Facebook**.
4. **Giữ provider Email bật.** Đây là đường đăng nhập bằng mật khẩu duy nhất còn lại; tắt provider Email sẽ chặn luôn cả đăng nhập.
5. Kiểm tra ngay sau khi tắt:
   - Admin tạo một tài khoản thử bằng form "Tạo tài khoản" trên Staff web (`POST /api/admin/users`), đăng nhập được và bị bắt đổi mật khẩu, rồi xoá tài khoản thử. Tài liệu Supabase không nói rõ việc tạo user bằng admin API (service role) có còn chạy khi tắt đăng ký hay không, nên phải kiểm tra thực tế.
   - Đăng ký trực tiếp bằng publishable key phải bị từ chối và không tạo user mới:

     ```bash
     curl -s -X POST "$SUPABASE_URL/auth/v1/signup" \
       -H "apikey: $SUPABASE_PUBLISHABLE_KEY" -H "Content-Type: application/json" \
       -d '{"email":"signup-check@example.com","password":"Chk#12345678"}'
     ```

     Nếu lệnh này tạo được user thì bước 2 chưa có hiệu lực. Tài khoản đó vào hệ thống với role `pending` (không có quyền), nhưng vẫn nên xoá trong **Authentication → Users**.

Chưa tắt thì rủi ro còn lại là tài khoản rác: mọi tài khoản tự đăng ký đều vào với role `pending`, backend trả 403 ở mọi endpoint trừ `GET /api/me`, `POST /api/me/password` và `/health`.

Stack local: tương đương là `enable_signup = false` trong mục `[auth]` của `supabase/config.toml` (hiện file chưa đặt giá trị này).

### 8.2 Email Auth

Vào **Authentication → Providers → Email**:

- ✅ Enable Email (giữ bật, xem 8.1)
- ✅ Enable Email Confirmations: **TẮT** (cho dev/demo nhanh)
- Hoặc bật nếu muốn verify email thật. Tài khoản admin tạo qua `POST /api/admin/users` đã được xác nhận email sẵn.

### 8.3 Site URL & Redirect

Vào **Authentication → URL Configuration**:

- **Site URL:** `http://localhost:5174` (dev) hoặc URL deploy
- **Redirect URLs:** thêm `http://localhost:5174/`**

### 8.4 Tạo tài khoản admin đầu tiên

Staff web không còn form đăng ký, nên admin đầu tiên được tạo trong Dashboard:

Cách 1 — Database mới (chưa có profile nào):

1. **Authentication → Users → Add user**, nhập email + password, chọn tự xác nhận email.
2. Trigger `handle_new_user` gán role `admin` cho profile đầu tiên của hệ thống.
3. Đăng nhập Staff web bằng tài khoản này; các tài khoản sau tạo bằng form "Tạo tài khoản" trong trang Quản lý người dùng.

Cách 2 — Database đã có profile:

1. **Authentication → Users → Add user**
2. Nhập email + password (tài khoản vào với role `pending`)
3. Vào **Table Editor → profiles** → sửa cột `role` = `admin`

## 9. Row Level Security (RLS)

Project dùng `SERVICE_ROLE_KEY` ở backend (bypass RLS), nên gate quyền ở tầng API (`auth_guard.py`).

Frontend đọc trực tiếp qua anon key + RLS:

- Tài khoản không thuộc ops (kể cả `pending`) chỉ đọc được dòng feedback/alert của chính mình; phản hồi ẩn danh (`user_id` NULL) chỉ ops đọc được
- Staff/admin đọc được feedback, alerts
- Chỉ ops staff được insert vào `feedback`, và phải đúng `user_id` của mình
- Knowledge base nội bộ (`graph_nodes`, `graph_edges`) chỉ ops staff đọc được
- `is_ops_staff()` và `is_admin()` đòi `password_is_current()`: tài khoản còn mật khẩu tạm (`app_metadata.must_change_password`) không có quyền ops/admin qua PostgREST và realtime cho tới khi đổi mật khẩu và refresh session

Bảng RLS đầy đủ theo từng bảng: [data-model.md](data-model.md) mục 11.

Kiểm tra RLS đã bật:

```sql
-- Trong SQL Editor của Supabase Dashboard
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';
```

## 10. Schema tóm tắt


| Bảng              | Mô tả                                                                              |
| ----------------- | ---------------------------------------------------------------------------------- |
| `feedback`        | Phản hồi đã phân loại (topic, sentiment, severity, confidence, area, needs_review) |
| `alerts`          | Ticket/Alert do spike detector + LLM sinh ra                                       |
| `profiles`        | User profile kèm role (admin/manager/staff/pending)                                |
| `correction_logs` | Audit trail khi staff sửa nhãn AI                                                  |
| `chat_messages`   | Lịch sử chat AI                                                                    |


## 11. Troubleshooting

### Lỗi "relation does not exist"

→ Chưa chạy migration. Chạy `supabase db push`.

### Lỗi "new row violates RLS policy"

→ Backend đang dùng anon key thay vì service_role key. Kiểm tra `.env`:

```env
SUPABASE_SERVICE_ROLE_KEY=eyJ...  # PHẢI là service_role, không phải anon
```

### Lỗi "JWT expired" khi gọi API

→ Token hết hạn. Lấy token mới (xem `pipeline/README.md` mục "Lấy token admin").

### Lỗi 403 khi `supabase start` (Việt Nam)

→ `jsr.io` chặn IP VN. File `config.toml` đã tắt `edge_runtime`:

```toml
[edge_runtime]
enabled = false
```

Nếu cần Edge Functions, bật VPN (1.1.1.1/Warp) rồi đổi lại `enabled = true`.

### Realtime không nhận event

1. Kiểm tra bảng đã bật Replication (Dashboard → Database → Replication)
2. Kiểm tra frontend dùng đúng `VITE_SUPABASE_URL` + `VITE_SUPABASE_PUBLISHABLE_KEY`

## 12. Supabase Local (tuỳ chọn — cần Docker)

Nếu muốn dev offline:

```bash
# Cần Docker Desktop đang chạy
cd AI-Quality-Intelligence-Platform/supabase
supabase start
```

Copy output (API URL, anon key, service_role key) vào `.env`. Khi dùng local:

```env
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_PUBLISHABLE_KEY=<anon key từ output>
SUPABASE_SERVICE_ROLE_KEY=<service_role key từ output>
```

Dừng:

```bash
supabase stop
```

Reset (xoá hết data):

```bash
supabase db reset
```

