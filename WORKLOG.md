# WORKLOG — C2-App-116

Nhật ký quyết định kỹ thuật, phân công và bug quan trọng của team 116.

## 2026-05-31

### Đề tài & stack
Chưa chốt. Team chưa thống nhất sản phẩm App-116 sẽ xây và ngôn ngữ/framework dùng.
TODO: ghi lại quyết định + lý do khi nhóm chốt (why approach này thay vì cái khác).

### Phân công
Chưa phân công. TODO: ai làm module nào, deadline nội bộ.

### Quy ước đang áp dụng (đề xuất của Kez, chờ nhóm xác nhận)
- Đặt tên branch theo dạng `<tên>/<task>`, mỗi branch một việc, xóa sau khi merge.
  Ví dụ: `kez/fix-codex-hooks`, `kez/init-docs`.
- Không push thẳng `main`. Mỗi thay đổi đi qua branch → PR → review → merge.
  (`main` hiện chưa bật branch protection; cần admin repo bật để ép luật này.)
- AI logging gắn theo từng cá nhân: mỗi thành viên tự `cp .env.example .env`
  + `bash scripts/setup_hooks.sh` trên máy mình và tự push phần của mình.
  Log stamp theo email git của từng người — nếu một người push hộ cả nhóm
  thì chỉ usage của người đó được ghi nhận.

### Bug quan trọng — `.codex/hooks.json` thiếu field `type`
- Triệu chứng: chạy `codex` trong repo báo lỗi
  `failed to parse hooks config .codex/hooks.json: missing field type`.
- Root cause: mỗi hook handler trong `.codex/hooks.json` chỉ có
  `{name, command, timeout}`, thiếu field bắt buộc `type`. Đối chiếu
  `.claude/settings.json` (chạy bình thường) thì mỗi handler đều có `"type": "command"`.
- Fix: thêm `"type": "command"` vào cả 2 handler (`log-prompt`, `log-stop`),
  theo schema chính thức tại developers.openai.com/codex/hooks → PR #1.
- Ghi chú: BTC đã cho phép team chủ động sửa scripts.

## 2026-06-12

### Chốt đề tài & stack
- Sản phẩm: **AI Quality Intelligence Platform** (Quality Operation Cockpit) —
  phân tích phản hồi khách hàng smart mobility (xanhSM/GreenSM).
- Stack: React 19 + TanStack Start (frontend `app/`), Python FastAPI + scikit-learn
  (pipeline `pipeline/`), Supabase (Postgres + Auth) làm trục dữ liệu.

### Quyết định kỹ thuật — cấu trúc repo (Hướng A)
- Dự án nguồn `xanh_iu` (build sẵn ~90% qua Lovable) được di trú vào repo theo
  layout chuẩn "một repo một nguồn sự thật": `app/` (frontend) + `pipeline/`
  (Python, phẳng ở root) + `supabase/` + `data/` + `docs/`.
- Lý do chọn restructure thay vì giữ `UI/`+`backend/` đã commit: layout phẳng
  khớp blueprint, dễ truy vết, tách bạch frontend/pipeline/schema/data.
- Dùng `git mv` để giữ lịch sử file (tracked thành rename, không mất blame).
- Bỏ thư mục `.joblib` trùng trong `app/pipeline/` (MD5 trùng `pipeline/ml/`).

### Quyết định — chế độ Batch (không real-time cho demo)
- Backend xanh_iu có sẵn live-stream + APScheduler. Theo constraint đã chốt
  (batch thủ công, demo 100–150 review/lô), `LIVE_STREAM_ENABLED=false` mặc định.
- Luồng demo dùng các endpoint batch: `/api/ingest-real-dataset`,
  `/api/run-real-pipeline`, `/api/trigger-spike-detect`.

### Bug quan trọng 1 — classifier chạy MOCK
- Root cause: `classifier.py` load model `.joblib` nhưng nhánh predict là `pass`
  + TODO, trả nhãn giả theo độ dài text. Model thật (TF-IDF + LinearSVC) không
  được gọi.
- Fix: nối `topic_model`/`sentiment_model` thật; severity suy từ sentiment;
  confidence ước lượng từ `decision_function` margin (LinearSVC không có proba).
- Verify: accuracy trên 932 mẫu test → topic 77.1%, sentiment 94.3%.

### Bug quan trọng 2 — severity inversion trong spike_detector
- Root cause: spike detector lọc `severity in ["P0","P1"]`, nhưng thang dự án là
  P1..P5 với **P5 = nghiêm trọng nhất**. Safety override sinh P5 → spike detector
  bỏ sót đúng các ca nguy hiểm cần bắt. Alert lại hardcode `severity="P1"`.
- Fix: lọc band cao `["P4","P5"]`; alert lấy mức severity cao nhất thực tế trong
  vùng spike.

### Bug quan trọng 3 — path math sai sau khi làm phẳng pipeline
- Root cause: code giả định `backend/pipeline/` (2 cấp dưới root); layout phẳng
  `pipeline/` chỉ còn 1 cấp → `PROJECT_ROOT` trỏ ra ngoài repo.
- Fix: sửa `env_config.py`, `main.py`, `ingest.py`. Verify import chain đầy đủ +
  `PROJECT_ROOT` đúng + canonical data tồn tại.

### Data provenance
- Canonical: `data/raw` (5000 review công khai Google Play/App Store),
  `data/processed/seed_real_clean.json` (đã nhãn LLM), `data/train` (train/eval),
  `data/demo/seed_demo_150.json` (nút bấm demo, chưa nhãn ML).
- Phân biệt rõ trường THẬT (text/title/rating/timestamp/app...) vs TỔNG HỢP
  (area/driver_id/trip_id/event_time/is_demo_spike). Chi tiết: `data/README.md`.
- Pin `scikit-learn==1.6.1` khớp version train model (tránh InconsistentVersionWarning).

## 2026-06-12 (chiều) — đảo chiều: bật streaming, verify chạy thật E2E

### Quyết định đảo chiều constraint
- Trước đây chốt "không real-time, batch thủ công". NAY đổi: ứng dụng chạy thật
  CÓ STREAMING, đúng luồng thực tế. Quyết định giữ **cả hai mode** — streaming
  (live-stream + APScheduler) làm luồng chính, vẫn giữ nút bắn batch cho demo
  an toàn trên sân khấu (đỡ phụ thuộc mạng/LLM lúc demo trực tiếp).
- Lý do giữ batch: streaming phụ thuộc scheduler + LLM + mạng; nút bấm batch là
  đường lui an toàn khi demo trước hội đồng.

### Verify chạy thật end-to-end (không phải chỉ đọc code)
- Supabase cloud thật: 4 bảng đã tồn tại, `profiles` có user thật để ingest.
- Backend FastAPI sống, provider = OpenRouter (key thật, model owl-alpha).
- Ingest 200 review thật → DB: 0 failed, severity convert đúng P-format.
- Streaming engine: scheduler tự bơm 27 batch (~1.860 review) không can thiệp tay.
- LLM thật sinh alert root-cause đa tầng + định tuyến phòng ban (Vận hành/CSKH...);
  ticket workflow tự chuyển open → in_progress → resolved.
- Frontend: `vite build` OK (client+SSR, 80 modules); dev server cổng 5174 phục vụ
  app thật, nối đúng `VITE_BACKEND_API_URL`; alerts/feedback subscribe Supabase realtime.

### Bug quan trọng 4 — LLM key chết giữa lúc verify
- Triệu chứng: alert sinh ra nhưng nội dung là fallback "Không thể phân tích do
  lỗi LLM: 401 User not found". Spike detect + severity ĐÚNG, chỉ mắt xích LLM hỏng.
- Root cause: OpenRouter key cũ (từ xanh_iu/.env) hết hạn/hết credit; OpenAI key
  cũng 401; 9router local không chạy.
- Fix: Kez cấp key OpenRouter mới → test `/auth/key` HTTP 200 + chat completion thật
  trả nội dung → restart backend (env chỉ đọc lúc khởi động) → spike lại sinh alert
  phân tích thật. Bài học: env đổi phải restart server; verify key sống TRƯỚC khi chạy luồng.

### Bảo mật
- `.gitignore` thêm `.env.*` + `!.env.example` để chặn mọi biến thể env (kể cả backup).
- `.env` thật (Supabase + OpenRouter) chỉ sống local, KHÔNG commit.
