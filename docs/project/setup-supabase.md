# Hướng dẫn thiết lập Supabase

> Dự án sử dụng **Supabase Cloud** (remote project) làm database chính.
> Supabase Local (Docker) là tuỳ chọn cho dev offline.

> **Cập nhật 2026-06-27:** rà soát khớp với migrations & schema 6 phòng hiện tại; nội dung kỹ thuật giữ nguyên.

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

### 8.1 Email Auth (mặc định)

Vào **Authentication → Providers → Email**:

- ✅ Enable Email
- ✅ Enable Email Confirmations: **TẮT** (cho dev/demo nhanh)
- Hoặc bật nếu muốn verify email thật

### 8.2 Site URL & Redirect

Vào **Authentication → URL Configuration**:

- **Site URL:** `http://localhost:5174` (dev) hoặc URL deploy
- **Redirect URLs:** thêm `http://localhost:5174/`**

### 8.3 Tạo tài khoản admin đầu tiên

Cách 1 — Qua UI frontend:

1. Mở `http://localhost:5174/auth`
2. Đăng ký email/password
3. User đầu tiên tự động được gán role `admin`

Cách 2 — Qua Supabase Dashboard:

1. **Authentication → Users → Add user**
2. Nhập email + password
3. Vào **Table Editor → profiles** → sửa cột `role` = `admin`

## 9. Row Level Security (RLS)

Project dùng `SERVICE_ROLE_KEY` ở backend (bypass RLS), nên gate quyền ở tầng API (`auth_guard.py`).

Frontend đọc trực tiếp qua anon key + RLS:

- Guest chỉ đọc được dashboard view
- Staff/admin đọc được feedback, alerts

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
| `profiles`        | User profile kèm role (admin/manager/staff/guest)                                  |
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

