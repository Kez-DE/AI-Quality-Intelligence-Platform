# C2-App-116 — AI Quality Intelligence Platform

**xanhSM** | Nền tảng Phân tích Chất lượng Dịch vụ Di chuyển Thông minh bằng AI

*AI20K Build Cohort 2 — Team 116*

---

## Giới thiệu

**C2-App-116** là nền tảng AI phân tích phản hồi khách hàng cho dịch vụ di chuyển thông minh **xanhSM**. Hệ thống tự động tiếp nhận phản hồi, làm sạch PII, phân loại bằng ML, phát hiện điểm nóng, tạo ticket/alert, và phân tích chuyên sâu theo phòng ban thông qua multi-agent LLM.

Mục tiêu: giúp đội ngũ vận hành nắm bắt nhanh vấn đề chất lượng dịch vụ, giảm thời gian xử lý, và đưa ra quyết định dựa trên dữ liệu.

> **Phạm vi**: chạy local, không Docker, chưa deploy public URL. Sử dụng Supabase cloud + FastAPI + Vite.

---

## Tính năng

| # | Tính năng | Mô tả |
|---|-----------|-------|
| 1 | Phân loại tự động | Model TF-IDF/LinearSVC + bộ luật keyword an toàn tiếng Việt |
| 2 | Che giấu PII | Tự động mask SĐT, email, biển số xe |
| 3 | Ma trận Rủi ro Sâu | Chấm điểm 5 chiều (safety, fraud, attitude, vehicle, compliance) qua LLM Scoring Agent |
| 4 | Phát hiện Spike | Nhận diện điểm nóng → tự động tạo alert ticket |
| 5 | Multi-Agent | 6 agent nghiệp vụ + Orchestrator |
| 6 | Phân tích phòng ban | Insights 6 phòng ban với phân tích sâu bằng LLM |
| 7 | Human-in-the-Loop | Hàng đợi duyệt nhãn — nhân viên sửa nhãn AI, ghi correction log |
| 8 | AI Chat | Hỏi đáp trực tiếp về dữ liệu phản hồi |
| 9 | Streaming Realtime | Ingest phản hồi theo luồng thời gian thực |
| 10 | RBAC 4 vai trò | Phân quyền admin, manager, staff, guest |

---

## Kiến trúc tổng quan

```text
┌─────────────────────────────────────────────────┐
│            FRONTEND (app/)                       │
│  React 19 + TanStack Start + Vite 7 + Tailwind  │
│  shadcn/ui + Recharts                           │
└──────────────────────┬──────────────────────────┘
                       │ REST API
                       ▼
┌─────────────────────────────────────────────────┐
│            BACKEND (pipeline/)                   │
│  FastAPI + scikit-learn + LM Agents             │
│                                                 │
│  clean.py → classifier.py → rules.py           │
│  spike_detector.py → llm_agent.py              │
│  agents/ (orchestrator, router, insight,        │
│           analyst, alert, ingestion)            │
└──────────────────────┬──────────────────────────┘
                       │ SQL / Realtime
                       ▼
┌─────────────────────────────────────────────────┐
│          SUPABASE (PostgreSQL)                   │
│       Auth + Database + Realtime                 │
└─────────────────────────────────────────────────┘
```

LLM Providers: OpenRouter, OpenAI, Gemini, Groq (cấu hình qua `LLM_PROVIDER` trong `.env`).

---

## Cài đặt nhanh

### Yêu cầu

- Python 3.10+
- Node.js 18+ (khuyên 20 LTS)
- Tài khoản Supabase cloud
- API key LLM (tùy chọn, cần cho agent)

### Bước 1: Cấu hình môi trường

```bash
git clone https://github.com/AI20K-Build-Cohort-2/C2-App-116.git
cd C2-App-116
cp .env.example .env
```

Điền các biến tối thiểu trong `.env`:

```env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
BACKEND_API_URL=http://127.0.0.1:8000
VITE_BACKEND_API_URL=http://127.0.0.1:8000
LLM_PROVIDER=auto
OPENROUTER_API_KEY=sk-or-...   # tùy chọn
```

### Bước 2: Backend (Terminal 1)

```bash
cd pipeline
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
set -a && source ../.env && set +a   # Windows: xem docs/setup-windows.md
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Kiểm tra: `curl http://127.0.0.1:8000/health`

### Bước 3: Frontend (Terminal 2)

```bash
cd app
npm install
set -a && source ../.env && set +a
npx vite dev --port 5174 --host 127.0.0.1
```

Mở: [http://localhost:5174](http://localhost:5174)

### Tài khoản Admin

- Email: `manhnguyn1912@gmail.com` / Password: `12345678`
- Staff/Guest: tạo qua UI hoặc Supabase Auth → gán role trong trang Admin.

---

## Cấu trúc thư mục

```text
C2-App-116/
├── app/                    Frontend (React 19 / TanStack Start / Vite 7)
│   └── src/routes/         dashboard, feedback, alerts, insights, chat, admin
├── pipeline/               Backend (FastAPI + ML + Agent pipeline)
│   ├── main.py             API chính
│   ├── classifier.py       ML classifier (TF-IDF/LinearSVC)
│   ├── clean.py            PII masking
│   ├── rules.py            Rule engine tiếng Việt
│   ├── spike_detector.py   Phát hiện spike P4/P5
│   ├── llm_agent.py        LLM scoring & ticket generation
│   ├── agents/             Multi-agent system
│   └── ml/                 Model .joblib + experiment scripts
├── supabase/               Migration SQL + cấu hình
├── data/                   Training data & datasets
├── docs/                   Tài liệu chi tiết
├── scripts/                Utility scripts
├── Todo.md                 Backlog cải tiến
├── JOURNAL.md              Nhật ký cohort
└── WORKLOG.md              Quyết định kỹ thuật
```

---

## Phân quyền RBAC

| Trang | Admin | Manager | Staff | Guest |
|-------|:-----:|:-------:|:-----:|:-----:|
| Dashboard | ✅ | ✅ | ✅ | ✅ |
| Ticket Triage (Alerts) | ✅ | ✅ | ❌ | ❌ |
| Phản hồi (list + HITL) | ✅ | ✅ | ✅ | ✅ |
| Phân tích phòng ban | ✅ | ✅ | ❌ | ❌ |
| AI Chat / Hỗ trợ CSKH | ✅ | ✅ | ✅ | ✅ |
| Quản lý người dùng | ✅ | ❌ | ❌ | ❌ |
| Trigger Operations | ✅ | ❌ | ❌ | ❌ |

- **Admin**: toàn quyền, quản lý user, trigger ingest/streaming
- **Manager**: giám sát — alerts, feedback, insights, chat
- **Staff**: công việc hàng ngày — feedback, chat
- **Guest**: dashboard, feedback, chat hỗ trợ CSKH

---

## Luồng demo

1. Login admin
2. Gửi phản hồi mới → kiểm tra topic/sentiment/severity tự gán
3. Xem Luồng phản hồi + Cần duyệt (HITL)
4. Sửa một nhãn sai → correction log
5. Chạy streaming hoặc ingest 150 review
6. Vào Ticket Triage xem alert
7. Phân tích phòng ban → bấm "Phân tích sâu"
8. AI Chat: hỏi "khu vực nào đang nóng?"

Kịch bản chi tiết: [`docs/demo-script.md`](docs/demo-script.md)

---

## Tài liệu

| File | Nội dung |
|------|----------|
| [`docs/setup-macos.md`](docs/setup-macos.md) | Cài đặt trên macOS |
| [`docs/setup-windows.md`](docs/setup-windows.md) | Cài đặt trên Windows |
| [`docs/setup-supabase.md`](docs/setup-supabase.md) | Cấu hình Supabase |
| [`docs/architecture.md`](docs/architecture.md) | Kiến trúc hệ thống |
| [`docs/agents-guide.md`](docs/agents-guide.md) | Hệ thống multi-agent |
| [`docs/demo-script.md`](docs/demo-script.md) | Kịch bản demo 5-7 phút |
| [`docs/guest-account.md`](docs/guest-account.md) | Cơ chế tài khoản khách |
| [`pipeline/README.md`](pipeline/README.md) | Hướng dẫn backend/ML pipeline |

---

## Tech Stack

| Layer | Công nghệ |
|-------|-----------|
| Frontend | React 19, TanStack Start/Router/Query, Vite 7, Tailwind CSS 4, shadcn/ui, Recharts |
| Backend | FastAPI, Python 3.10+, scikit-learn (TF-IDF + LinearSVC) |
| LLM | OpenRouter / OpenAI / Gemini / Groq (multi-provider) |
| Database | Supabase (PostgreSQL + Auth + Realtime) |

---

## Quy tắc làm việc nhóm

- Trước khi PR: cập nhật `JOURNAL.md`, `WORKLOG.md` nếu có quyết định mới
- Ghi AI usage log: `python3 scripts/log_manual.py --tool "<tool>" --prompt "<việc>" --result "<kết quả>"`
- Commit nhỏ theo phase, không commit `.env`, `.venv`, `node_modules`
- Push GitHub khi đã build/test thành công

---

## License

Dự án phục vụ mục đích học tập và demo trong khuôn khổ AI20K Build Cohort 2.
