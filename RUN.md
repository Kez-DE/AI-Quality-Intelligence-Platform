# RUN — AI Quality Intelligence Platform (chạy & test local)

> Yêu cầu: đã có `pipeline/.venv` (Python deps) và `app/node_modules` (frontend deps).
> Mọi key sống trong `.env` ở repo root (KHÔNG commit).

## 1. Chạy BACKEND (FastAPI, cổng 8000)

```bash
cd ~/C2-App-116/pipeline
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Đợi tới khi thấy `Application startup complete.` Kiểm tra:

```bash
curl -s http://127.0.0.1:8000/health
# {"status":"ok",...}
curl -s http://127.0.0.1:8000/api/agent/status
# provider/model LLM đang dùng + key nào configured
```

## 2. Chạy FRONTEND (React/TanStack, cổng 5174) — MỞ TERMINAL THỨ 2

```bash
cd ~/C2-App-116/app
set -a && . ../.env && set +a          
node node_modules/vite/bin/vite.js dev --port 5174 --host 127.0.0.1
```

Mở trình duyệt: **http://localhost:5174**

> Lưu ý: bước `set -a && . ../.env && set +a` là bắt buộc. Chat AI dùng biến
> `SUPABASE_URL` + `BACKEND_API_URL` (non-VITE); chạy `vite` trần sẽ thiếu chúng → chat lỗi.

## 3. Đăng nhập

- **Admin:** `demo.20260606180215@example.com` / `Admin@12345`
  (toàn quyền: ingest, streaming, trigger ticket, quản lý user)
- Tài khoản `khangduc*@gmail.com` = role **staff** (xem dữ liệu, không vận hành được).

## 4. Test nhanh từng tính năng

### a) Lấy token admin (dùng cho các lệnh curl bên dưới)
```bash
cd ~/C2-App-116/pipeline
TOKEN=$(.venv/bin/python - <<'PY'
import os; from dotenv import load_dotenv; load_dotenv("../.env")
from supabase import create_client
c=create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_PUBLISHABLE_KEY"])
r=c.auth.sign_in_with_password({"email":"demo.20260606180215@example.com","password":"Admin@12345"})
print(r.session.access_token)
PY
)
echo "${TOKEN:0:20}..."
```

### b) Streaming 50 review/giây (luồng chính)
```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
 "http://127.0.0.1:8000/api/live-stream/start?batch_size=50&interval_seconds=1&loop=false&reset=true&auto_ticket=true&ticket_every_batches=10"

# theo dõi tiến độ (chạy lại nhiều lần để thấy số tăng):
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/live-stream/status

# dừng giữa chừng nếu cần:
curl -s -X POST -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/live-stream/stop
```
Trong lúc stream chạy, mở UI trang **Dashboard / Phản hồi / Ticket Triage** — số liệu tự cập nhật (realtime).

### c) Nút "bắn 1 lô" demo an toàn (không cần streaming)
```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
 "http://127.0.0.1:8000/api/ingest-real-dataset?limit=150&batch_size=150"
```

### d) Trigger ticket thủ công (gọi LLM thật, ~10–25s)
```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
 "http://127.0.0.1:8000/api/trigger-spike-detect?max_feedback=1000&max_spikes=3"
```

### e) Multi-agent — insight theo phòng ban
```bash
# 1 phòng ban (kèm phân tích root cause của LLM):
curl -s -H "Authorization: Bearer $TOKEN" \
 "http://127.0.0.1:8000/api/insights/departments/Safety?with_analysis=true"

# toàn bộ 6 phòng ban (chạy ~2 phút vì gọi LLM nhiều lần):
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
 "http://127.0.0.1:8000/api/agent/run?hours=24"
```

### f) Chat AI (cách nhanh nhất: test thẳng trên UI trang "AI Chat")
```bash
# hoặc test backend trực tiếp:
curl -s -X POST -H "Content-Type: application/json" \
 -d '{"messages":[{"role":"user","content":"Khu vực nào tiêu cực nhất?"}]}' \
 http://127.0.0.1:8000/api/agent/chat
```

## 5. Reset dữ liệu demo (nếu muốn chạy lại từ đầu)
Streaming với `reset=true` (mục 4b) đã tự xoá dữ liệu cũ trước khi bơm lô mới.

## Dừng hệ thống
Ctrl+C ở cả 2 terminal, hoặc:
```bash
lsof -ti:8000 | xargs kill -9 ; lsof -ti:5174 | xargs kill -9
```
