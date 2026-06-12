# C2-App-116 — AI Quality Intelligence Platform

Hệ thống phân tích phản hồi khách hàng cho dịch vụ gọi xe (smart mobility). Nhận đánh giá → ML phân loại topic/sentiment/severity → safety rule → agent LLM gom sự cố và định tuyến ticket cho phòng ban → dashboard + human review.

Dự án của **AI20K Build Cohort 2 — Team 116**. Xây trên dữ liệu đánh giá công khai (App Store / Google Play) kết hợp metadata vận hành tổng hợp — xem `data/README.md` để biết nguồn gốc từng trường.

## Kiến trúc (tóm tắt)

```
┌─────────────┐   ghi    ┌────────────┐   đọc   ┌──────────────┐
│  pipeline/  │ ───────▶ │  Supabase  │ ◀────── │     app/     │
│ Python ML + │          │ (Postgres) │         │ React + Vite │
│  LLM agent  │          │            │         │  (dashboard) │
└─────────────┘          └────────────┘         └──────────────┘
```

Supabase là trục: pipeline Python ghi vào, frontend đọc ra. Không cần backend server trung gian. Chi tiết luồng demo vs production: `docs/architecture.md`.

## Cấu trúc repo

```
├── app/             # Frontend — TanStack Start + React 19 + Supabase
├── pipeline/        # Backend xử lý — Python (ingest, ML, agent, spike)
├── supabase/        # DB migrations (profiles, feedback, alerts, chat)
├── data/            # Dataset: raw / processed / train / demo / reference
├── docs/            # architecture, demo-script
├── scripts/         # 🔒 Khung cohort — AI usage logging (không sửa)
├── JOURNAL.md       # Nhật ký tuần (bắt buộc cập nhật trước mỗi PR)
├── WORKLOG.md       # Quyết định kỹ thuật
└── .env.example     # Mẫu cấu hình (không commit .env thật)
```

## Chạy nhanh

**Backend pipeline** (chi tiết: `pipeline/README.md`):
```bash
cd pipeline && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py     # http://localhost:8000/docs
```

**Frontend** (chi tiết: `app/README.md`):
```bash
cd app && bun install && bun run dev
```

Cấu hình `.env` ở gốc repo (copy từ `.env.example`). Cần Supabase URL + service role key cho pipeline, và publishable key cho frontend.

## Demo

Kịch bản 5 phút trong `docs/demo-script.md`: bấm nút nạp ~150 đánh giá → dashboard sáng đỏ khu vực sự cố → agent sinh ticket gửi đúng phòng ban → nhân viên sửa một nhãn AI nhận nhầm (vòng Human-in-the-Loop).

---

## Khung Cohort — AI Logging (giữ nguyên)

### Cài pre-push hook

**Linux / macOS / Git Bash:**
```bash
bash scripts/setup_hooks.sh
```

**Windows PowerShell:**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1
```

### Cấu hình môi trường

```bash
cp .env.example .env
```

Điền `AI_LOG_SERVER` và `AI_LOG_API_KEY` (do khóa học cung cấp).

### Nhật ký tuần

Cập nhật **[JOURNAL.md](./JOURNAL.md)** cuối mỗi tuần: feature đã ship, AI tool đã dùng, vấn đề khó nhất, điều sẽ làm khác, kế hoạch tuần sau. **Phải cập nhật trước mỗi PR.**

### Worklog

Cập nhật **[WORKLOG.md](./WORKLOG.md)** mỗi khi có quyết định kỹ thuật hoặc đổi hướng: lý do chọn cách này, phân công, brainstorm, bug quan trọng + cách sửa.

### AI Logging

Prompt và tool call được **tự động log** khi dùng các AI tool được hỗ trợ (Claude Code, Cursor, Codex, Gemini, Antigravity, Copilot) sau khi chạy `setup_hooks`. Với ChatGPT/web tool, log thủ công:

```bash
bash scripts/_pyrun.sh scripts/log_manual.py --tool chatgpt --prompt "<việc đã làm>"
```

Hệ thống hook cần **một** trong: `python3`, `python`, hoặc `py` trên PATH.
