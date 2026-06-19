# AI Systems — xanhSM Quality Operation Cockpit

Tài liệu mô tả kiến trúc AI của dự án: các lớp AI, luồng dữ liệu, và cách chạy trong từng worker.

> Cập nhật: 2026-06-17

---

## Tổng quan

Hệ thống có **4 lớp AI** chạy trên dataset feedback gọi xe (lưu ở Supabase), vận hành bởi **1 web API + 4 background worker** (5 Railway service backend, cộng frontend là 6). Mọi lệnh gọi LLM đi qua **một cổng router duy nhất** có failover. Đổi provider/model chỉ cần sửa env var, không sửa code.

| Lớp | Thành phần | Loại |
|-----|-----------|------|
| A. Chat LLM (real-time) | `agent/model_router.py`, `/api/agent/chat` | LLM |
| B. Multi-agent pipeline (batch) | `agents/*` qua `orchestrator.py` | LLM + Rule + ML |
| C. ML models | `classifier.py` (TF-IDF + LinearSVC) | ML (sklearn) |
| D. Rule-based | `rules.py`, `spike_detector.py`, `ticket_workflow.py` | Rule |

---

## A. Chat LLM (real-time, đồng bộ)

### LLM Provider Router — `pipeline/agent/model_router.py`

Cổng gọi LLM **duy nhất** của toàn hệ thống. Có failover tự động + chế độ mock không bao giờ vỡ.

```
LLM_PROVIDER=auto  →  thử lần lượt provider CÓ KEY theo thứ tự:
   openrouter  →  openai  →  gemini  →  groq  →  mock
   + retry 3 lần (exponential backoff) khi gặp 429 / rate-limit
```

- **Input → Output:** `list[ChatMessage]` → `dict{content, provider, model, latency_ms, usage}`
- **Provider/model hiện tại:** `openrouter` / `deepseek/deepseek-v4-flash` (set qua env var trên Railway)
- Mỗi lần gọi ghi `logs/agent.log` (provider, model, latency, usage, failover)

### Endpoint chat — `POST /api/agent/chat` (`main.py`)

Có **2 cơ chế**, chia theo `guest` vs non-guest:

| Role | System prompt | Data context | Rate limit |
|------|--------------|-------------|------------|
| **guest** | `GUEST_SYSTEM_PROMPT` — chỉ hướng dẫn dùng app, KHÔNG lộ data nội bộ | ❌ | 20 req/giờ |
| **staff / manager / admin** | `AGENT_SYSTEM_PROMPT` | ✅ `build_agent_data_context()` | 100 req/giờ |

> Staff/manager/admin hiện dùng **chung một cơ chế chat** (cùng prompt, cùng data context, cùng rate limit). Backend chỉ phân biệt guest vs non-guest.

### Context builder — `services/agent_context.py` (RAG-lite, rule-based)

Đọc 300 feedback + 20 alert gần nhất từ Supabase, dùng `Counter` tổng hợp phân bố severity/sentiment/topic/area + alert status + live-stream state → render thành text block tiêm vào system prompt cho chat của staff.

---

## B. Multi-Agent Pipeline (batch)

Điều phối bởi `pipeline/agents/orchestrator.py` → `run_agent_pipeline(hours=24)`. Chạy trong `agent-worker` mỗi 300s. Orchestrator chỉ điều phối/retry/logging — không phải agent nghiệp vụ.

Helper chung (`agents/common.py`): `get_db()`, `call_llm()` (wrap router + cache MD5 + nuốt lỗi), `log_agent_run()`. Schema I/O định nghĩa bằng **Pydantic** (`agents/schemas.py`).

### Luồng 7 bước

```
Step 1   Lấy feedback P4/P5 trong N giờ → gom theo area
Step 2   alert_agent.process_area_alerts(area, fbs)          [RULE]  create / skip
Step 3   (nếu create) llm_agent.analyze_spike(area, texts)   [LLM]   title/desc/action
         router_agent.route_ticket(topic, severity)          [RULE]  team + SLA
Step 4   ticket_agent.create_or_update_ticket(...)           [DB]    insert alerts
Step 5   task_agent.cluster_alerts_into_tasks()              [RULE + 1 LLM/cụm mới]
Step 5.5 ticket_agent.get_overdue_tickets(24h)               [RULE]  quá SLA
Step 6   for team in TEAMS: insight_agent.generate(...)      [RULE]  metric theo phòng
Step 7   analyst_agent.analyze_root_cause(team, insights)    [LLM]   → department_reports
```

`TEAMS = [IT, Safety, CSKH, Vận hành, Pricing, Marketing]`

### Các agent

| Agent | Loại | Vai trò | Input → Output |
|-------|------|---------|----------------|
| `ingestion_agent` | ML + Rule | clean PII → classify → gán nhãn (fallback heuristic khi ML lỗi) | text → topic/sentiment/severity/confidence/needs_review |
| `alert_agent` | Rule | escalation WATCH≥3 / WARNING≥5 / CRITICAL≥10; P5→CRITICAL; dedup cooldown | (area, feedbacks) → create/skip + severity |
| `router_agent` | Rule | route ticket theo `routing_table.json`; P5/P0 ép về Safety | (topic, severity) → team + SLA |
| `ticket_agent` | DB | tạo/cập nhật ticket bảng `alerts`; quét overdue SLA | → ticket_id, action, status |
| `task_agent` | Rule + LLM | gom cụm alert `(team, area)` → task (LLM đặt title/summary) | alerts → tasks_created |
| `insight_agent` | Rule | tổng hợp metric feedback theo phòng | (team, hours) → severity dist + top topics |
| `analyst_agent` | **LLM** | phân tích root-cause + 3 action item (fallback khi lỗi) | (team, insights) → summary + risk_level + actions |
| `llm_agent` | **LLM** | phân tích spike khu vực → nguyên nhân gốc + action + team | (area, texts) → title/desc/action/team |
| `scoring_agent`* | LLM + Rule | chấm 5 chiều rủi ro (safety/fraud/attitude/vehicle/compliance 0-10) → waterfall max-pooling ra điểm 1-5 | feedback → overall_risk + 5 risk vector |

\* `scoring_agent` chạy chính trong `ml-worker`, không nằm trong `run_agent_pipeline`.

---

## C. ML Models (sklearn, offline-trained)

### `pipeline/classifier.py` — Classifier

- 2 model `joblib`: `ml/topic_model.joblib` + `ml/sentiment_model.joblib`, đều là **TF-IDF + LinearSVC** Pipeline
- **Input → Output:** `text` → `{topic, sentiment, severity P1-P5, confidence, needs_review}`
- LinearSVC không có `predict_proba` → ước lượng confidence từ margin `decision_function`
- **Sau ML luôn chạy `rules.py`** ghi đè khi keyword rõ; `apply_safety_rules` ép Safety/P5
- Fallback khi model chưa load: topic=Other, neutral, P3, conf 0.3

### `pipeline/ml/train_sentiment.py` — Training (offline)

sklearn `Pipeline(TfidfVectorizer(ngram 1-2, max_features=30000, sublinear_tf) + LinearSVC(C=1, class_weight=balanced))`. Ghi ra `sentiment_model.NEW.joblib` (không tự ghi đè — swap thủ công).

---

## D. Rule-based Components

- **`rules.py`** — lớp rule chính sau ML. Ưu tiên Safety > PaymentFraud > App > Map > Payment > Supply > DriverNeg > Pricing > Delay > Positive. Có **negation guard tiếng Việt** (`không/ko/chẳng`), gibberish detector, set `needs_review` khi confidence < 0.55 hoặc P5 hoặc safety override.
- **`spike_detector.py`** — `SPIKE_THRESHOLD=5`: area ≥5 phàn nàn P4/P5 → spike → gọi `analyze_spike` (LLM). Cần `SUPABASE_SERVICE_ROLE_KEY` (bypass RLS).
- **`scoring_agent.calculate_overall_risk()`** — waterfall max-pooling 5 chiều → thang 1-5.
- **`services/ticket_workflow.py`** — vòng đời ticket theo thời gian: open → in_progress (10s) → resolved (30s).
- **`services/live_stream.py`** — scheduler nạp dataset theo batch, cứ N batch chạy auto spike detection.

---

## E. Workers (1 web API + 4 worker)

Tất cả dùng APScheduler + signal handling.

| Worker file | Railway service | Chạy gì | Chu kỳ | Tốn LLM? |
|-------------|-----------------|---------|--------|----------|
| `worker_ingest.py` | `ingest-worker` | `start_live_stream` (nạp dataset batch + auto spike) | 10s/batch | gián tiếp |
| `worker_ml.py` | `ml-worker` | quét feedback `overall_risk IS NULL & negative` → `score_feedback_batch` | 30-60s, batch 50 | ✅ LLM |
| `worker_agent.py` | `agent-worker` | `run_agent_pipeline(24h)` — full multi-agent | 300s; tắt bằng `WORKER_AGENT_ENABLED=false` | ✅ LLM |
| `worker_ticket.py` | `backend-worker` | `advance_ticket_workflow` | 5s | Rule |
| `main.py` (backend) | `backend` | API + chat + scheduler on-demand | — | ✅ chat |

> Chỉ `agent-worker` và `ml-worker` tốn LLM cost — đều có cờ tắt / fallback mock.

---

## Sơ đồ luồng dữ liệu

```
dataset ─ingest-worker→ ingest_dataset → feedback
                              │
                              ▼ (ingestion path)
              clean PII → classifier.py [ML: TF-IDF+LinearSVC] → rules.py [RULE + negation]
                              │                                   → topic / sentiment / severity / needs_review
                              │
   ml-worker:   feedback(overall_risk NULL, neg) → scoring_agent [LLM 5-dim] → calculate_overall_risk [RULE waterfall]
                              │
   agent-worker (300s) ── run_agent_pipeline ──────────────────────────────────────────────────────────
        P4/P5 → alert_agent[RULE] ─create→ llm_agent.analyze_spike[LLM] + router_agent[RULE] → ticket_agent[DB]→alerts
                          │
                   task_agent[RULE cụm + LLM title] → tasks
                   insight_agent[RULE agg] → analyst_agent[LLM root-cause] → department_reports
   ticket-worker (5s):  ticket_workflow[RULE time]  open → in_progress → resolved

CHAT (sync, /api/agent/chat):
   guest → GUEST_SYSTEM_PROMPT ─┐
   staff → AGENT_SYSTEM_PROMPT + agent_context.build_agent_data_context()[RULE aggregate]
                                └→ chat_completion → model_router [LLM failover]

★ MỌI LLM call → pipeline/agent/model_router.py
   (1 cổng duy nhất · failover openrouter→openai→gemini→groq→mock · retry · logs/agent.log)
```

---

## Điểm chốt

1. **Một LLM router duy nhất** (`model_router.py`) — đổi provider/model qua env var, không sửa code. Trên Railway phải set var cho từng service: `backend`, `ml-worker`, `agent-worker` (xem `deploy-railway.md`).
2. **ML chỉ ở `classifier.py`** — 2 model sklearn, luôn bị `rules.py` ghi đè khi keyword rõ.
3. **Phân loại agent:** LLM = analyst, scoring (chấm), task (title), spike. Rule = alert, router, insight, ingestion-fallback, ticket-workflow, scoring-waterfall.
4. **Chỉ `agent-worker` + `ml-worker` tốn LLM cost** — đều có cờ tắt / fallback mock.
