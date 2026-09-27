# AI Quality Intelligence Platform

**xanhSM** | Nền tảng Phân tích Chất lượng Dịch vụ Di chuyển Thông minh bằng AI

*Dự án cá nhân*

---

## Giới thiệu

**AI Quality Intelligence Platform** là nền tảng AI phân tích phản hồi khách hàng cho dịch vụ di chuyển thông minh **xanhSM**. Hệ thống tự động tiếp nhận phản hồi, làm sạch PII, phân loại bằng ML, phát hiện điểm nóng, tạo ticket/alert, và phân tích chuyên sâu theo phòng ban thông qua multi-agent LLM.

Mục tiêu: giúp đội ngũ vận hành nắm bắt nhanh vấn đề chất lượng dịch vụ, giảm thời gian xử lý, và đưa ra quyết định dựa trên dữ liệu.

> **Phạm vi**: chạy được cả local lẫn deploy. Production chạy trên Railway (6 service Docker; service `customer-web` mới chưa tạo) + Supabase cloud. Stack: FastAPI + Vite + Supabase. Hai web: **Staff web** (`app/`, cho nhân viên) và **Customer web** (`customer-web/`, khách gửi phản hồi không cần tài khoản).

---

## Tính năng

| # | Tính năng | Mô tả |
|---|-----------|-------|
| 1 | Phân loại tự động | Model TF-IDF/LinearSVC + bộ luật keyword an toàn tiếng Việt |
| 2 | Che giấu PII | Tự động mask SĐT, email, biển số xe |
| 3 | Ma trận Rủi ro Sâu | Chấm điểm 5 chiều (safety, fraud, attitude, vehicle, compliance) qua LLM Scoring Agent |
| 4 | Phát hiện Spike | Nhận diện điểm nóng → tự động tạo alert ticket |
| 5 | Multi-Agent | 8 agent nghiệp vụ + Orchestrator |
| 6 | Phân tích phòng ban | Báo cáo AI 6 phòng ban theo lịch (09:00 & 14:00, nhiều báo cáo/ngày), cấu trúc 3 khối Vấn đề → Phân tích → Đề xuất, phân tích sâu bằng LLM |
| 7 | Human-in-the-Loop | Hàng đợi duyệt nhãn — nhân viên sửa nhãn AI, ghi correction log |
| 8 | AI Chat & RAG (Tiered) | Hỏi đáp tích hợp Hybrid Search KB, tự động phân quyền truy cập (widget trang chủ `public_only`: Public FAQ / Staff: Internal Ops Tools) |
| 9 | Streaming Realtime | Ingest phản hồi theo luồng thời gian thực |
| 10 | RBAC 4 vai trò | Phân quyền admin, manager, staff, pending (chờ cấp quyền); chỉ admin tạo tài khoản |
| 11 | Khép kín Báo cáo → Task | HI-Loop Approval: Manager biên tập hành động AI đề xuất trong báo cáo rồi duyệt một nút để tự tạo task chính thức, có liên kết ngược về báo cáo gốc |
| 12 | MCP Server | Expose tool nghiệp vụ qua MCP (stdio) cho agent ngoài (Claude Desktop...), identity + phân quyền cố định phía server — xem [`docs/project/mcp-server.md`](docs/project/mcp-server.md) |
| 13 | Customer web | Khách gửi phản hồi và tra cứu trạng thái bằng mã tra cứu, không cần tài khoản; nội dung tự xoá sau 180 ngày — xem [`docs/project/guest-account.md`](docs/project/guest-account.md) |

---

## Kiến trúc tổng quan

```text
┌──────────────────────────────┐  ┌───────────────────────────┐
│   STAFF WEB (app/)           │  │  CUSTOMER WEB             │
│   React 19 + TanStack Start  │  │  (customer-web/)          │
│   Vite 7 + Tailwind          │  │  Vite + React, SPA tĩnh   │
│   shadcn/ui + Recharts       │  │  không đăng nhập          │
└──────────────┬───────────────┘  └─────────────┬─────────────┘
               │ REST API                       │ /api/public/*
               └───────┬────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│            BACKEND (pipeline/)                   │
│  FastAPI + scikit-learn + LLM Agents            │
│                                                 │
│  clean.py → classifier.py → rules.py           │
│  spike_detector.py → llm_agent.py              │
│  agent/   chat ReAct + RAG + model router       │
│  agents/  orchestrator + 8 agent nghiệp vụ      │
│                                                 │
│  4 worker: ticket · ingest · ml · agent         │
│  (ticket worker: xoá nội dung quá hạn 03:00)    │
└──────────────────────┬──────────────────────────┘
                       │ SQL / Realtime
                       ▼
┌─────────────────────────────────────────────────┐
│          SUPABASE (PostgreSQL)                   │
│       Auth + Database + Realtime                 │
└─────────────────────────────────────────────────┘
```

LLM Providers: OpenRouter, OpenAI, Gemini, Groq (cấu hình qua `LLM_PROVIDER` trong `.env`). Deploy: 6 Railway service Docker, xem [`docs/project/deploy-railway.md`](docs/project/deploy-railway.md).

---

## Cài đặt nhanh

### Yêu cầu

- Python 3.11 hoặc 3.12 (production Docker pin `python:3.11-slim`; không dùng 3.13/3.14 cho venv)
- Node.js 18+ (khuyên 20 LTS)
- Tài khoản Supabase cloud
- API key LLM (tùy chọn, cần cho agent)

### Bước 1: Cấu hình môi trường

```bash
git clone https://github.com/Kez-DE/AI-Quality-Intelligence-Platform.git
cd AI-Quality-Intelligence-Platform
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
set -a && source ../.env && set +a   # Windows: xem docs/project/setup-windows.md
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

### Bước 4: Customer web (Terminal 3, tuỳ chọn)

```bash
cd customer-web
npm install
VITE_BACKEND_API_URL=http://127.0.0.1:8000 npm run dev
```

Customer web không cần biến Supabase nào. Dev server chạy ở cổng 5175 (Staff web ở 5174), nên chạy song song được. Chi tiết: [`customer-web/README.md`](customer-web/README.md).

### Tài khoản Admin

- Email: `manhnguyn1912@gmail.com` / Password: `12345678`
- Tài khoản khác: admin tạo bằng form "Tạo tài khoản" trong trang Admin (mật khẩu tạm, bắt đổi ở lần đăng nhập đầu). Staff web không còn form tự đăng ký. Tài khoản tạo trong Supabase Dashboard vào với role `pending` và chờ admin cấp quyền.
- Chủ dự án cần tắt tự đăng ký và Google/Facebook trong Supabase Dashboard: xem [`docs/project/setup-supabase.md`](docs/project/setup-supabase.md) mục 8.1.

---

## Cấu trúc thư mục

```text
AI-Quality-Intelligence-Platform/
├── app/                    Staff web (React 19 / TanStack Start / Vite 7)
│   └── src/routes/         dashboard, feedback, alerts, insights, chat, admin
├── customer-web/           Customer web (Vite + React SPA tĩnh): gửi phản hồi, tra cứu mã
├── pipeline/               Backend (FastAPI + ML + Agent)
│   ├── main.py             API chính + endpoint handlers
│   ├── classifier.py       ML classifier (TF-IDF/LinearSVC)
│   ├── clean.py            PII masking
│   ├── rules.py            Rule engine tiếng Việt
│   ├── spike_detector.py   Phát hiện risk/volume spike và route ticket theo phòng
│   ├── llm_agent.py        LLM phân tích spike
│   ├── agent/              Chat ReAct + RAG (nội bộ/khách) + model router
│   ├── agents/             8 agent nghiệp vụ + orchestrator (batch)
│   ├── services/           Live stream, ticket workflow, agent context
│   ├── worker_*.py         4 worker: ticket / ingest / ml / agent
│   ├── core/               Path/config dùng chung
│   └── ml/                 Model .joblib + script train
├── supabase/               Migration SQL + cấu hình
├── data/
│   ├── README.md           Manifest dữ liệu, provenance, quy tắc sử dụng
│   ├── knowledge_base/     KB nội bộ mock cho RAG theo phòng
│   ├── public_kb/          FAQ công khai cho tầng chat public_only
│   ├── taxonomy/           routing_table.json, severity_rules.json
│   ├── reference/          area_catalog + enrichment summary
│   ├── raw/ processed/     Public reviews + dataset runtime đã clean
│   ├── train/ demo/        Split ML + seed demo 150 review
│   └── auxiliary/data2/    Dataset phụ trợ/thí nghiệm, không thay runtime
├── docs/                   Tài liệu chi tiết (xem mục Tài liệu)
├── JOURNAL.md              Nhật ký phát triển
└── WORKLOG.md              Quyết định kỹ thuật
```

---

## Phân quyền RBAC

| Trang | Admin | Manager | Staff | Pending |
|-------|:-----:|:-------:|:-----:|:-----:|
| Dashboard | có | có | có | không |
| Ticket Triage (Alerts) | có | có | có | không |
| Phản hồi (list + HITL) | có | có | có | không |
| Phân tích phòng ban | có | có | có | không |
| AI Chat / Hỗ trợ CSKH | có | có | có | không |
| Quản lý người dùng | có | không | không | không |
| Trigger Operations | có | không | không | không |

- **Admin**: toàn quyền, quản lý user, trigger ingest/streaming, xem mọi phòng
- **Manager**: giám sát phòng mình — alerts, feedback, insights, reports, chat
- **Staff**: công việc hàng ngày phòng mình — feedback, tasks, chat
- **Pending**: tài khoản chờ cấp quyền, chỉ thấy màn "Tài khoản đang chờ admin cấp quyền"; backend trả 403 trừ `GET /api/me`, `POST /api/me/password` và `/health`
- **Khách hàng**: không có tài khoản, dùng Customer web

Ngoài role, mỗi ops user gắn một **phòng ban** (IT/CSKH/Vận hành/Tài chính & Thanh toán/Sản phẩm/Quản lý Rủi ro & Gian lận) quyết định họ thấy dữ liệu của ai. Manager/staff chỉ xem và thao tác trong phòng mình; admin xem tất cả. Chi tiết cơ chế scope: [`docs/project/rbac-departments.md`](docs/project/rbac-departments.md).

---

## Luồng demo

1. Login admin
2. Gửi phản hồi mới → kiểm tra topic/sentiment/severity tự gán
3. Xem Luồng phản hồi + Cần duyệt (HITL)
4. Sửa một nhãn sai → correction log
5. Chạy streaming hoặc ingest 150 review
6. Vào Ticket Triage xem alert
7. Phân tích phòng ban → bấm "Phân tích sâu"
8. Vào Báo cáo AI → sửa Draft Task → bấm "Duyệt và triển khai task" → xem task mới trên Task Board (badge "Từ báo cáo")
9. AI Chat: hỏi "khu vực nào đang nóng?"
10. Mở Customer web, gửi một phản hồi → nhận mã tra cứu → xem trạng thái; trong Staff web, dòng đó có badge "Khách hàng"

Kịch bản chi tiết: [`docs/project/demo-script.md`](docs/project/demo-script.md)

---

## Tài liệu

**Bắt đầu**

| File | Nội dung |
|------|----------|
| [`docs/project/setup-macos.md`](docs/project/setup-macos.md) | Cài đặt trên macOS |
| [`docs/project/setup-windows.md`](docs/project/setup-windows.md) | Cài đặt trên Windows |
| [`docs/project/setup-supabase.md`](docs/project/setup-supabase.md) | Cấu hình Supabase (auth, schema, migration) |
| [`pipeline/README.md`](pipeline/README.md) | Backend/ML pipeline chi tiết |

**Kiến trúc & AI**

| File | Nội dung |
|------|----------|
| [`docs/project/co_che.md`](docs/project/co_che.md) | Cơ chế tổng thể: luồng → ticket/alert/task/report, phân quyền, chia việc, lộ trình cải thiện (đọc trước khi build lại) |
| [`docs/project/architecture.md`](docs/project/architecture.md) | Kiến trúc tổng thể, 3 tầng, cấu trúc data, 6 service |
| [`docs/project/architecture-diagram.md`](docs/project/architecture-diagram.md) | Sơ đồ Mermaid các module |
| [`docs/project/architecture/e2e-flow.md`](docs/project/architecture/e2e-flow.md) | Luồng xử lý phản hồi đầu cuối (E2E) — hiện trạng thực tế của code |
| [`docs/project/architecture/routing-taxonomy.md`](docs/project/architecture/routing-taxonomy.md) | Taxonomy định tuyến: 6 phòng ban, bảng topic→phòng, quy tắc override, accuracy holdout (71.1% dept) |
| [`docs/project/ai-systems.md`](docs/project/ai-systems.md) | 4 lớp AI, LLM router, luồng dữ liệu theo worker |
| [`docs/project/agents-guide.md`](docs/project/agents-guide.md) | 8 agent + orchestrator: thứ tự thực thi, I/O, routing |
| [`docs/project/rbac-departments.md`](docs/project/rbac-departments.md) | Phân quyền role + scope theo phòng ban |

**Dữ liệu & KB**

| File | Nội dung |
|------|----------|
| [`data/README.md`](data/README.md) | Manifest dữ liệu, provenance, dataset runtime, Data_2 phụ trợ |
| [`data/knowledge_base/README.md`](data/knowledge_base/README.md) | KB nội bộ mock, frontmatter, cách retriever ops đọc Markdown |
| [`data/public_kb/README.md`](data/public_kb/README.md) | KB công khai cho tầng chat `public_only`, manifest và quy tắc biên tập |
| [`data/auxiliary/data2/README.md`](data/auxiliary/data2/README.md) | Data_2 phụ trợ cho safety spike và thí nghiệm balanced-label |

**Vận hành**

| File | Nội dung |
|------|----------|
| [`docs/project/deploy-railway.md`](docs/project/deploy-railway.md) | Deploy 6 service (+ `customer-web`) lên Railway qua GitHub Actions |
| [`docs/project/demo-script.md`](docs/project/demo-script.md) | Kịch bản demo 5-7 phút |
| [`docs/project/guest-account.md`](docs/project/guest-account.md) | Khách hàng (Customer web), tài khoản chờ cấp quyền, cách tạo tài khoản |
| [`docs/project/eval-evidence.md`](docs/project/eval-evidence.md) | Bằng chứng đánh giá model (Gate G2) |

---

## Tech Stack

| Layer | Công nghệ |
|-------|-----------|
| Frontend | React 19, TanStack Start/Router/Query, Vite 7, Tailwind CSS 4, shadcn/ui, Recharts |
| Backend | FastAPI, Python 3.10+, scikit-learn (TF-IDF + LinearSVC), multi-agent LLM |
| LLM | OpenRouter / OpenAI / Gemini / Groq (multi-provider) |
| Database | Supabase (PostgreSQL + Auth + Realtime) |

---

## Quy tắc làm việc

- Trước khi PR: cập nhật `JOURNAL.md`, `WORKLOG.md` nếu có quyết định mới
- Commit nhỏ theo phase, không commit `.env`, `.venv`, `node_modules`
- Push GitHub khi đã build/test thành công

---

## License

Dự án cá nhân, phục vụ mục đích học tập và demo.
