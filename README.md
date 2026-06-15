# C2-App-116 — AI Quality Intelligence Platform

Hệ thống phân tích phản hồi khách hàng cho dịch vụ smart mobility/xanhSM. Ứng dụng nhận phản hồi → làm sạch PII → phân loại topic/sentiment/severity → tách Review Queue → phát hiện spike → tạo alert/ticket → phân tích theo phòng ban bằng multi-agent → cho nhân viên duyệt/sửa nhãn AI.

Dự án thuộc **AI20K Build Cohort 2 — Team 116**. Dữ liệu review là review công khai từ App Store/Google Play; metadata vận hành như khu vực/chuyến/driver là dữ liệu tổng hợp cho demo. Xem `data/README.md` để biết provenance.

> Phạm vi local hiện tại: **không Docker, chưa deploy public URL**. Chạy local bằng Supabase cloud/remote + FastAPI + Vite.

## 1. Trạng thái hiện tại

Đã build và verify các luồng chính:

- **Auth + RBAC 4 role**: admin, manager, staff, guest.
- **Feedback intake**: nhập phản hồi text, kênh, khu vực; backend tự phân loại, không cho client tự gán nhãn ML.
- **Classifier 2 tầng**: TF-IDF/LinearSVC + rule engine tiếng Việt (`pipeline/rules.py`).
- **Review Queue / Luồng phản hồi**: tách 2 cột rõ ràng; Queue chỉ giữ P5/Safety/confidence thấp/gibberish thật.
- **Human-in-the-Loop**: nhân viên duyệt/sửa nhãn; mọi correction ghi vào `correction_logs`.
- **Streaming demo**: bơm review theo batch 50/s, tự trigger spike/alert theo cấu hình.
- **Alert/Ticket triage**: spike detector + LLM agent tạo root cause/action/team.
- **Phân tích phòng ban**: trang `/insights` gom metric 6 phòng ban và chỉ gọi LLM khi bấm “Phân tích sâu”.
- **Giao diện tiếng Việt**: topic/sentiment/severity/channel hiển thị tiếng Việt, canonical value vẫn giữ tiếng Anh trong DB để không phá logic.
- **Docs/setup**: hướng dẫn macOS + Windows, lệnh chạy local, troubleshooting.

## 2. Kiến trúc tóm tắt

```text
User / Demo data
   │
   ▼
app/ React + TanStack Start ───────┐
   │                               │ đọc realtime
   │ gọi API                       ▼
pipeline/ FastAPI + ML + Agent ─▶ Supabase Postgres/Auth
   │
   ├─ clean.py              mask PII
   ├─ classifier.py         ML topic/sentiment
   ├─ rules.py              rule override + confidence + needs_review
   ├─ spike_detector.py     phát hiện điểm nóng P4/P5
   ├─ llm_agent.py          tạo alert/ticket bằng LLM
   └─ agents/               router/insight/analyst/alert/orchestrator
```

Chi tiết: `docs/architecture.md`.

## 3. Cấu trúc repo

```text
C2-App-116/
├── app/                    Frontend React/TanStack Start/Vite
│   └── src/routes/         dashboard, feedback, alerts, insights, chat, admin
├── pipeline/               FastAPI backend + ML + agent pipeline
│   ├── main.py             API chính
│   ├── classifier.py       ML classifier
│   ├── rules.py            Rule engine tiếng Việt
│   ├── agents/             Multi-agent theo phòng ban
│   └── ml/                 model .joblib + experiment scripts
├── supabase/               Migration SQL + hướng dẫn CLI
├── data/                   raw/processed/demo/train/reference/auxiliary
├── docs/                   Architecture, setup, demo script
├── scripts/                Cohort AI logging hooks — giữ nguyên
├── RUN.md                  Lệnh chạy/test local
├── Todo.md                 Backlog cải tiến sản phẩm
├── JOURNAL.md              Nhật ký cohort
└── WORKLOG.md              Quyết định kỹ thuật
```

## 4. Chạy nhanh local

### 4.1 Chuẩn bị `.env`

```bash
cp .env.example .env
```

Điền tối thiểu:

```env
SUPABASE_URL=...
SUPABASE_PUBLISHABLE_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
VITE_SUPABASE_URL=...
VITE_SUPABASE_PUBLISHABLE_KEY=...
BACKEND_API_URL=http://127.0.0.1:8000
VITE_BACKEND_API_URL=http://127.0.0.1:8000
LLM_PROVIDER=auto
OPENROUTER_API_KEY=...   # optional nhưng nên có để agent thật chạy
```

Không commit `.env` thật.

### 4.2 Backend

```bash
cd pipeline
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
set -a && . ../.env && set +a   # Windows xem docs/setup-windows.md
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

### 4.3 Frontend

```bash
cd app
npm install
set -a && . ../.env && set +a
node node_modules/vite/bin/vite.js dev --port 5174 --host 127.0.0.1
```

Mở: [http://localhost:5174](http://localhost:5174)

Chi tiết đầy đủ: `RUN.md`, `docs/setup-macos.md`, `docs/setup-windows.md`.

## 5. Tài khoản demo

- Admin: `demo.20260606180215@example.com` / `Admin@12345`
- Staff/guest: tạo trong UI hoặc Supabase Auth rồi gán role trong Admin page.

Nếu DB reset hoặc tài khoản chưa tồn tại, tạo user trong Supabase Auth trước, sau đó vào bảng `profiles`/Admin page để kiểm tra role.

## 6. Luồng demo nên chạy

1. Login admin.
2. Vào **Phản hồi**: gửi một phản hồi mới; kiểm tra topic/sentiment/severity tự gán.
3. Xem **Luồng phản hồi** bên trái và **Cần duyệt** bên phải.
4. Sửa một nhãn sai → kiểm tra correction log.
5. Chạy streaming hoặc ingest 150 review.
6. Vào **Ticket Triage** để xem alert/ticket.
7. Vào **Phân tích phòng ban** → metric 6 team hiện nhanh → bấm phân tích sâu cho Safety/IT.
8. Vào **AI Chat** hỏi “khu vực nào đang nóng?”.

Kịch bản nói trước hội đồng: `docs/demo-script.md`.

## 7. Có nên train lại model không?

Chưa nên thay model runtime chỉ vì cảm giác imbalance. Quyết định hiện tại:

- Giữ model `.joblib` hiện tại vì sentiment test tốt; đã từng thử augment câu ngắn nhưng làm neutral recall sụp mạnh.
- Dùng **rule engine + Review Queue + correction_logs** để xử lý lỗi demo và tạo data cải thiện thật.
- Dữ liệu `data/auxiliary/data2/` dùng cho experiment; chỉ swap model nếu metric held-out tốt hơn rõ ràng trên từng class.

Nói ngắn: **measure first, retrain later**. Agent/routing hiện hưởng lợi nhiều hơn từ rule + HITL hơn là retrain vội.

## 8. Quy tắc làm việc nhóm

- Trước khi PR: cập nhật `JOURNAL.md`, `WORKLOG.md` nếu có quyết định mới.
- Ghi AI usage log bằng hook hoặc manual log:

```bash
python3 scripts/log_manual.py --tool "<tool>" --prompt "<việc đã nhờ AI>" --result "<kết quả>"
python3 scripts/submit_log.py
```

- Commit nhỏ theo phase. Không commit `.env`, `.venv`, `node_modules`, `.ai-log/session.jsonl`, logs runtime.
- Push GitHub chỉ khi đã build/test và được team thống nhất.

