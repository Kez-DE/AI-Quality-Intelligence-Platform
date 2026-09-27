# Luồng xử lý phản hồi đầu cuối (E2E)

> **Cập nhật 2026-06-27:** Mở rộng từ 6 chặng pipeline sang đủ 12 luồng chuẩn theo spec Mục 2: thêm ingest/stream (Luồng 1), 5-dim risk scoring (Luồng 4), AI chat + tiered hybrid RAG (Luồng 8), human-in-the-loop duyệt nhãn (Luồng 9), RBAC 4 vai trò (Luồng 11), worker topology (Luồng 12).

Tài liệu này mô tả đúng hiện trạng của hệ thống. Các chặng dưới đây phản ánh code thực đang chạy, không phải thiết kế mục tiêu.

Spec định tuyến liên quan: `docs/superpowers/specs/2026-06-25-router-accuracy-design.md`.

---

## Danh mục 12 luồng chuẩn

| # | Luồng | File nguồn chính |
|---|-------|-----------------|
| 1 | Ingest & streaming realtime | `ingest.py`, `worker_ingest.py` |
| 2 | Clean + PII mask | `clean.py` |
| 3 | ML classify + severity rules | `classifier.py`, `rules.py`, `worker_ml.py` |
| 4 | Ma trận rủi ro 5 chiều (Scoring) | `agents/scoring_agent.py`, `worker_ml.py` |
| 5 | Spike → auto alert/ticket | `spike_detector.py`, `agents/alert_agent.py`, `agents/ticket_agent.py`, `worker_ticket.py` |
| 6 | Multi-agent orchestration | `agents/orchestrator.py` + router/ingestion/scoring/analyst/insight/alert/ticket/task |
| 7 | Phân tích phòng ban + báo cáo AI (6 phòng, 3 khối) | `departments.py`, `agents/report_builder.py`, `agents/analyst_agent.py`, `agents/insight_agent.py` |
| 8 | AI Chat + tiered hybrid RAG | `agent/chat_agent.py`, `agent/rag_engine.py`, `agent/knowledge_base.py`, `agent/public_kb.py` |
| 9 | Human-in-the-Loop duyệt nhãn + correction log | `main.py` (PATCH endpoints), eval `extract_corrections.py` |
| 10 | Khép kín Báo cáo → Task (HI-Loop approval) | `agents/task_agent.py`, report-approval endpoints trong `main.py` |
| 11 | RBAC 4 vai trò + scope phòng ban | `auth_guard.py`, `departments.py`, RLS migrations |
| 12 | Topology worker + API | `main.py`, `worker.py`, `worker_ticket/ingest/ml/agent.py` |

Luồng 1-7 là pipeline xử lý phản hồi chính. Luồng 8-12 là các luồng hỗ trợ và vận hành. Chi tiết mỗi luồng ở các phần bên dưới.

---

## Sơ đồ tổng quan (pipeline chính, Luồng 1-7)

```
Phản hồi khách hàng (text)
        |
        v
[1] PHÂN LOẠI
    classifier.predict_feedback()
      - TF-IDF + LinearSVC (pipeline/ml/topic_model.joblib)
      - rules.apply_rules()  <-- ghi đè theo keyword
    --> topic, sentiment, severity (P1-P5), confidence, needs_review
        |
        v
[2] ĐỊNH TUYẾN
    agents/router_agent.route_ticket()
      - Đọc data/taxonomy/routing_table.json
      - Thứ tự ưu tiên: P5 override > sentiment override > topic match > default
    --> phòng ban (IT / CSKH / Vận hành / Tài chính & Thanh toán / Sản phẩm / Quản lý Rủi ro & Gian lận), SLA, priority
        |
        v
[3] PHÁT HIỆN SPIKE & SINH TICKET
    spike_detector.py  <-- gom phản hồi theo (area, topic)
      - Tạo/cập nhật ticket qua agents/ticket_agent.create_or_update_ticket()
    --> bảng alerts (DB)
        |
        v
[4] SINH TASK
    agents/task_agent.cluster_alerts_into_tasks()
      - Gom alert theo (team, area)
      - Gọi LLM 1 lần khi cần tạo Task mới
    --> bảng tasks (DB)
        |
        v
[5] BÁO CÁO
    agents/insight_agent.generate_department_insights()
    agents/analyst_agent  <-- phân tích chuyên sâu
    agents/report_builder <-- render + lưu
    --> bảng department_reports (suggested_tasks JSONB, root_cause_summary)
        |
        v
[6] HI-LOOP APPROVAL (Manager)
    Manager xem báo cáo, chỉnh sửa Draft Tasks
    POST /api/reports/{id}/approve-and-dispatch
      - Gọi Postgres RPC: approve_report_and_dispatch
      - Tạo rows trong bảng tasks (source='report', report_id set)
    Nhân viên xem task trên tasks.tsx
      - Badge "Từ báo cáo" + link "Xem báo cáo gốc"
```

---

## Chi tiết từng chặng

### Chặng 1: Phân loại (`pipeline/classifier.py`)

Hàm `predict_feedback(text)` là điểm vào duy nhất. Nó chạy theo hai lớp:

**Lớp model (nền):** TF-IDF + LinearSVC, artifact ở `pipeline/ml/topic_model.joblib` và `pipeline/ml/sentiment_model.joblib`. Model trả về topic, sentiment, và ước lượng confidence từ decision function margin (không có `predict_proba` vì LinearSVC). Mức severity ban đầu được suy từ sentiment: negative = P3, neutral = P2, positive = P1.

**Lớp rule (`pipeline/rules.py`):** Chạy sau model, có thể ghi đè hoàn toàn. Thứ tự ưu tiên trong `apply_rules()`:

1. Safety keyword (ưu tiên cao nhất, có negation guard với window 16 ký tự) -- ép topic = Safety, severity = P5, force needs\_review = True.
2. Driver tích cực (keyword cụm rõ + negation guard).
3. Driver tiêu cực có chủ ngữ tài xế (kết hợp DRIVER\_NEGATIVE\_KEYWORDS + DRIVER\_SUBJECT\_KEYWORDS) -- tránh bị App/Payment cướp nhầm.
4. Payment fraud / mất tiền -- severity P4.
5. App Issue (crash, lag, lỗi app).
6. Navigation/Map -- gộp vào App Issue (không có topic Map riêng).
7. Payment thường.
8. Supply thiếu cuốc -- gộp vào Delay (Vận hành điều phối).
9. Driver tiêu cực (không có chủ ngữ tài xế rõ).
10. Lost item / tình trạng xe -- Other.
11. Pricing.
12. Delay.
13. Neutral, Positive, Negative chung.

Rule cũng tính `needs_review`: True khi confidence < 0.55, hoặc severity = P5, hoặc rule Safety kích hoạt.

Kết quả trả về: `{ topic, sentiment, severity ('P1'..'P5'), confidence, needs_review, review_reason }`.

### Chặng 2: Định tuyến (`pipeline/agents/router_agent.py`)

Hàm `route_ticket(topic, severity, sentiment)` đọc `data/taxonomy/routing_table.json` và chạy theo thứ tự ưu tiên cứng:

1. **Severity override:** P5 ép về Vận hành, SLA 1 giờ, bất kể topic hay sentiment.
2. **Sentiment override:** Positive + topic thuộc danh sách `["Other", "App Issue"]` ép về Sản phẩm. Positive về Payment, Driver Behavior không khớp danh sách, nên rơi xuống topic match (đúng phòng chuyên môn).
3. **Topic match:** Tra bảng routes theo topic.
4. **Default:** CSKH nếu không khớp gì.

Logic này là deterministic, không có LLM.

### Chặng 3: Spike detector + Ticket agent

`spike_detector.py` gom phản hồi theo (area, topic). Khi vượt ngưỡng (P5 = ngay lập tức, P4 = cụm nhỏ, thấp hơn = volume spike), nó gọi `agents/ticket_agent.create_or_update_ticket()`, tạo hoặc cập nhật row trong bảng `alerts`.

### Chặng 4: Task agent (`pipeline/agents/task_agent.py`)

`cluster_alerts_into_tasks()` gom alert theo **(team, area, topic)**. Nếu đã có Task còn hút được (`open` / `assigned` / `in_progress`) cùng bộ ba đó, nó gán alert vào Task hiện có và **nâng mức ưu tiên** nếu alert mới nặng hơn (ưu tiên chỉ đi lên, `due_at` siết theo SLA mới). Nếu chưa có, tạo Task mới với `topic`, `area`, `source='agent'` và `due_at` lấy từ SLA của routing table; LLM được gọi một lần để đặt title/summary, hỏng thì dùng tiêu đề suy diễn từ dữ liệu cụm. Cụm nào lỗi được đếm vào `clusters_failed` và trả về `status='partial_success'` — alert vẫn giữ `task_id` null để chu kỳ sau thử lại, không bị mất.

Hợp đồng đầy đủ: `docs/harness/decisions/0014-dispatch-and-hitl-contract.md`.

### Chặng 5: Báo cáo

`agents/insight_agent.generate_department_insights()` tổng hợp metric 24 giờ qua cho từng phòng. `analyst_agent` phân tích chuyên sâu. `report_builder` render và lưu vào bảng `department_reports`, bao gồm hai cột quan trọng:
- `suggested_tasks` (JSONB): danh sách task đề xuất từ phân tích AI.
- `root_cause_summary`: nguyên nhân gốc rễ do LLM tổng hợp.

### Chặng 6: HI-Loop Approval

Manager vào trang báo cáo (`app/src/routes/_authenticated/reports.tsx`), xem `suggested_tasks`, chỉnh sửa nội dung Draft Tasks nếu cần, rồi nhấn "Phê duyệt và phân công". Frontend gọi:

```
POST /api/reports/{id}/approve-and-dispatch
```

Backend gọi Postgres RPC `approve_report_and_dispatch` (migration `supabase/migrations/20260627000000_suggested_tasks_and_report_link.sql`). RPC tạo các row trong bảng `tasks` với:
- `source = 'report'`
- `report_id` = ID báo cáo gốc

Nhân viên xem task trên `tasks.tsx`. Mỗi task từ báo cáo hiển thị badge "Từ báo cáo" và link "Xem báo cáo gốc" để quay lại context đầy đủ.

---

## Ghi chú về trạng thái hiện tại

- Pipeline chính (Luồng 1-7) và toàn bộ 12 luồng chuẩn đang hoạt động trong production.
- HI-Loop Approval đã được triển khai đầy đủ (xem commit lịch sử gần nhất).
- Có 6 phòng ban: IT, CSKH, Vận hành, Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận.
- Accuracy định tuyến và cách đo trung thực: xem `docs/project/architecture/routing-taxonomy.md`.

---

## Luồng 1: Ingest & streaming realtime (`ingest.py`, `worker_ingest.py`)

`ingest.py` chứa hàm ghi feedback vào Supabase sau khi qua clean+classify. Thứ tự trong `ingest_feedback()`: gọi `clean.mask_pii()` trước, rồi `classifier.predict_feedback()`, rồi ghi kết quả vào bảng `feedback`.

`worker_ingest.py` (`ingest-worker`) chạy APScheduler bơm batch theo lịch:
- Biến env `LIVE_STREAM_ENABLED=true` kích hoạt tự động khi worker khởi động.
- `LIVE_STREAM_BATCH_SIZE` (mặc định 150 bản ghi/lô), `LIVE_STREAM_INTERVAL_SECONDS` (mặc định 5 giây).
- Nguồn dữ liệu: `data/processed/seed_real_clean.json` (4837 bản ghi).

`main.py` cũng cung cấp `POST /api/live-stream/start` để kích on-demand scheduler từ frontend. Hai endpoint bổ sung: `POST /api/run-real-pipeline` (một lô thủ công), `POST /api/trigger-spike-detect` (kích spike detect ngay).

---

## Luồng 4: Ma trận rủi ro 5 chiều (`agents/scoring_agent.py`, `worker_ml.py`)

`scoring_agent.score_feedback_batch()` gọi LLM chấm điểm mỗi feedback trên 5 chiều (thang 0-10):

| Chiều | Mô tả |
|-------|-------|
| `risk_safety` | Đe dọa tính mạng, tai nạn, quấy rối, đánh nhau |
| `risk_fraud` | Gian lận cước, lừa đảo, vòi vĩnh |
| `risk_attitude` | Thái độ tiêu cực của tài xế |
| `risk_vehicle` | Tình trạng xe không đạt chuẩn |
| `risk_compliance` | Vi phạm quy định, không tuân thủ SOP |

Sau khi có 5 điểm, `calculate_overall_risk()` chạy thuật toán Waterfall Max-Pooling:
- P5 nếu `risk_safety >= 8` (chỉ an toàn tính mạng lên P5).
- P4 nếu `risk_fraud >= 8` hoặc `risk_safety >= 5` hoặc `risk_attitude >= 8`.
- P3/P2/P1 theo ngưỡng còn lại.

`worker_ml.py` (`ml-worker`) quét định kỳ (mặc định 30 giây) các bản ghi có `overall_risk IS NULL` và `sentiment = 'negative'`, gọi `score_feedback_batch()` theo lô (mặc định 50 bản ghi/lô).

---

## Luồng 8: AI Chat + Tiered Hybrid RAG (`agent/chat_agent.py`, `agent/rag_engine.py`)

`run_chat_agent()` chạy vòng lặp ReAct (tối đa 5 lần) để LLM tự gọi công cụ trước khi trả lời. PII người dùng bị mask trước khi gọi LLM.

**Tiered RAG theo vai trò:**

| Tier | Người dùng | Knowledge base | Công cụ |
|------|-----------|----------------|---------|
| Internal | staff, manager, admin | `knowledge_base/` (SOP/SLA nội bộ) | Full tool set + `scope_team` filter |
| Public | ops staff gửi cờ `public_only` (widget trang chủ) | `public_kb/` (FAQ công khai) | `PUBLIC_TOOLS_DEFINITIONS` (giới hạn) |

`scope_team` ép tool chỉ truy vấn dữ liệu đúng phòng, tránh rò dữ liệu chéo phòng.

**Hybrid RAG trong `rag_engine.py`:**

1. Vector search: `CohereEmbeddingService` (model `embed-multilingual-v3.0`) + Supabase RPC `match_graph_nodes` (pgvector).
2. Keyword search: BM25-lite qua `agent/knowledge_base.search_knowledge()`.
3. Merge: Reciprocal Rank Fusion (k=60) cộng điểm từ cả hai danh sách rồi sort giảm dần.

Kết quả top-k đưa vào context LLM. Câu trả lời kèm trích dẫn `[Nguồn N]` liên kết về tài liệu gốc.

---

## Luồng 9: Human-in-the-Loop duyệt nhãn + correction log

Nhân viên vào trang `/feedback` để xử lý **Review Queue** (`needs_review=true`, `reviewed=false`):

- `PATCH /api/feedback/{id}/review`: đánh dấu đã duyệt (`reviewed=true`), bản ghi rời Queue.
- `PATCH /api/feedback/{id}/label`: sửa nhãn AI gán sai. Ghi vào `correction_logs` (ai sửa, field nào, giá trị cũ và mới), set `confidence=1.0`, `reviewed=true`.

`correction_logs` là audit trail và nguồn dữ liệu retrain tương lai. Admin có thể dùng `POST /api/feedback/reclassify` để phân loại lại data cũ với rule mới (bỏ qua bản đã có người duyệt).

Bản ghi vào Review Queue khi: `confidence < 0.55`, hoặc `severity = P5`, hoặc rule Safety kích hoạt.

---

## Luồng 11: RBAC 4 vai trò + scope phòng ban (`auth_guard.py`, `departments.py`)

4 vai trò: **admin**, **manager**, **staff**, **pending** (chờ cấp quyền). Khách hàng không có tài khoản; họ gửi phản hồi qua Customer web (`POST /api/public/feedback`).

| Vai trò | Quyền chính |
|---------|------------|
| admin | Toàn quyền: CRUD user, reclassify, xem mọi phòng |
| manager | Xem insights/báo cáo phòng mình, phê duyệt task, chat nội bộ |
| staff | Duyệt nhãn, xem feedback, chat nội bộ (scoped theo phòng) |
| pending | Không có quyền: 403 ở mọi endpoint trừ `GET /api/me`, `POST /api/me/password` và `/health` |

Backend dùng `SERVICE_ROLE_KEY` (bypass RLS Supabase). Gate quyền ở tầng API: decorator `require_admin`, `require_ops_staff` trong `auth_guard.py`. Bootstrap: profile đầu tiên của hệ thống tự nhận role admin; sau đó chỉ admin tạo tài khoản (`POST /api/admin/users`).

`departments.py` định nghĩa tuple `DEPARTMENTS` gồm 6 phòng ban chuẩn. Mọi code routing, ticket, report đều import từ đây.

---

## Luồng 12: Topology worker + API (`main.py`, `worker_*.py`)

5 service backend Railway:

| Service | File entrypoint | Công việc |
|---------|----------------|-----------|
| `backend` | `main.py` | FastAPI REST API + on-demand APScheduler |
| `ingest-worker` | `worker_ingest.py` | Live stream batch ingest |
| `backend-worker` | `worker_ticket.py` | Ticket workflow (open → in_progress → resolved) |
| `ml-worker` | `worker_ml.py` | Deep Risk Scoring 5 chiều cho feedback chưa chấm |
| `agent-worker` | `worker_agent.py` | Multi-agent orchestration (`run_agent_pipeline()`) |

`worker.py` là base class chia sẻ vòng lặp chờ và signal handling. Tất cả 5 service dùng chung source `pipeline/` qua `Dockerfile.workers` với biến `WORKER_MODULE` chọn entrypoint. Cách phân tách này tránh job định kỳ nặng (scoring, orchestration) cạnh tranh CPU với API request. Chi tiết deploy: `docs/project/deploy-railway.md`.
