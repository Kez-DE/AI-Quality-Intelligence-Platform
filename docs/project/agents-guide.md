# Hệ thống Agent — Hướng dẫn kiến trúc & vận hành

AI Quality Intelligence Platform có hai lớp agent tách biệt:

- **`pipeline/agents/`** — các agent nghiệp vụ chạy theo batch, điều phối bởi `orchestrator.py`. Tài liệu này mô tả lớp đó.
- **`pipeline/agent/`** — chat agent ReAct + RAG cho giao diện chat. Xem [rbac-departments.md](rbac-departments.md) phần chat.

Lớp `agents/` gồm 8 agent nghiệp vụ + 1 orchestrator. Orchestrator không phải agent: nó chỉ điều phối thứ tự, retry và logging.

---

## Hai agent chạy độc lập (ngoài orchestrator)

Hai agent này không nằm trong `run_agent_pipeline`, mà chạy ở luồng ingest và worker riêng:

| Agent | File | Chạy ở đâu | Vai trò |
|-------|------|-----------|---------|
| `ingestion_agent` | `ingestion_agent.py` | luồng ingest dataset | Clean PII, normalize area, classify topic/sentiment/severity, ghi bảng `feedback` |
| `scoring_agent` | `scoring_agent.py` | `ml-worker` | Chấm 5 chiều rủi ro (safety/fraud/attitude/vehicle/compliance, 0-10) bằng LLM, rồi waterfall max-pooling ra điểm `overall_risk` 1-5 |

`ingestion_agent` nhận `IngestionInput(text, channel, area, source, user_id)`, làm sạch và phân loại (fallback heuristic + safety keyword khi ML lỗi), ghi vào bảng `feedback`. `scoring_agent` quét các feedback `overall_risk IS NULL AND sentiment='negative'`, chấm rủi ro và cập nhật ngược lại.

---

## Pipeline điều phối — `orchestrator.run_agent_pipeline(hours=24)`

Chạy trong `agent-worker` mỗi `WORKER_AGENT_INTERVAL_SECONDS` (mặc định 300s). Thứ tự thực thi đã trace từ code:

```
Step 1-4  spike_detector gom theo (area, topic, team), áp ngưỡng risk/volume,
          Router Agent quyết định team/SLA/priority và LLM chỉ sinh title/desc/action.
Step 5    task_agent.cluster_alerts_into_tasks()               [RULE + LLM/cụm mới]
Step 5.5  ticket_agent.get_overdue_tickets(sla_hours=24)       [RULE]  → ticket quá hạn
Step 6-7  for team in TEAMS:
            insight_agent.generate_department_insights(team)   [RULE]  → metric theo phòng
            nếu total_feedback > 0 và analyst bật:
              analyst_agent.analyze_root_cause(team, insights) [LLM]   → root cause + actions
              upsert vào department_reports
```

`TEAMS = [IT, CSKH, Vận hành, Marketing]`.

Một chi tiết dễ nhầm: `insight_agent` bên trong tự gọi `router_agent.route_ticket` cho từng feedback để lọc đúng phòng, nên `router_agent` được dùng ở cả Step 3 lẫn Step 6.

Helper chung trong `agents/common.py`: `get_db()` (Supabase client singleton), `call_llm()` (wrap model_router + cache LRU + nuốt lỗi), `log_agent_run()` (ghi file JSONL + insert bảng `agent_run_logs`). Schema I/O định nghĩa bằng Pydantic trong `agents/schemas.py`.

---

## Chi tiết từng agent trong pipeline

### alert_agent — phân cấp cảnh báo

Đọc ngưỡng từ `data/taxonomy/severity_rules.json` (fallback: WATCH ≥3, WARNING ≥5, CRITICAL ≥10, cooldown 60 phút). Quy tắc `classify_alert_severity(case_count, has_p5)`: có P5 → CRITICAL; nếu không thì so `case_count` với ngưỡng giảm dần; dưới WATCH → INFO. Dedup `is_duplicate_alert` đọc bảng `alerts` (status=open, cùng area, trong cooldown). Đọc bảng `alerts`, không ghi.

### router_agent — định tuyến phòng ban

`route_ticket(topic, severity, sentiment=None)` đọc `data/taxonomy/routing_table.json`. Thứ tự ưu tiên:

1. `severity_overrides`: P5 → Vận hành (thắng tất cả).
2. `sentiment_overrides`: positive → Marketing.
3. `routes`: match theo topic.
4. `default_team`: CSKH.

Bảng route thật:

| Topic | Team | SLA | Priority |
|-------|------|----:|----------|
| Safety | Vận hành | 1h | P5 |
| Driver Behavior | Vận hành | 8h | P3 |
| App Issue | IT | 12h | P3 |
| Payment | CSKH | 12h | P3 |
| Pricing | CSKH | 12h | P3 |
| Delay | Vận hành | 8h | P3 |
| Other | CSKH | 24h | P4 |

Override: P5 → Vận hành (1h); sentiment positive → Marketing (48h). Agent chỉ đọc JSON, đổi routing không cần sửa code.

### ticket_agent — tạo ticket

`create_or_update_ticket(...)` ghi `assigned_team`, `topic`, `priority`, `ticket_type`, `routing_source`, `sla_due_at` vào bảng `alerts`. Markdown metadata chỉ được giữ để ticket cũ tương thích. Thiếu `user_id` thì lấy một id từ bảng `profiles`.

### task_agent — gom alert thành task

`cluster_alerts_into_tasks()` đọc bảng `alerts` (task_id null, status open), gom theo `(assigned_team, area)`; ticket cũ fallback parse Markdown. Mỗi cụm: tìm task open cùng team/area, chưa có thì gọi LLM sinh title/summary rồi INSERT với `source='agent'`. Ngoài đường này, bảng `tasks` còn nhận task `source='report'` (kèm `report_id`) khi manager duyệt báo cáo qua RPC `approve_report_and_dispatch`.

### insight_agent — tổng hợp metric theo phòng

`generate_department_insights(team, hours)` đọc bảng `feedback` (limit 2000), lọc theo team bằng cách chạy `route_ticket` từng feedback, tính `severity_distribution` (CRITICAL/WARNING/WATCH/INFO), top topics, và 3 recent samples. Chỉ đọc, không ghi.

### analyst_agent — phân tích root cause

`analyze_root_cause(team, insights)` lấy recent samples, build system prompt theo persona phòng ban, gọi LLM trả JSON `{root_cause_summary, risk_level, action_items}`. Fallback `_fallback_analysis` dùng `fallback_actions` của persona khi LLM lỗi. Agent không tự ghi DB; orchestrator mới upsert kết quả vào `department_reports`, trong đó `action_items` được lưu thành cột `suggested_tasks` (JSONB) và `root_cause_summary` lưu thành cột riêng — đây là dữ liệu manager biên tập rồi duyệt thành task ở luồng HI-Loop Approval (xem `co_che.md` mục 8).

Persona theo phòng ban hardcode trong dict `DEPARTMENT_PERSONAS` ngay trong `analyst_agent.py` (không đọc file/DB ngoài). Mỗi key (Safety, Pricing, IT, CSKH, Vận hành, Marketing) có persona, priorities (chèn vào system prompt) và `fallback_actions`. Phòng không có trong dict thì dùng persona rỗng + action generic.

### llm_agent — phân tích spike

Nằm ngoài `agents/` (module `pipeline/llm_agent.py`). `analyze_spike(area, texts)` gửi review của vùng spike cho LLM, trả về title, mô tả, action và team gợi ý. Được orchestrator gọi ở Step 3 khi alert_agent quyết định create.

---

## Cờ env bật/tắt

Orchestrator dùng `_agent_enabled(name)` đọc `AGENT_{NAME}_ENABLED` (mặc định True):

| Cờ | Tắt thì sao |
|----|-------------|
| `AGENT_ALERT_ENABLED` | Bỏ Step 1-4 (alert + ticket) |
| `AGENT_TASK_ENABLED` | Bỏ Step 5 (gom task) |
| `AGENT_INSIGHT_ENABLED` | Bỏ cả Step 6-7 (insight + analyst) |
| `AGENT_ANALYST_ENABLED` | Vẫn chạy insight nhưng bỏ phần root-cause LLM |

Cấp worker: `WORKER_AGENT_ENABLED` (false thì worker không chạy pipeline, tiết kiệm LLM cost mà không cần redeploy), `WORKER_AGENT_INTERVAL_SECONDS` (300), `WORKER_AGENT_HOURS` (24).

---

## Bảng Supabase mỗi agent dùng

| Bảng | Ai ghi | Ai đọc |
|------|--------|--------|
| `feedback` | ingestion_agent | orchestrator, insight_agent, scoring_agent |
| `alerts` | ticket_agent | alert_agent (dedup), task_agent (gán task_id) |
| `tasks` | task_agent (`source=agent`), RPC approve_report_and_dispatch (`source=report`) | task_agent, API tasks |
| `department_reports` | orchestrator (upsert content + root_cause_summary + suggested_tasks), API draft-tasks/approve | API reports |
| `profiles` | — | ticket_agent (lấy user_id mặc định) |
| `agent_run_logs` | mọi agent qua `common.log_agent_run` | API stats, System Health |

---

## Nguyên tắc thiết kế

| Nguyên tắc | Giải thích |
|-----------|-----------|
| Hybrid fast/slow | ML classify toàn bộ data (rẻ, cost 0); LLM chỉ dùng cho root-cause, spike, task title |
| Config-driven | Routing và threshold nằm trong JSON, đổi không cần sửa code |
| Graceful degradation | Mọi agent có fallback khi LLM lỗi hoặc thiếu key |
| Tiết kiệm quota | Analyst chỉ chạy cho phòng có feedback |
| Idempotent | Ticket dedup tránh tạo trùng khi scheduler chạy lại |
| Audit trail | Mọi agent run ghi log: agent_name, input_hash, status, latency |

---

## Chạy test

```bash
cd pipeline

# Test từng agent riêng
python -m agents.alert_agent
python -m agents.router_agent
python -m agents.ticket_agent
python -m agents.insight_agent
python -m agents.analyst_agent

# Test pipeline đầy đủ
python -m agents.orchestrator
```

Test qua API (cần backend chạy + token admin):

```bash
# Chạy full pipeline
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/agent/run?hours=24"

# Insight 1 phòng ban kèm phân tích
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/insights/departments/Safety?with_analysis=true"
```

---

## Thêm hoặc sửa agent

1. Tạo file mới trong `pipeline/agents/`.
2. Implement function chính + fallback.
3. Import vào `orchestrator.py`, thêm vào đúng Step trong `run_agent_pipeline`.
4. Thêm endpoint trong `main.py` nếu cần expose API.
5. Cập nhật `co_che.md` (cơ chế tổng thể) và tài liệu này.
