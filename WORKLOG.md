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

## 2026-06-15

### Nâng cấp Kiến trúc — Chuyển sang Deep Risk Matrix & LLM Scoring Agent
- **Vấn đề**: Logic cũ chỉ dùng 1 nhãn `severity` (dựa trên sentiment model + rules từ khoá cố định). Điều này làm lọt lưới nhiều feedback rủi ro ẩn giấu vì ngôn ngữ tự nhiên vô hạn, if-else keyword không thể bắt hết các trường hợp phức tạp (như tiếng lóng, mỉa mai).
- **Giải pháp (Thay đổi kiến trúc)**:
  1. Cập nhật `MASTER_BLUEPRINT.md` chính thức hóa chiến lược **Tối ưu Ingestion (Phễu Lọc 3 Tầng Vàng)** để đưa LLM vào chấm điểm mà vẫn giữ chi phí API = ~0đ.
  2. Tạo Database Migration (`20260615000000_deep_risk_matrix.sql`) bổ sung 5 cột rủi ro (thang 0-10): `risk_safety`, `risk_fraud`, `risk_attitude`, `risk_vehicle`, `risk_compliance` vào bảng `feedback`.
  3. Code mới `pipeline/agents/scoring_agent.py`: Agent chuyên bóc tách 5 vector rủi ro bằng LLM (Llama 3) kèm thuật toán tính điểm Waterfall (overall_risk từ 1-5).
  4. Sửa cơ chế Fallback: Nếu LLM gặp sự cố (Rate Limit, Timeout), tự động gán cờ `needs_review = True` đưa vào Review Queue cho con người duyệt (Human-in-the-loop), tuyệt đối không dùng rule-based thay thế để tránh sai lệch dữ liệu.
- **Quyết định Tối ưu Chi phí / Tốc độ (Đang thi công phần Ingestion)**:
  - **Tầng 1 (Lọc ML)**: Dùng `.joblib` gạt bỏ 100% feedback positive/neutral (gán risk=0).
  - **Tầng 2 (Batching)**: Gom cụm các feedback negative lại gọi API LLM 1 lần duy nhất để giải quyết triệt để rủi ro nghẽn mạng lúc Demo Day.
  - **Tầng 3 (Caching)**: Dùng In-memory Hash Cache để tái sử dụng kết quả nếu review bị trùng lặp.

### Hoàn thiện Phase 1 — Xây dựng lại hệ thống 6 Agent & Tối ưu LLM
- **Vấn đề**: Hệ thống trước đây chỉ chạy gom nhóm insight cơ bản, thiếu sự liên kết thành một chu trình khép kín, và chưa có cơ chế kiểm soát lỗi hay quản lý chi phí LLM (dễ bị Rate Limit 429).
- **Giải pháp (Thay đổi kiến trúc)**:
  1. **Áp dụng Pydantic Schema**: Chuyển đổi toàn bộ 6 Agent sang dùng `schemas.py` để kiểm soát chặt chẽ cấu trúc Input/Output.
  2. **Orchestrator 7 Bước**: Viết lại `orchestrator.py` tạo vòng lặp khép kín: Quét P4/P5 -> Alert Agent (Dedup) -> Root Cause -> Router Agent (Định tuyến đội ban) -> Ticket Agent (Tạo ticket) -> Insight -> Analyst.
  3. **Tối ưu LLM & Cost**: Thiết kế thuật toán **Exponential Backoff** tự động chờ và thử lại khi gặp mã lỗi 429. Bổ sung **Memory Cache** hash nội dung để tái sử dụng phản hồi LLM trong cùng một mẻ (batch) quét.
  4. **System Observability**: Thêm `log_agent_run` lưu lại toàn bộ vết thực thi của Agent (thời gian, status, hash, usage) vào bảng `agent_run_logs` mới.
  5. **Fallback Heuristic**: Xây dựng giá trị dự phòng hợp lệ (fallback object) cho tất cả Agent để không làm chết hệ thống khi LLM gặp sự cố.
- **Kết quả**: Vòng lặp Multi-Agent đã sẵn sàng, tích hợp hoàn toàn qua endpoint `/api/agent/run` và cronjob APScheduler.

### Hoàn thiện Phase 2 — Triển khai Phân quyền (Role-based Access) & Tối ưu UI/UX
- **Vấn đề**: Toàn bộ tính năng đang mở cho tất cả người dùng, chưa có khái niệm Guest (Tài khoản khách) và Admin phân biệt, dẫn đến rò rỉ dữ liệu nội bộ (PII, Alert, Ticket).
- **Giải pháp**:
  1. Thêm cơ chế bảo vệ đường dẫn (Route Guard) trong `route.tsx`, tự động chặn `guest` truy cập `/alerts`, `/insights`, `/admin`.
  2. Cập nhật `AppShell.tsx` tự động co giãn thanh điều hướng (Sidebar) theo quyền của người dùng (Progressive Disclosure).
  3. Áp dụng UI Pattern 2 (Upload) cho màn hình Phản hồi của Guest: chỉ hiển thị form gửi. Áp dụng Pattern 6 (Queue + Approval) cho Staff/Admin: hiển thị Review Queue và luồng dữ liệu sống.
  4. Chỉnh sửa Dashboard (`QualityCockpit.tsx`): ẩn các thành phần Ticket, Alerts, Live Feed đối với Guest, và thay thế bằng `SecurityNotice` (khu vực hạn chế).
  5. Cấu hình lại Chat AI cho Guest thành "Hỗ trợ trực tuyến" (CSKH), giới hạn câu hỏi gợi ý để hướng dẫn sử dụng app, trong khi Admin tiếp tục dùng Ops Assistant.
- **Kết quả**: Hệ thống đã tách bạch quyền hạn giao diện an toàn, đáp ứng chuẩn thiết kế UX/UI cho Guest và Staff.

## 2026-06-16

### Hoàn thiện luồng duyệt tài khoản (Queue + Approval) & Default Guest Role
- **Vấn đề**: Tài khoản mới đăng ký mặc định là `staff` mang lại rủi ro bảo mật nếu lộ lọt luồng công việc nội bộ. Đồng thời, trang quản lý Admin (`admin.tsx`) có UI cũ gồm một danh sách chung dài, gây Cognitive Load cao và khó nhận biết tài khoản mới chờ duyệt.
- **Giải pháp**:
  1. Cập nhật Trigger `handle_new_user` trong Supabase (Migration `20260616000000_default_role_guest.sql`): tài khoản mới mặc định nhận role `guest` (tài khoản đầu tiên bootstrap vẫn là `admin`).
  2. Tối ưu UX/UI trang Admin theo hướng **Pattern 6: Queue + approval** và phong cách **Data-dense professional** dựa trên UX Audit skills.
  3. Ứng dụng Chunking chia màn hình thành 2 Tabs riêng biệt: "Chờ duyệt" (guest) và "Đã phân quyền" (staff, manager, admin).
  4. Cung cấp action duyệt nhanh (1-click) ngay tại tab "Chờ duyệt" (thay thế dạng Dropdown rườm rà), bổ sung Badge hiển thị số lượng chờ xử lý để tạo feedback trực quan.
- **Kết quả**: Thắt chặt luồng onboarding nội bộ; tối ưu mạnh mẽ tốc độ thao tác duyệt quyền của quản trị viên.

### Hoàn thiện Module 2 & 3 — Cơ chế Task Clustering & Báo cáo Chuyên sâu
- **Vấn đề**: Các alert rời rạc khiến phòng ban bị choáng ngợp; thiếu báo cáo tổng quan. Việc đánh giá rủi ro còn chung chung dựa trên 1 nhãn duy nhất.
- **Giải pháp**:
  1. **Task Clustering (Heuristic-first)**: Gom cụm các alert/ticket đang mở theo `(team, area)` bằng SQL (không tốn LLM token). LLM chỉ được dùng duy nhất 1 lần để sinh Tên & Tóm tắt khi tạo Task mới.
  2. **Phân tích Báo cáo Chuyên sâu (Analyst/Task Agent)**: Báo cáo định kỳ cho các Trưởng phòng được sinh ra tự động, định dạng Markdown với 4 mục khắt khe: (1) Nguyên nhân gốc rễ, (2) Mức rủi ro (LOW/WARNING/CRITICAL), (3) Dự báo, (4) Đề xuất hành động ưu tiên. Frontend UI tự động "đỏ/cam" (Highlight) dựa trên từ khóa rủi ro.
  3. **Deep Risk Matrix (Scoring Agent)**: Hoàn thiện chấm điểm rủi ro 5 chiều (An toàn, Gian lận, Thái độ, Phương tiện, Tuân thủ) kết hợp thuật toán Thác rơi (Max-pooling Waterfall) và phễu lọc 3 tầng (Lọc ML -> Batching LLM -> Caching) để tối ưu chi phí.
- **Kết quả**: Vòng lặp Agent đã hoàn thiện, vừa tiết kiệm API LLM vừa mang lại báo cáo vận hành cực kỳ sắc bén cho người quản lý.

## 2026-06-17

### Hoàn thiện Phase 3 — Quản trị Tổ chức, Giám sát & CSKH Online
- **Team Isolation**: Triển khai cơ chế phân quyền nâng cao trên API `/api/tasks` và `/api/reports`. Role Manager giờ đây chỉ nhìn thấy Ticket và Báo cáo thuộc `department` của mình (xác định qua bảng `profiles`).
- **Support Dashboard (`/support`)**: 
  - Tạo giao diện riêng theo kiến trúc **Queue + Approval** dành cho luồng CSKH.
  - Phân loại Ticket nổi bật theo mức độ khẩn cấp và SLA (Thời gian xử lý).
  - Tích hợp tính năng **Canned Responses** (Mẫu trả lời soạn sẵn) giúp đóng Ticket chỉ bằng một chạm.
- **Observability (Webhook & Healthcheck)**: 
  - Tích hợp `webhook_notifier.py` vào `spike_detector.py`. Tự động đẩy cảnh báo đến kênh chat nội bộ khi sinh ra Alert P5/Critical.
  - Thêm trang **System Health (`/health`)** trên React để Admin trực tiếp theo dõi uptime, latency của API, DB và mô hình LLM.

### Hoàn thiện Phase 4 — Gamification & UI Tối ưu
- **Team Leaderboard**: Thêm API `/api/leaderboard` tính toán tốc độ xử lý (Avg Resolution Time) và số lượng Ticket đã giải quyết. Hiển thị Widget xếp hạng lên màn hình `QualityCockpit` tạo động lực thúc đẩy năng suất giữa các Team.
- **Chế độ Tối (Dark Mode)**: 
  - Thiết kế Theme chuyển đổi sáng/tối đồng bộ qua Tailwind `darkMode: class`.
  - Tạo `useTheme` hook ghi nhớ tùy chọn vào `localStorage` và tự động kế thừa `prefers-color-scheme` của hệ điều hành.
- **Tổng kết**: Toàn bộ dự án AI Quality Intelligence Platform đã được phát triển hoàn thiện 100% roadmap từ Ingestion, AI Processing, đến Operation Dashboard và Gamification.

### Hoàn thiện Giai đoạn 2 — Tăng cường Bảo mật (Đặc biệt cho AI)
- **OWASP LLM (Tránh rò rỉ dữ liệu PII)**: Tích hợp hàm `mask_pii()` từ `clean.py` vào `pipeline/agent/chat_agent.py`. Lọc PII (Email, SĐT, Biển số xe) từ câu hỏi của người dùng và từ kết quả phân tích của Tool/LLM để tránh rò rỉ khi gán vào Prompt.
- **Quản lý Cấu hình (Pydantic Settings)**: Thêm thư viện `pydantic-settings` vào `requirements.txt`. Refactor `env_config.py` để sử dụng class `Settings` quản lý toàn bộ cấu hình, loại bỏ `os.getenv` thô sơ trong `main.py`, `webhook_notifier.py` và `model_router.py` nhằm nâng cao tính an toàn (type hinting & validation).
- **Rate Limiting**: Rà soát và xác nhận đã áp dụng giới hạn request (`chat_rate_limit` và `chat_rate_limit_staff`) cho endpoint `/api/agent/chat` nhằm phòng ngừa rủi ro bị lạm dụng API Key của LLM. Thống nhất sử dụng `httpx` thay cho `requests` trong Webhook.

## 2026-06-20

### Sửa lỗi luồng chấm điểm (Scoring Agent) và Cảnh báo (Spike Detector)
- **Vấn đề**: Các cảnh báo sinh ra không sử dụng điểm rủi ro thực tế (`overall_risk`) từ `scoring_agent.py`, dẫn đến sai lệch mức độ ưu tiên.
- **Giải pháp**: Cập nhật hàm `_severity_number` trong `spike_detector.py` để ưu tiên lấy trường `overall_risk` (chấm theo 5 chiều rủi ro) làm độ ưu tiên chuẩn. Đảm bảo vé P1-P5 phản ánh chính xác thuật toán Thác rơi (Waterfall).

### Sửa lỗi hiển thị Priority bị rác (`**Routing Note:**`)
- **Vấn đề**: `router_agent.py` không trả về `priority` ở nhánh Default, khiến chuỗi sinh ra bị rỗng, làm `task_agent.py` parse nhầm dòng liền kề thành độ ưu tiên.
- **Giải pháp**: Bổ sung `priority="P4"` làm mặc định cho nhánh Default. Làm chặt chẽ điều kiện regex bắt Priority trong `task_agent.py` để lọc bỏ các chuỗi rác.

### Sửa lỗi BUG-02 — Định tuyến sai phòng ban cho vé P5
- **Vấn đề**: Cấu hình `severity_overrides` mặc định ép MỌI vé có mác P5 về phòng Safety. Dẫn đến một "Lỗi ứng dụng" hay "Lỗi thanh toán" nghiêm trọng (P5) bị chuyển nhầm sang Safety thay vì IT hoặc CSKH.
- **Giải pháp**: 
  - Cập nhật `routing_table.json`: Bổ sung mảng `topics: ["Safety", "Driver Behavior"]` vào luật ghi đè P5.
  - Cập nhật `router_agent.py`: Chỉ cho phép override P5 sang Safety nếu chủ đề thuộc mảng nhạy cảm. Với các chủ đề khác, vé vẫn được chuyển về IT/CSKH nhưng **giữ nguyên độ ưu tiên P5** thay vì bị hạ cấp xuống ưu tiên mặc định của phòng ban đó.
