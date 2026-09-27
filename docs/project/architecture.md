# Kiến trúc — AI Quality Intelligence Platform

> **Cập nhật 2026-06-27:** Cập nhật mô tả KB nội bộ: xóa claim phủ số phòng ban cố định; ghi rõ KB dùng nhãn legacy (Safety, CSKH, Vận hành, IT) vì soạn trước khi chuyển 6 phòng ban chuẩn.
>
> **Cập nhật 2026-09-27 (US-077 / decision 0017):** thêm Customer web (`customer-web/`), bỏ role `guest` thay bằng `pending`.

Phân tích phản hồi khách hàng smart mobility (xanhSM) và định tuyến sự cố tới đúng phòng ban.

## Một repo, ba tầng

```
AI-Quality-Intelligence-Platform/
├── app/        Staff web: TanStack Start + React 19 (Quality Cockpit, auth, chat, admin)
├── customer-web/ Customer web: Vite + React SPA tĩnh (gửi phản hồi + tra cứu, không đăng nhập)
├── pipeline/   Python FastAPI: clean → classify → ingest → spike → LLM agent → multi-agent
├── supabase/   Schema PostgreSQL + RLS + RBAC (6 migration)
└── data/       Dataset public review + metadata synthetic + train splits + taxonomy
```

Supabase là trục nối: pipeline Python **ghi** kết quả, frontend **đọc** để hiển thị (realtime). Backend FastAPI chịu trách nhiệm xử lý + xác thực; frontend cũng đọc trực tiếp Supabase qua RLS cho realtime subscription.

## Cấu trúc thư mục `data/`

```
data/
├── knowledge_base/       KB nội bộ cho RAG theo phòng ban (SOP neo chính sách greensm thật + mock)
│   ├── sop/              quy trình xử lý theo phòng (an toàn, gian lận, thái độ, khiếu nại NTD...)
│   ├── sla/              cam kết bồi thường chuẩn
│   ├── tech/             lỗi kỹ thuật + bảo mật dữ liệu (neo chính sách greensm)
│   └── tickets/          1 file case study P5 làm few-shot cho AI
├── public_kb/            FAQ khách hàng cho tầng chat công khai `public_only` (audience: public)
├── taxonomy/             routing_table.json, severity_rules.json
├── reference/            area_catalog.json (16 khu vực HN/HCM/ĐN), enrichment
├── raw/                  Dataset review công khai (Google Play + App Store)
├── processed/            seed_real_clean.json — nguồn ingest chính
├── train/                seed_train_labeled + train/test split cho ML
├── demo/                 seed_demo_150.json cho demo nhanh
└── auxiliary/data2/      Dataset phụ trợ/thí nghiệm, không thay runtime
```

Mỗi file trong `knowledge_base/` có YAML frontmatter `department` để RAG lọc theo phòng. KB nội bộ hiện dùng nhãn legacy (`Safety`, `CSKH`, `Vận hành`, `IT`) vì được soạn trước khi chuyển sang 6 phòng ban chuẩn; các phòng Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận chưa có tài liệu KB riêng. `public_kb/` gắn `topic_group` theo phòng nhưng mở cho mọi khách. `data/taxonomy/` không chứa `safety_keywords.json`; file keyword này chỉ nằm trong `data/auxiliary/data2/taxonomy/` để thí nghiệm Data_2. Xem [agents-guide.md](agents-guide.md), [rbac-departments.md](rbac-departments.md), và [`data/README.md`](../../data/README.md).

## Hạ tầng: 6 Railway service + `customer-web`

Hệ thống deploy thành 6 service riêng, cộng service `customer-web` mới đã có Dockerfile nhưng chưa tạo trên Railway (xem chi tiết ở [deploy-railway.md](deploy-railway.md)):

- `frontend` (Staff web) → `app/Dockerfile`
- `customer-web` (Customer web) → `customer-web/Dockerfile`, file tĩnh, chưa deploy
- `backend` (web API) → `pipeline/Dockerfile`
- `backend-worker`, `ingest-worker`, `ml-worker`, `agent-worker` → cùng `pipeline/Dockerfile.workers`, chọn entrypoint qua biến `WORKER_MODULE`

Web API và 4 worker dùng chung source `pipeline/` + `data/`. Job định kỳ (ticket workflow, live stream, ML scoring, multi-agent) chạy trong worker riêng để không trùng với scheduler on-demand của web API.

Code bên trong tách theo module để khi lỗi thì sửa đúng phần:

```
pipeline/
├── core/                 Path/config dùng chung cho backend
├── services/             Live stream, ticket workflow, agent context
├── agents/               8 agent nghiệp vụ + orchestrator (batch)
├── agent/                Chat agent ReAct + RAG + LLM provider router
├── ml/                   Model .joblib + script train
├── main.py               FastAPI app wiring + endpoint handlers
├── worker_*.py           4 entrypoint worker (ticket/ingest/ml/agent)
└── classifier.py, clean.py, rules.py, spike_detector.py, ...

app/src/
├── features/             Logic theo feature/domain
├── components/           UI components (AppShell, DepartmentBadge, ...)
├── routes/               TanStack route screens
├── integrations/         Supabase clients/auth middleware
└── lib/                  Shared frontend helpers/API client
```

## Luồng xử lý

```
Review (Customer web / form thủ công / demo 150 / dataset 4837 / streaming)
   │
   ▼
[1] clean.py        mask PII (SĐT, email), chuẩn hóa text
   │
   ▼
[2] classifier.py   TF-IDF + LinearSVC → topic (7 lớp) + sentiment   (tầng MODEL)
   │
   ▼
[3] rules.py        rule keyword ghi đè khi tín hiệu rõ              (tầng RULE)
   │                 - Safety / Payment-fraud / App / Map / Supply / Driver / Pricing / Delay
   │                 - negation guard ("app không thân thiện" ≠ positive)
   │                 - confidence band thật (rule mạnh 80–88%, mơ hồ 50–65%, câu ngắn ≤50%)
   │                 - needs_review = P5 / safety / confidence thấp
   ▼
[4] ingest.py       ghi vào Supabase feedback (topic, sentiment, severity P1..P5,
   │                 confidence, area code, needs_review, review_reason)
   ▼
[5] spike_detector  group theo area + topic + team; áp ngưỡng risk/volume → spike
   │
   ▼
[6] llm_agent.py    gửi review đã che PII cho LLM → {title, root cause, action}
   │
   ▼
[7] alerts          ghi alert vào Supabase → frontend hiển thị realtime
```

## Phân loại 2 tầng: Model + Rule

Khác bản đầu (chỉ có model + rule Safety đơn giản), giờ có **rule engine đầy đủ** (`pipeline/rules.py`) chạy SAU model:

- **Model** (TF-IDF + LinearSVC) cho dự đoán nền.
- **Rule keyword** ghi đè khi có tín hiệu mạnh và rõ, theo thứ tự ưu tiên: Safety > Driver-positive > Payment-fraud > App > Map > Payment > Supply > Driver-negative > Pricing > Delay > Positive chung.
- **Negation guard**: từ phủ định ("không/ko/chẳng/chưa") ngay trước keyword sẽ chặn gán sai.
- **Confidence band**: phản ánh độ chắc thật, không còn 95% cứng cho mọi câu.

Lý do: model thuần yếu ở **câu ngắn** (người dùng gõ form hay viết ngắn → ít token → model ngả về lớp đa số negative). Rule layer lấp đúng lỗ hổng này. (Đã thử retrain với augment câu ngắn nhưng làm sụp neutral recall 78%→7%, nên giữ model gốc + dùng rule.)

## Lưới Safety

Bất kỳ review chứa keyword nguy hiểm (tai nạn, xe tông, bỏ chạy, say xỉn, cướp, hành hung, sàm sỡ...) đều bị ép `Safety / negative / P5 / needs_review=true`, confidence hạ thấp. Rule luôn thắng model — an toàn không nhường cho xác suất.

## Hai chế độ chạy

**1. Streaming (luồng chính) — gần real-time**
- `POST /api/live-stream/start` bật APScheduler bơm batch theo `interval_seconds`. Demo dùng **50 review/giây** (`LIVE_STREAM_BATCH_SIZE=50`, `INTERVAL_SECONDS=1`, `LOOP=false`).
- Sau mỗi `ticket_every_batches` lô (mặc định 2), khi stream kết thúc hoặc khi admin bấm dừng → tự spike detect → LLM → ghi alert.
- Ticket workflow tự chuyển `open → in_progress → resolved`.
- Frontend subscribe Supabase realtime → dashboard tự cập nhật.

**2. Batch thủ công — nút bấm demo an toàn**
- `POST /api/run-real-pipeline` / `POST /api/trigger-spike-detect`: bắn một lô review và sinh alert ngay. Dùng khi không muốn phụ thuộc nhịp scheduler/mạng lúc demo.

Đã verify chạy thật: streaming bơm trọn 4837 review/~97s qua scheduler (sau khi fix lỗi Broken pipe do stdout pipe); LLM thật (OpenRouter) sinh alert root-cause + định tuyến phòng ban.

## Review Queue / Feedback Stream

Trang `/feedback` tách 2 luồng rõ ràng:

- **Cần duyệt (Review Queue)** — lấy đúng từ server `GET /api/feedback/recent?needs_review=true&reviewed=false`. Gồm ca P5/safety/confidence thấp. Có badge lý do + nút Duyệt / Sửa nhãn / Đã xử lý.
- **Luồng phản hồi (Feedback Stream)** — danh sách chung, loại các id đang trong Queue.
- **Stat cards**: Tổng / Cần duyệt / P5+P4 / Confidence thấp.

## Human-in-the-Loop + audit

- `PATCH /api/feedback/{id}/label` — nhân viên sửa nhãn AI gán sai → ghi `correction_logs` (ai sửa, field nào, cũ→mới), set `confidence=1.0`, `reviewed=true`, rời Review Queue.
- `PATCH /api/feedback/{id}/review` — duyệt / đánh dấu đã xử lý.
- `correction_logs` vừa là audit, vừa là dữ liệu retrain tương lai (vòng học khép kín).
- `POST /api/feedback/reclassify` (admin) — phân loại lại data cũ bằng rule mới, bỏ qua bản đã có người duyệt.

## Multi-agent layer

`pipeline/agents/` — 8 agent nghiệp vụ + orchestrator, phân tích theo phòng ban (IT/CSKH/Vận hành/Tài chính & Thanh toán/Sản phẩm/Quản lý Rủi ro & Gian lận). Điều phối bởi `orchestrator.run_agent_pipeline()` chạy trong `agent-worker`:

- **alert_agent** — phân cấp WATCH/WARNING/CRITICAL + chống alert trùng (cooldown).
- **router_agent** — định tuyến ticket theo topic → phòng ban + SLA; P5 override → Safety.
- **ticket_agent** — tạo/cập nhật ticket vào bảng `alerts`.
- **task_agent** — gom alert thành task theo `(team, area)`.
- **insight_agent** — gom metric/topic theo phòng ban.
- **analyst_agent** — gọi LLM phân tích root cause + action items, có persona theo phòng.
- **ingestion_agent** và **scoring_agent** — chạy độc lập ngoài orchestrator (ingest + ml-worker).

Chi tiết thứ tự thực thi và I/O từng agent: [agents-guide.md](agents-guide.md).

Endpoint: `GET /api/insights/departments`, `GET /api/insights/departments/{team}`, `POST /api/agent/run`.

## RBAC — 4 vai trò

`pipeline/auth_guard.py` xác thực Supabase JWT + đọc role từ `profiles`. 4 role: **admin / manager / staff / pending**. `pending` là tài khoản chờ cấp quyền: 403 ở mọi endpoint trừ `GET /api/me`, `POST /api/me/password` và `/health`. Tài khoản còn mật khẩu tạm (`app_metadata.must_change_password`) bị mọi role guard trả 403 cho tới khi đổi mật khẩu qua `POST /api/me/password`. Role thiếu hoặc không hợp lệ rơi về `pending`.
- Backend dùng SERVICE_ROLE_KEY (bypass RLS) nên gate quyền ở tầng API: `require_admin`, `require_ops_staff`.
- `pipeline/users_admin.py` — CRUD user (admin only), gồm tạo tài khoản `POST /api/admin/users` (mật khẩu tạm, bắt đổi ở lần đăng nhập đầu). Staff web không còn tự đăng ký.
- Bootstrap: profile đầu tiên = admin, còn lại = `pending` (trigger `handle_new_user`).

## Customer web và API công khai

Khách hàng không có tài khoản. `customer-web/` là SPA tĩnh riêng, không có Supabase client, gọi thẳng backend từ trình duyệt qua `VITE_BACKEND_API_URL` (không qua proxy, vì rate limit tính theo IP client lấy từ entry bên phải nhất của `X-Forwarded-For`). Hai route công khai nằm ở `pipeline/public_intake.py`:

- `POST /api/public/feedback` — gửi phản hồi, trả mã tra cứu. Có honeypot `website`: có nội dung thì 400, không lưu.
- `GET /api/public/feedback/{public_ref}` — trả đúng `public_ref`, `status` (`received` / `under_review` / `reviewed`), `created_at`. Mã hết hạn hoặc đã xoá nội dung trả 404.

Phản hồi ẩn danh đi qua đúng pipeline phân loại, chấm rủi ro, spike và định tuyến như mọi phản hồi khác. `backend-worker` xoá nội dung các dòng quá `retention_until` lúc 03:00 hằng ngày, giữ nguyên nhãn. Quyết định: [decisions/0016](../harness/decisions/0016-anonymous-public-feedback-intake.md), [decisions/0017](../harness/decisions/0017-separate-customer-web-retire-guest.md).

## Region mapping (code ↔ label)

`pipeline/regions.py` + `app/src/lib/regions.ts` (mirror). DB lưu **code** (`HN-Cau-Giay`, khớp spike detector); UI luôn hiển thị **label đẹp** (`Cầu Giấy, Hà Nội`). 16 khu vực HN/HCM/ĐN. Form dùng dropdown thay vì gõ tay → dữ liệu khu vực nhất quán.

## Demo vs Production

| Khía cạnh | Cái đang build (chạy thật) | Production đầy đủ (nếu mở rộng) |
| :--- | :--- | :--- |
| Ingest | Streaming scheduler 50/s + batch thủ công, nguồn dataset đóng gói | Hút review real-time trực tiếp từ store/app |
| Data | Public store review + metadata synthetic | Dữ liệu vận hành thật của hãng |
| Thông báo | Realtime trên dashboard | Push tới Slack/email/app tài xế |
| Hạ tầng | Supabase cloud + chạy local | Container hóa, CI/CD, monitoring |

## ML — distillation

Model `.joblib` (TF-IDF + LinearSVC) train trên nhãn do LLM sinh (distillation).

**Số đo chính thức — holdout n=968** (`eval/splits.py`, seed=42, model chỉ train trên 3.869 mẫu còn lại):

| Trục | Accuracy | KTC 95% | Macro-F1 | Baseline lớp đa số |
|---|---|---|---|---|
| Topic (7 lớp) | 75.0% | 72.2–77.6% | 0.674 | 33.4% |
| Department (6 lớp) | 71.1% | 68.1–73.8% | 0.698 | 33.1% |

Cohen's κ (department) = 0.635. Chạy lại: `.venv/bin/python -m eval.holdout_report`.

**Điểm yếu theo lớp** (bị accuracy tổng thể che):
- `Delay` recall **0.328** — bỏ sót 2/3 phản hồi chậm chuyến, phần lớn bị đẩy sang `App Issue`.
- `App Issue` precision **0.568** / recall 0.870 — hố đen: model dồn văn bản không chắc chắn vào đây, kéo precision phòng IT xuống 0.484.
- `Safety` chỉ có **7 mẫu** trong holdout → chưa kết luận được gì về năng lực phát hiện an toàn.

**Cảnh báo về `data/train/test_split.json` (932 mẫu):** KHÔNG phải holdout của `splits.py` — 79% số mẫu của nó nằm trong tập train của model hiện tại. Con số 77.1% từng công bố cho tập này thuộc về **model topic đời trước**, đã bị thay khi retrain 2026-06-25. Đừng dùng lại.

**Sentiment model chưa truy được nguồn gốc:** không có script train nào trong repo sinh ra `sentiment_model.joblib`. Nó đạt precision 1.000 trên lớp `neutral` (n=35) của holdout, trong khi model train sạch chỉ đạt 0.083 → dấu hiệu đã học trên holdout. Xem `ml/retrain_sentiment.py`.

Rule engine bù phần model yếu (câu ngắn, từ khóa rõ).

## LLM provider — failover

`pipeline/agent/model_router.py` hỗ trợ nhiều provider (OpenRouter, OpenAI, Gemini, Groq) + mock. `LLM_PROVIDER=auto` → dựng chuỗi mọi provider CÓ KEY, thử lần lượt; provider lỗi (key chết, hết credit) tự nhảy sang provider kế. Hết key thật → mock (vẫn sinh alert giả lập để demo luồng). Chat, spike, multi-agent đều hưởng failover này.

## MCP server (expose ra ngoài)

`pipeline/mcp_server.py` là MCP server stdio cho agent ngoài (Claude Desktop, ...) truy vấn platform. Nó là **adapter mỏng** bọc `agent/chat_tools.py` — không lặp logic. Danh tính (role + phòng ban) cố định phía server qua env `MCP_ROLE`/`MCP_SCOPE_TEAM`; `scope_team` không bao giờ đọc từ tham số tool nên client không leo được ra khỏi phòng ban. Chi tiết + cấu hình Claude Desktop: [mcp-server.md](mcp-server.md). Quyết định: [decisions/0009](../harness/decisions/0009-mcp-server-expose-platform.md).
