# Hướng dẫn cài đặt trên macOS

> Hướng dẫn dựng môi trường dự án từ đầu. Sau khi hoàn tất, bạn sẽ chạy được cả backend (FastAPI) và frontend (React/Vite) trên máy Mac.

> **Cập nhật 2026-06-27:** đồng bộ env-var (.env.example) và thêm COHERE_API_KEY (bắt buộc cho RAG hybrid embedding).

## Yêu cầu hệ thống

| Phần mềm | Phiên bản tối thiểu | Kiểm tra |
|-----------|---------------------|-----------|
| macOS | 12 Monterey trở lên | `sw_vers` |
| Python | 3.10+ | `python3 --version` |
| Node.js | 18+ (khuyên 20 LTS) | `node --version` |
| npm hoặc bun | npm 9+ / bun 1.0+ | `npm --version` |
| Git | 2.30+ | `git --version` |

## 1. Cài đặt công cụ (nếu chưa có)

### Homebrew (trình quản lý package macOS)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Python 3

```bash
brew install python@3.12
# Hoặc dùng pyenv nếu bạn cần quản lý nhiều version:
# brew install pyenv && pyenv install 3.12.4
```

### Node.js

```bash
brew install node@20
# Hoặc dùng nvm:
# brew install nvm && nvm install 20
```

### Supabase CLI (tuỳ chọn — dùng khi cần chạy local DB)

```bash
brew install supabase/tap/supabase
```

## 2. Clone repo và chuẩn bị environment

```bash
git clone <repo-url> AI-Quality-Intelligence-Platform
cd AI-Quality-Intelligence-Platform

# Tạo file .env từ template
cp .env.example .env
```

Mở `.env` và điền các giá trị thật:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_PUBLISHABLE_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=eyJ...
BACKEND_API_URL=http://127.0.0.1:8000
VITE_BACKEND_API_URL=http://127.0.0.1:8000
LLM_PROVIDER=auto
OPENROUTER_API_KEY=sk-or-...   # Tuỳ chọn, nên có để agent chạy thật
COHERE_API_KEY=...             # Bắt buộc cho RAG hybrid embedding (lấy tại dashboard.cohere.com)
```

> Lấy key Supabase: vào [supabase.com](https://supabase.com) → project → Settings → API.

## 3. Cài đặt Backend (Python)

```bash
cd pipeline

# Tạo virtual environment
python3 -m venv .venv

# Kích hoạt venv
source .venv/bin/activate

# Cài đặt dependencies
pip install -r requirements.txt
```

Kiểm tra:

```bash
python -c "import fastapi; print('FastAPI OK')"
python -c "import sklearn; print('Scikit-learn OK')"
```

## 4. Cài đặt Frontend (Node.js)

```bash
cd ../app

# Cài dependencies (bun là công cụ chính; npm install cũng được)
bun install
```

## 5. Chạy hệ thống

Mở **2 terminal** riêng biệt:

### Terminal 1 — Backend (cổng 8000)

```bash
cd ~/AI-Quality-Intelligence-Platform/pipeline
source .venv/bin/activate
set -a && source ../.env && set +a
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Chờ thấy `Application startup complete.` rồi kiểm tra:

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok","message":"Backend service is running"}
```

### Terminal 2 — Frontend (cổng 5174)

```bash
cd ~/AI-Quality-Intelligence-Platform/app
set -a && source ../.env && set +a
npx vite dev --port 5174 --host 127.0.0.1
```

Mở trình duyệt: **http://localhost:5174**

> **Quan trọng:** Bước `set -a && source ../.env && set +a` bắt buộc cho cả backend lẫn frontend. Frontend cần biến `SUPABASE_URL`, `BACKEND_API_URL` (non-VITE) để Chat AI hoạt động.

## 6. Đăng nhập demo

| Role | Email | Password |
|------|-------|----------|
| Admin | `manhnguyn1912@gmail.com` | `Admin@12345` |
| Tài khoản khác | Admin tạo bằng form "Tạo tài khoản" trong trang Admin (mật khẩu tạm, đổi ở lần đăng nhập đầu) | |

## 7. Xử lý lỗi thường gặp

### Port đã bị chiếm

```bash
# Tìm và kill process đang dùng port
lsof -ti:8000 | xargs kill -9
lsof -ti:5174 | xargs kill -9
```

### Lỗi `ModuleNotFoundError` khi chạy backend

```bash
cd pipeline
source .venv/bin/activate
pip install -r requirements.txt
```

### Lỗi model `.joblib` không load được

Kiểm tra file tồn tại:

```bash
ls pipeline/ml/*.joblib
# Phải thấy topic_model.joblib và sentiment_model.joblib
```

### Frontend lỗi `VITE_SUPABASE_URL is undefined`

Đảm bảo đã load env trước khi chạy vite:

```bash
set -a && source ../.env && set +a
npx vite dev --port 5174
```

### Supabase connection refused

- Kiểm tra `SUPABASE_URL` trong `.env` đúng format `https://xxx.supabase.co`
- Kiểm tra `SUPABASE_PUBLISHABLE_KEY` không bị thiếu/sai

### LLM agent trả về mock (không phân tích thật)

- Kiểm tra có ít nhất 1 LLM key trong `.env`: `OPENROUTER_API_KEY` hoặc `OPENAI_API_KEY` hoặc `GROQ_API_KEY`
- `LLM_PROVIDER=auto` sẽ tự chọn provider có key sống

## 8. Dừng hệ thống

```bash
# Ctrl+C ở cả 2 terminal, hoặc:
lsof -ti:8000 | xargs kill -9
lsof -ti:5174 | xargs kill -9
```

## 9. Cập nhật code mới

```bash
cd ~/AI-Quality-Intelligence-Platform
git pull origin main

# Backend: cài lại nếu có package mới
cd pipeline && source .venv/bin/activate && pip install -r requirements.txt

# Frontend: cài lại nếu có package mới
cd ../app && bun install   # hoặc npm install
```
