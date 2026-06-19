# Hệ thống 6 Agent — Hướng dẫn kiến trúc & vận hành

> Trái tim của AI Quality Intelligence Platform: 6 agent chuyên trách + 1 orchestrator điều phối.

---

## Tổng quan kiến trúc

```
Feedback mới vào hệ thống
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  Agent 1: Ingestion/Classifier Agent                │
│  Clean PII → ML classify → Rule override → Ingest  │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│  Agent 2: Router Agent                              │
│  Định tuyến ticket về phòng ban (routing_table.json)│
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│  Agent 3: Ticket Agent                              │
│  Tạo/cập nhật ticket, dedup, gán SLA + priority    │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│  Agent 4: Insight Agent                             │
│  Tổng hợp metric theo phòng ban (trend, severity)  │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│  Agent 5: Analyst Agent                             │
│  LLM phân tích root cause + dự báo + 3 action items│
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│  Agent 6: Alert/Escalation Agent                    │
│  Phân cấp WATCH/WARNING/CRITICAL + dedup cooldown  │
└─────────────────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │  Orchestrator (không    │
        │  tính là agent nghiệp   │
        │  vụ — chỉ điều phối)    │
        └─────────────────────────┘
```

---

## Chi tiết từng Agent

### Agent 1: Ingestion/Classifier Agent

**File:** `pipeline/agents/ingestion_agent.py`

**Nhiệm vụ:**

- Nhận feedback thô (text + channel + area)
- Clean PII: mask SĐT → `[SĐT]`, email → `[EMAIL]`
- Phân loại ML: TF-IDF + LinearSVC → topic (7 lớp) + sentiment
- Rule engine ghi đè khi keyword rõ (Safety override, negation guard)
- Tính confidence band thực tế (không còn 95% cứng)
- Đánh dấu `needs_review` cho P5/safety/confidence thấp

**Input:**

```python
{
    "text": "Tài xế say xỉn lái xe nguy hiểm",
    "channel": "app",
    "area": "HN-Cau-Giay"
}
```

**Output:**

```python
{
    "status": "success",
    "text_cleaned": "Tài xế say xỉn lái xe nguy hiểm",
    "topic": "Safety",
    "sentiment": "negative",
    "severity": "P5",
    "confidence": 0.45,
    "needs_review": True,
    "review_reason": "safety_keyword"
}
```

**Fallback:** Nếu model file không tồn tại → dùng rule-only mode (keyword matching).

---

### Agent 2: Router Agent

**File:** `pipeline/agents/router_agent.py`

**Nhiệm vụ:**

- Đọc `data/taxonomy/routing_table.json`
- Map topic → phòng ban + SLA
- P5/P0 luôn override → Safety (SLA 1h)
- Thay đổi routing chỉ cần sửa JSON, không sửa code

**Input:**

```python
route_ticket(topic="App Issue", severity="P3")
```

**Output:**

```python
{
    "team": "IT",
    "sla_hours": 24,
    "routed_by": "router_agent (Topic Match)",
    "is_override": False
}
```

**Config:** `data/taxonomy/routing_table.json`

```json
{
    "routes": [
        {"topic": "App Issue", "team": "IT", "sla_hours": 24},
        {"topic": "Safety", "team": "Safety", "sla_hours": 1},
        {"topic": "Driver", "team": "Vận hành", "sla_hours": 12}
    ],
    "default_team": "CSKH",
    "severity_overrides": [
        {"severity": "P5", "team": "Safety", "sla_hours": 1}
    ]
}
```

---

### Agent 3: Ticket Agent

**File:** `pipeline/agents/ticket_agent.py`

**Nhiệm vụ:**

- Tạo ticket mới hoặc cập nhật ticket cũ (dedup)
- Dedup key: `area + topic + severity` trong cooldown 60 phút
- Gán priority scoring: severity × case_count × has_p5
- State machine: `open → triaged → in_progress → resolved → closed`
- Gán SLA (due_at) theo routing output

**Input:**

```python
create_or_update_ticket(
    area="HN-Cau-Giay",
    topic="Safety",
    severity="CRITICAL",
    title="Spike an toàn khu vực Cầu Giấy",
    description="3 ca P5 trong 1h...",
    team="Safety",
    sla_hours=1,
    case_count=5,
    has_p5=True
)
```

**Output:**

```python
{
    "action": "created",  # hoặc "updated" nếu dedup
    "ticket_id": "uuid-...",
    "priority_score": 25,
    "due_at": "2026-06-16T15:00:00Z"
}
```

**Fallback:** Nếu DB lỗi → ghi log và trả `{"action": "failed", "reason": "..."}`.

---

### Agent 4: Insight Agent

**File:** `pipeline/agents/insight_agent.py`

**Nhiệm vụ:**

- Tổng hợp metric theo phòng ban trong N giờ qua
- Phân bố severity (CRITICAL/WARNING/WATCH/INFO)
- Top topics + count
- Trend so kỳ trước (nếu có data)
- Sample feedback gần nhất (3 mẫu)

**Input:**

```python
generate_department_insights(team="Safety", hours=24)
```

**Output:**

```python
{
    "team": "Safety",
    "period_hours": 24,
    "total_feedback": 42,
    "severity_distribution": {"CRITICAL": 8, "WARNING": 12, "WATCH": 15, "INFO": 7},
    "top_topics": [{"topic": "Safety", "count": 30}, ...],
    "recent_samples": [{"id": "...", "text": "...", "area": "..."}]
}
```

---

### Agent 5: Analyst Agent

**File:** `pipeline/agents/analyst_agent.py`

**Nhiệm vụ:**

- Nhận insight từ Agent 4
- Gọi LLM phân tích root cause xuyên suốt nhiều ticket
- Đánh giá risk level: LOW / MEDIUM / HIGH / CRITICAL
- Dự báo 24-48h
- Đề xuất 3 action items có deadline

**Output (LLM):**

```json
{
    "root_cause_summary": "Nhiều tài xế khu vực Cầu Giấy vi phạm quy trình an toàn sau ca đêm",
    "risk_level": "HIGH",
    "action_items": [
        {"action": "Rà soát lịch trình ca đêm khu vực Cầu Giấy", "deadline": "24h"},
        {"action": "Tăng cường giám sát realtime cho tài xế có lịch sử vi phạm", "deadline": "48h"},
        {"action": "Cập nhật quy trình onboarding về an toàn", "deadline": "1w"}
    ]
}
```

**Fallback:** Khi không có LLM key → trả heuristic analysis dựa trên top topic + severity count.

---

### Agent 6: Alert/Escalation Agent

**File:** `pipeline/agents/alert_agent.py`

**Nhiệm vụ:**

- Nhận danh sách feedback P4/P5 theo khu vực
- Phân cấp cảnh báo:
  - 🟡 WATCH: ≥3 case tiêu cực
  - 🟠 WARNING: ≥5 case
  - 🔴 CRITICAL: ≥10 case HOẶC có P5
- Dedup: khu vực đã có alert `open` trong 60 phút → không tạo mới
- Ngưỡng cấu hình qua `data/taxonomy/severity_rules.json`

**Config:** `data/taxonomy/severity_rules.json`

```json
{
    "alert_escalation": {
        "WATCH": {"min_negative": 3},
        "WARNING": {"min_negative": 5},
        "CRITICAL": {"min_negative": 10}
    },
    "alert_cooldown_minutes": 60
}
```

---

### Orchestrator

**File:** `pipeline/agents/orchestrator.py`

**VAI TRÒ:** Không phải agent nghiệp vụ. Chỉ điều phối pipeline, retry, logging, schedule.

**Luồng 7 bước:**

1. Quét feedback P4/P5 trong N giờ → nhóm theo area
2. Alert Agent: phân cấp cảnh báo từng khu vực
3. Ticket Agent: tạo/cập nhật ticket cho area vượt ngưỡng
4. Router Agent: xác nhận phòng ban + SLA
5. Ghi alert vào Supabase
6. Insight Agent: tổng hợp metric tất cả phòng ban
7. Analyst Agent: root-cause cho phòng có rủi ro

**Kích hoạt:**

- Tự động: APScheduler mỗi 10 phút
- Thủ công: `POST /api/agent/run?hours=24` (admin only)

---

## Nguyên tắc thiết kế


| Nguyên tắc               | Giải thích                                                                 |
| ------------------------ | -------------------------------------------------------------------------- |
| **Hybrid Fast/Slow**     | ML classify 100% data (Fast, cost=0), LLM chỉ cho root-cause/report (Slow) |
| **Config-driven**        | Routing + threshold nằm trong JSON, đổi không cần sửa code                 |
| **Graceful degradation** | Mọi agent có fallback khi LLM lỗi/thiếu key                                |
| **Tiết kiệm quota**      | Analyst chỉ chạy cho phòng CÓ feedback tiêu cực                            |
| **Idempotent**           | Ticket dedup tránh tạo trùng khi scheduler chạy lại                        |
| **Audit trail**          | Mọi agent run ghi log: agent_name, input_hash, status, latency             |


---

## Chạy test

### Test từng agent riêng lẻ

```bash
cd pipeline

# Test Ingestion Agent
python -m agents.ingestion_agent

# Test Router Agent
python -m agents.router_agent

# Test Ticket Agent
python -m agents.ticket_agent

# Test Insight Agent
python -m agents.insight_agent

# Test Analyst Agent (cần LLM key hoặc sẽ dùng fallback)
python -m agents.analyst_agent

# Test Alert Agent
python -m agents.alert_agent
```

### Test pipeline đầy đủ

```bash
cd pipeline
python -m agents.orchestrator
```

### Test qua API (cần backend đang chạy + token admin)

```bash
# Chạy full pipeline
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/agent/run?hours=24"

# Insight 1 phòng ban
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/insights/departments/Safety?with_analysis=true"

# Insight tất cả phòng ban
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/insights/departments?hours=24"
```

---

## Thêm/sửa agent

1. Tạo file mới trong `pipeline/agents/`
2. Implement function chính + fallback
3. Import vào `orchestrator.py` và thêm vào pipeline
4. Thêm endpoint trong `main.py` nếu cần expose API
5. Cập nhật `MASTER_BLUEPRINT.md`

