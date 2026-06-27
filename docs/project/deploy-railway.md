# Deploy lên Railway

> **Cập nhật 2026-06-27:** đồng bộ env-var (.env.example) và luồng deploy. Push lên `main` là đường deploy chính (GitHub Actions tự kích hoạt).

Hệ thống chạy trên Railway dưới dạng **6 service riêng**, build từ Docker, deploy tự động qua GitHub Actions khi push lên `main`. Supabase là dịch vụ ngoài (cloud), không nằm trong Railway.

## Kiến trúc 6 service

| Railway service | Build từ | Chạy gì | Public domain |
|-----------------|----------|---------|:-------------:|
| `frontend` | `app/Dockerfile` | TanStack Start node-server (port 3000) | ✅ |
| `backend` | `pipeline/Dockerfile` | FastAPI uvicorn `main:app` (port 8000) | ✅ |
| `backend-worker` | `pipeline/Dockerfile.workers` | `worker_ticket.py` — vòng đời ticket | ❌ |
| `ingest-worker` | `pipeline/Dockerfile.workers` | `worker_ingest.py` — live stream nạp dataset | ❌ |
| `ml-worker` | `pipeline/Dockerfile.workers` | `worker_ml.py` — chấm risk bằng LLM | ❌ |
| `agent-worker` | `pipeline/Dockerfile.workers` | `worker_agent.py` — multi-agent pipeline | ❌ |

`backend` và 4 worker dùng **chung source** (`pipeline/` + `data/`). Bốn worker build từ cùng một Dockerfile (`Dockerfile.workers`); mỗi service chọn entrypoint bằng biến `WORKER_MODULE` (ví dụ `worker_ticket`, `worker_agent`).

```
Railway Project
├── frontend        app/Dockerfile           → port 3000, public
├── backend         pipeline/Dockerfile      → port 8000, public
├── backend-worker  Dockerfile.workers       → WORKER_MODULE=worker_ticket
├── ingest-worker   Dockerfile.workers       → WORKER_MODULE=worker_ingest
├── ml-worker       Dockerfile.workers       → WORKER_MODULE=worker_ml
└── agent-worker    Dockerfile.workers       → WORKER_MODULE=worker_agent

Supabase (external cloud) ← tất cả service kết nối qua env var
```

## Vì sao tách worker khỏi web API

Các job định kỳ (ticket workflow, live stream, ML scoring, multi-agent) chạy trong worker riêng, không nhét vào `backend`. Lý do: nếu cả web API và worker cùng giữ scheduler thì job sẽ chạy trùng. Web API chỉ giữ scheduler cho job thủ công on-demand (ví dụ `POST /api/live-stream/start`). Tách ra còn cho phép scale và tắt từng phần độc lập, ví dụ tắt `agent-worker` để tiết kiệm LLM cost mà không ảnh hưởng API.

---

## Deploy tự động qua GitHub Actions

Đây là cơ chế deploy chính. Repo dùng `.github/workflows/railway.yml` chạy trên **self-hosted runner**, gọi `railway up --ci` cho từng service. Railway **không** tự watch GitHub repo; mọi deploy đi qua workflow này.

Workflow trigger khi push `main` và có thay đổi trong các path: `app/**`, `pipeline/**`, `data/**`, `.env.example`, `railway.json`, hoặc chính file workflow.

Quy tắc detect service cần deploy (job `changes`):

- Đổi `app/**` → deploy `frontend`.
- Đổi `pipeline/**` hoặc `data/**` → deploy `backend` **và cả 4 worker** (vì share chung source).
- Đổi `railway.json`, `.env.example`, hoặc workflow → tính là đổi cả frontend lẫn backend.

Vì chỉ sửa file `.md` (không nằm trong watch path) sẽ **không** trigger deploy service nào.

### Deploy thủ công

Vào tab **Actions** trên GitHub → workflow **Deploy to Railway** → **Run workflow**, chọn `target`: `all`, `frontend`, `backend`, `backend-worker`, `ingest-worker`, `ml-worker`, hoặc `agent-worker`.

### Secrets và variables cần có

Vào GitHub repo → **Settings** → **Secrets and variables** → **Actions**:

| Tên | Loại | Giá trị |
|-----|------|---------|
| `RAILWAY_TOKEN` | Secret | Project token lấy từ Railway → Settings → Tokens |
| `RAILWAY_PROJECT_ID` | Secret | Project ID (xem qua `railway status` hoặc URL project) |
| `RAILWAY_ENVIRONMENT` | Variable | Mặc định `production` nếu không set |

`railway.json` ở gốc repo cấu hình builder Docker + restart policy (`ON_FAILURE`, tối đa 10 lần).

---

## Biến môi trường runtime

GitHub Actions chỉ deploy code. Các biến runtime phải set trong **Railway Variables** của từng service.

### backend + 4 worker (chung nhóm biến Supabase + LLM)

```env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
LLM_PROVIDER=auto
OPENROUTER_API_KEY=sk-or-...
COHERE_API_KEY=...             # Bắt buộc cho RAG hybrid embedding
```

Backend đọc Supabase theo chuỗi fallback: `SUPABASE_SERVICE_ROLE_KEY` > `SUPABASE_KEY` > `SUPABASE_PUBLISHABLE_KEY`. Dùng service role key để bypass RLS (RBAC kiểm ở tầng API, xem [rbac-departments.md](rbac-departments.md)).

Biến riêng theo worker:

```env
# backend-worker (worker_ticket)
WORKER_TICKET_WORKFLOW_INTERVAL_SECONDS=15

# ingest-worker (worker_ingest)
LIVE_STREAM_ENABLED=true
LIVE_STREAM_BATCH_SIZE=150
LIVE_STREAM_INTERVAL_SECONDS=10

# ml-worker (worker_ml)
WORKER_ML_INTERVAL_SECONDS=60
WORKER_ML_BATCH_SIZE=50

# agent-worker (worker_agent) — tắt để tiết kiệm LLM cost
WORKER_AGENT_ENABLED=true
WORKER_AGENT_INTERVAL_SECONDS=300
WORKER_AGENT_HOURS=24
```

### frontend

Biến `VITE_*` được nhúng vào client bundle **lúc build**, nên phải set trước khi deploy:

```env
PORT=3000
NITRO_PRESET=node-server
BACKEND_API_URL=http://backend.railway.internal:8000
VITE_BACKEND_API_URL=https://backend-xxx.up.railway.app
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
```

`VITE_BACKEND_API_URL` là URL public (browser gọi trực tiếp). `BACKEND_API_URL` dùng internal networking cho server-side call.

---

## Test local với Docker Compose

`docker-compose.yml` chỉ để test local (Railway deploy từng service từ Dockerfile riêng, không từ compose). Compose chỉ dựng `backend` + `frontend`:

```bash
docker compose up --build
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000/health
docker compose down
```

---

## Troubleshooting

**Backend healthy nhưng RAG trả rỗng:** kiểm tra `data/` đã được `COPY` vào image (`pipeline/Dockerfile` dòng `COPY data/ /app/data/`). KB retriever resolve path `/app/data/knowledge_base` và `/app/data/public_kb` trong container.

**Backend crash "No module named sklearn":** `requirements.txt` cần `scikit-learn`; model `.joblib` phải khớp version.

**Frontend không gọi được backend:** `VITE_BACKEND_API_URL` phải là URL public có `https`, backend phải có domain public, và CORS trong `main.py` allow origin frontend.

**Worker chạy sai entrypoint:** kiểm tra biến `WORKER_MODULE` của service đó trên Railway (ví dụ `agent-worker` phải set `WORKER_MODULE=worker_agent`).

---

## Chi phí

Railway Hobby ($5/tháng) là gói thuê bao kèm $5 tín dụng tài nguyên, tính theo mức dùng thật (RAM, CPU, disk theo giây). Đây là hạn mức, không phải "dùng vô hạn": vượt $5 thì trả thêm phần vượt. RAM thường trực là khoản tốn nhất, nên các worker tốn LLM (`agent-worker`, `ml-worker`) đều có cờ tắt để tiết kiệm khi không demo.
