# Hướng dẫn cài đặt trên Windows

> Dành cho thành viên mới join dự án. Sau khi hoàn tất, bạn sẽ chạy được cả backend (FastAPI) và frontend (React/Vite) trên máy Windows.

## Yêu cầu hệ thống

| Phần mềm | Phiên bản tối thiểu | Kiểm tra (PowerShell) |
|-----------|---------------------|------------------------|
| Windows | 10 (21H2) hoặc 11 | `winver` |
| Python | 3.10+ | `python --version` |
| Node.js | 18+ (khuyên 20 LTS) | `node --version` |
| npm | 9+ | `npm --version` |
| Git | 2.30+ | `git --version` |

## 1. Cài đặt công cụ

### Python 3

Tải từ [python.org/downloads](https://www.python.org/downloads/) → chọn bản 3.12.x.

> **Quan trọng:** Khi cài, tick ✅ "Add Python to PATH" ở màn hình đầu tiên.

Kiểm tra sau khi cài:

```powershell
python --version
pip --version
```

### Node.js

Tải từ [nodejs.org](https://nodejs.org/) → chọn bản LTS (20.x).

Kiểm tra:

```powershell
node --version
npm --version
```

### Git

Tải từ [git-scm.com](https://git-scm.com/download/win). Cài đặt mặc định.

### Supabase CLI (tuỳ chọn)

```powershell
npm install -g supabase
# Hoặc dùng scoop:
# scoop install supabase
```

## 2. Clone repo và chuẩn bị environment

Mở **PowerShell** hoặc **Git Bash**:

```powershell
git clone <repo-url> C2-App-116
cd C2-App-116

# Tạo file .env từ template
copy .env.example .env
```

Mở `.env` bằng VS Code hoặc Notepad và điền các giá trị thật:

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
```

> Lấy key Supabase: vào [supabase.com](https://supabase.com) → project → Settings → API.

## 3. Cài đặt Backend (Python)

Mở PowerShell trong thư mục dự án:

```powershell
cd pipeline

# Tạo virtual environment
python -m venv .venv

# Kích hoạt venv (PowerShell)
.venv\Scripts\Activate.ps1

# Nếu bị lỗi ExecutionPolicy, chạy lệnh sau trước:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Cài đặt dependencies
pip install -r requirements.txt
```

Nếu dùng **CMD** (Command Prompt) thay vì PowerShell:

```cmd
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

Kiểm tra:

```powershell
python -c "import fastapi; print('FastAPI OK')"
python -c "import sklearn; print('Scikit-learn OK')"
```

## 4. Cài đặt Frontend (Node.js)

```powershell
cd ..\app
npm install
```

## 5. Chạy hệ thống

Mở **2 terminal** (2 tab PowerShell hoặc 2 cửa sổ trong VS Code):

### Terminal 1 — Backend (cổng 8000)

**PowerShell:**

```powershell
cd C2-App-116\pipeline
.venv\Scripts\Activate.ps1

# Load biến môi trường từ .env
Get-Content ..\.env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), 'Process')
    }
}

python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

**Git Bash (thay thế):**

```bash
cd ~/C2-App-116/pipeline
source .venv/Scripts/activate
set -a && source ../.env && set +a
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Chờ thấy `Application startup complete.` rồi kiểm tra:

```powershell
curl http://127.0.0.1:8000/health
# {"status":"ok","message":"Backend service is running"}
```

### Terminal 2 — Frontend (cổng 5174)

**PowerShell:**

```powershell
cd C2-App-116\app

# Load biến môi trường
Get-Content ..\.env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), 'Process')
    }
}

npx vite dev --port 5174 --host 127.0.0.1
```

**Git Bash (thay thế):**

```bash
cd ~/C2-App-116/app
set -a && source ../.env && set +a
npx vite dev --port 5174 --host 127.0.0.1
```

Mở trình duyệt: **http://localhost:5174**

## 6. Đăng nhập demo

| Role | Email | Password |
|------|-------|----------|
| Admin | `manhnguyn1912@gmail.com` | `Admin@12345` |
| Guest | Tự tạo trong Supabase Auth hoặc Admin page | |

## 7. Script tiện lợi — file `.bat`

Tạo file `start-backend.bat` ở thư mục gốc:

```bat
@echo off
cd pipeline
call .venv\Scripts\activate.bat
for /f "usebackq tokens=1,* delims==" %%A in ("..\.env") do (
    set "%%A=%%B"
)
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Tạo file `start-frontend.bat`:

```bat
@echo off
cd app
for /f "usebackq tokens=1,* delims==" %%A in ("..\.env") do (
    set "%%A=%%B"
)
npx vite dev --port 5174 --host 127.0.0.1
```

Double-click file `.bat` để chạy nhanh.

## 8. Xử lý lỗi thường gặp

### Lỗi `Activate.ps1 cannot be loaded because running scripts is disabled`

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Port đã bị chiếm

```powershell
# Tìm process dùng port 8000
netstat -ano | findstr :8000
# Kill process theo PID
taskkill /PID <pid> /F
```

### Lỗi `pip install` thất bại (C++ build tools)

Một số package Python cần Visual C++ Build Tools. Tải từ:
[visualstudio.microsoft.com/visual-cpp-build-tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

Chọn "Desktop development with C++" rồi cài lại:

```powershell
pip install -r requirements.txt
```

### Lỗi `python` không tìm thấy

- Kiểm tra Python đã được thêm vào PATH
- Thử dùng `python3` thay vì `python`
- Hoặc dùng đường dẫn đầy đủ: `C:\Users\<you>\AppData\Local\Programs\Python\Python312\python.exe`

### Frontend lỗi `VITE_SUPABASE_URL is undefined`

Đảm bảo đã load env trước khi chạy vite. Xem lại bước load biến môi trường ở mục 5.

### LLM agent trả về mock

- Kiểm tra có ít nhất 1 LLM key trong `.env`
- `LLM_PROVIDER=auto` sẽ tự chọn provider có key sống

### Lỗi encoding tiếng Việt

Nếu terminal hiện ký tự lạ thay vì tiếng Việt:

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001
```

## 9. Dừng hệ thống

Nhấn `Ctrl+C` ở cả 2 terminal.

Hoặc kill port bằng PowerShell:

```powershell
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force
Get-Process -Id (Get-NetTCPConnection -LocalPort 5174).OwningProcess | Stop-Process -Force
```

## 10. Cập nhật code mới

```powershell
cd C2-App-116
git pull origin main

# Backend
cd pipeline
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Frontend
cd ..\app
npm install
```

## Ghi chú: WSL2 (tuỳ chọn nâng cao)

Nếu bạn quen Linux, có thể dùng WSL2 và làm theo hướng dẫn macOS. Cài WSL2:

```powershell
wsl --install
```

Sau đó mở Ubuntu terminal và làm theo `docs/project/setup-macos.md`.
