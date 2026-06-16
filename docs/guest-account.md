# Tài khoản khách (Guest Account) — Cơ chế & giới hạn

> Tài khoản khách là vai trò có quyền thấp nhất trong hệ thống. Mục tiêu: cho phép người ngoài xem dashboard tổng quan và gửi feedback mà không truy cập được dữ liệu nội bộ.

---

## 1. Phân quyền tổng quan

| Tính năng | Admin | Manager | Staff | Guest |
|-----------|:-----:|:-------:|:-----:|:-----:|
| Dashboard (xem) | ✅ | ✅ | ✅ | ✅ |
| Gửi feedback | ✅ | ✅ | ✅ | ✅ |
| Xem danh sách feedback raw | ✅ | ✅ | ✅ | ❌ |
| Sửa nhãn AI (HITL) | ✅ | ✅ | ✅ | ❌ |
| Alerts / Ticket Triage | ✅ | ✅ | ✅ | ❌ |
| Phân tích phòng ban | ✅ | ✅ | ✅ | ❌ |
| AI Chat | ✅ | ✅ | ✅ | ❌ |
| Agent Logs | ✅ | ✅ | ✅ | ❌ |
| Quản lý người dùng | ✅ | ❌ | ❌ | ❌ |
| Trigger demo/stream | ✅ | ❌ | ❌ | ❌ |
| Chạy agent pipeline | ✅ | ❌ | ❌ | ❌ |

---

## 2. Cơ chế hoạt động

### 2.1 Frontend (React/TanStack Router)

**AppShell** (`app/src/components/AppShell.tsx`):
- Sidebar ẩn các menu không dành cho guest
- Guest chỉ thấy: Dashboard, Gửi phản hồi
- Không hiển thị: Alerts, Feedback list, Insights, Chat, Admin

**Route guard** (`app/src/routes/_authenticated/route.tsx`):
- Mọi route authenticated đều check role
- Guest truy cập route không được phép → redirect về `/dashboard`

**Trang upload riêng** (`app/src/routes/_authenticated/feedback-upload.tsx`):
- Guest dùng trang này để gửi feedback
- Chỉ nhập: nội dung + kênh + khu vực
- Topic/sentiment/severity do AI tự phân tích

### 2.2 Backend (FastAPI)

**Auth guard** (`pipeline/auth_guard.py`):
```python
VALID_ROLES = {"admin", "manager", "staff", "guest"}
OPS_ROLES = {"admin", "manager", "staff"}  # guest KHÔNG nằm trong đây
```

**Endpoint chặn guest:**
- `require_ops_staff` → 403 nếu role = guest
- `require_admin` → 403 nếu role ≠ admin

**Endpoint guest ĐƯỢC gọi:**
- `GET /api/me` — xem thông tin bản thân
- `GET /api/feedback/recent` — chỉ data aggregate/dashboard
- `POST /api/feedback/submit` — gửi feedback mới
- `GET /api/live-stream/status` — xem trạng thái stream
- `GET /health` — health check

**Endpoint guest BỊ CHẶN:**
- `POST /api/live-stream/start|stop` — trigger stream
- `POST /api/ingest-real-dataset` — nạp data
- `POST /api/trigger-spike-detect` — spike detect
- `POST /api/agent/run` — chạy agent pipeline
- `POST /api/agent/chat` — chat AI
- `PATCH /api/feedback/*/label` — sửa nhãn
- `PATCH /api/feedback/*/review` — duyệt feedback
- `GET /api/insights/departments` — insight phòng ban
- `PATCH /api/alerts/*/status` — đổi trạng thái alert

### 2.3 Supabase RLS

**Policy cho guest:**
```sql
-- Guest chỉ insert feedback của chính mình
CREATE POLICY "guest_insert_own_feedback" ON feedback
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Guest chỉ đọc feedback aggregate (qua view hoặc function)
-- KHÔNG cho đọc trực tiếp bảng feedback raw
CREATE POLICY "ops_read_feedback" ON feedback
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND profiles.role IN ('admin', 'manager', 'staff')
    )
  );
```

---

## 3. Tạo tài khoản khách

### Cách 1: Qua Admin UI

1. Login admin → vào trang "Quản lý người dùng"
2. Tạo user mới → chọn role = guest
3. Gửi thông tin đăng nhập cho khách

### Cách 2: Tự đăng ký

1. User đăng ký qua trang `/auth`
2. Mặc định tài khoản mới = staff (hoặc guest tùy config)
3. Admin vào Admin page đổi role nếu cần

### Cách 3: Qua Supabase Dashboard

1. Vào Supabase Dashboard → Authentication → Users → Invite user
2. Sau khi user xác nhận email, vào bảng `profiles`
3. Set `role = 'guest'` cho user đó

---

## 4. Luồng guest sử dụng hệ thống

```
Guest login
    │
    ▼
┌───────────────┐
│  Dashboard    │ ← Xem KPI, trend, severity, heatmap
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  Gửi phản hồi│ ← Nhập text + kênh + khu vực
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  AI phân tích │ ← Tự gán topic/sentiment/severity
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  Done         │ ← Guest thấy thông báo thành công
└───────────────┘
        
        ❌ Guest KHÔNG thể:
        - Xem feedback raw của người khác
        - Vào trang Alerts/Tickets
        - Chat với AI
        - Xem phân tích phòng ban
        - Sửa nhãn AI
        - Trigger demo/stream
```

---

## 5. Bảo mật

- **Không leak PII:** Guest không đọc được bảng feedback raw
- **Không leak internal:** Guest không thấy agent logs, prompt, config
- **URL guard:** Truy cập trực tiếp bằng URL → redirect về dashboard
- **API guard:** Backend validate role ở mọi endpoint nhạy cảm
- **RLS guard:** Supabase chặn ở tầng database nếu bypass frontend
- **Rate limit:** Nên thêm rate limit cho guest upload (tránh spam)

---

## 6. Test tài khoản khách

```bash
# 1. Tạo guest account trong Supabase Auth
# 2. Login và lấy token
TOKEN_GUEST=$(.venv/bin/python - <<'PY'
import os; from dotenv import load_dotenv; load_dotenv("../.env")
from supabase import create_client
c=create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_PUBLISHABLE_KEY"])
r=c.auth.sign_in_with_password({"email":"guest@example.com","password":"Guest@12345"})
print(r.session.access_token)
PY
)

# 3. Test gửi feedback (PHẢI được)
curl -s -X POST -H "Authorization: Bearer $TOKEN_GUEST" \
  -H "Content-Type: application/json" \
  -d '{"text":"Xe sạch, tài xế lịch sự","channel":"app","area":"HN-Cau-Giay"}' \
  http://127.0.0.1:8000/api/feedback/submit
# → 200 OK

# 4. Test trigger spike (PHẢI bị chặn)
curl -s -X POST -H "Authorization: Bearer $TOKEN_GUEST" \
  http://127.0.0.1:8000/api/trigger-spike-detect
# → 403 Forbidden

# 5. Test chạy agent (PHẢI bị chặn)
curl -s -X POST -H "Authorization: Bearer $TOKEN_GUEST" \
  http://127.0.0.1:8000/api/agent/run
# → 403 Forbidden

# 6. Test chat AI (PHẢI bị chặn)
curl -s -X POST -H "Authorization: Bearer $TOKEN_GUEST" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"test"}]}' \
  http://127.0.0.1:8000/api/agent/chat
# → 403 Forbidden
```
