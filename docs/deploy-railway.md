# Deploy lên Railway với Docker

## Kiến trúc

```
Railway Project (C2-App-116)
├── backend   (Empty Service → pipeline/Dockerfile)
├── frontend  (Empty Service → app/Dockerfile)
└── Supabase  (external, giữ nguyên cloud)
```

Tách 2 service riêng biệt để:
- Scale độc lập (backend nặng ML, frontend nhẹ)
- Deploy riêng khi chỉ sửa 1 phần
- Dễ debug logs từng service

---

## Bước 1: Tạo project trên Railway

1. Vào [railway.app](https://railway.app), đăng nhập
2. **New Project** → chọn **Empty Project**
3. Đặt tên: `c2-app-116`

---

## Bước 2: Tạo Backend service

1. Trong project, click **+ New** → **Empty Service**
2. Đặt tên service: `backend`
3. Vào tab **Settings** của service:
   - **Source**: Connect GitHub repo `AI20K-Build-Cohort-2/C2-App-116`
   - **Build**: chọn **Dockerfile**
   - **Dockerfile Path**: `pipeline/Dockerfile`
   - **Watch Paths**: `pipeline/**`, `data/**` (chỉ redeploy khi thay đổi backend)
4. Tab **Networking**:
   - Click **Generate Domain** (lấy URL public, ví dụ `backend-xxx.up.railway.app`)
   - Hoặc chỉ dùng Internal Networking nếu frontend cùng project
5. Tab **Variables** → thêm env vars:

```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
LLM_PROVIDER=auto
OPENROUTER_API_KEY=sk-or-...
PORT=8000
```

---

## Bước 3: Tạo Frontend service

1. Click **+ New** → **Empty Service**
2. Đặt tên service: `frontend`
3. Tab **Settings**:
   - **Source**: cùng GitHub repo
   - **Build**: chọn **Dockerfile**
   - **Dockerfile Path**: `app/Dockerfile`
   - **Watch Paths**: `app/**` (chỉ redeploy khi thay đổi frontend)
4. Tab **Networking**:
   - Click **Generate Domain** (đây là URL user truy cập)
   - Hoặc gắn custom domain
5. Tab **Variables**:

```
PORT=3000
NITRO_PORT=3000
NITRO_HOST=0.0.0.0
NITRO_PRESET=node-server

# Trỏ tới backend service (dùng internal networking)
BACKEND_API_URL=http://backend.railway.internal:8000
VITE_BACKEND_API_URL=https://backend-xxx.up.railway.app

# Supabase (cần cho SSR)
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
```

Lưu ý: `VITE_BACKEND_API_URL` phải là URL public của backend (browser gọi trực tiếp). `BACKEND_API_URL` dùng internal networking (server-side calls).

---

## Bước 4: Kết nối 2 service

Railway cung cấp internal networking miễn phí giữa các service cùng project:

- Frontend gọi backend qua: `http://backend.railway.internal:8000`
- Browser gọi backend qua: `https://backend-xxx.up.railway.app`

Vào backend **Settings** → **Networking** → đảm bảo **Private Networking** đang bật.

---

## Bước 5: Deploy

Push code lên GitHub. Railway auto-deploy khi detect thay đổi trong watch paths.

Hoặc trigger thủ công: vào service → **Deployments** → **Trigger Deploy**.

---

## Test local với Docker Compose

Trước khi push lên Railway, test local:

```bash
cd C2-App-116

# Build và chạy cả 2 service
docker compose up --build

# Frontend: http://localhost:3000
# Backend:  http://localhost:8000/health
```

Dừng:
```bash
docker compose down
```

---

## Cách dùng Docker Image trên Railway (thay vì GitHub source)

Nếu muốn push Docker image lên registry rồi Railway pull:

```bash
# Build
docker build -f pipeline/Dockerfile -t c2-backend .
docker build -f app/Dockerfile -t c2-frontend .

# Tag cho Docker Hub hoặc GHCR
docker tag c2-backend ghcr.io/ai20k-build-cohort-2/c2-backend:latest
docker tag c2-frontend ghcr.io/ai20k-build-cohort-2/c2-frontend:latest

# Push
docker push ghcr.io/ai20k-build-cohort-2/c2-backend:latest
docker push ghcr.io/ai20k-build-cohort-2/c2-frontend:latest
```

Trên Railway: **+ New** → **Docker Image** → nhập image URL.

---

## Troubleshooting

### Build frontend fail: "Cannot find module @lovable.dev/vite-tanstack-config"
Package này nằm trong `node_modules`. Đảm bảo `npm ci` chạy trước `npm run build` trong Dockerfile.

### Backend crash: "No module named 'sklearn'"
Check requirements.txt có `scikit-learn>=1.6.1`. ML models cần đúng version.

### Frontend không gọi được backend
- Kiểm tra `VITE_BACKEND_API_URL` là URL public (có https)
- Kiểm tra backend service có domain public
- CORS trong `main.py` đã allow origin của frontend

### Nitro vẫn build Cloudflare target
Set env var `NITRO_PRESET=node-server` trong Railway variables. File `vite.config.ts` đã detect biến này.

---

## Chi phí

Railway Hobby plan (5$/tháng):
- 8GB RAM / 8 vCPU shared
- 500 giờ execution / tháng (đủ cho 2 service chạy liên tục)
- Nếu chỉ cần demo: dùng trial credit miễn phí
