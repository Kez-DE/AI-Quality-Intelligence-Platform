# Spec: 5000 synthetic reviews → 6 departments

Date: 2026-07-04
Status: approved (brainstorming)

## Goal

Sinh 5000 review tiếng Việt tổng hợp (đặt đồ ăn, thanh toán, sự cố app đặt xe),
phủ đủ **6 phòng ban**, một phần **chèn biển số xe + số điện thoại** trong text để
test PII-masking + `risk_vehicle`. Nạp vào bảng `feedback`, chạy `spike_detector`
để sinh alert mới trải đều 6 phòng. Commit generator + dataset lên `main`.

## Bối cảnh (đã xác minh trong code)

- `feedback` schema: `text` (bắt buộc), `topic`, `sentiment`, `severity`, `area`,
  `source`, `channel`, `risk_*`. KHÔNG có cột biển số/SĐT → PII nằm trong `text`.
- `ingest.py::ingest_dataset(json_path, defer_llm_scoring=...)` đọc **JSON array**
  các row dict; mỗi row qua `build_feedback_payload` (đọc `text/topic/sentiment/area/source`),
  ML gán severity, insert theo batch. Cần `SUPABASE_SERVICE_ROLE_KEY` + ≥1 profile (đã có).
- Routing (`data/taxonomy/routing_table.json`) topic→team:
  `App Issue→IT`, `Payment→Tài chính & Thanh toán`, `Pricing→Quản lý Rủi ro & Gian lận`,
  `Safety/Driver Behavior/Delay→Vận hành`, `Other→CSKH`, positive `Other/App Issue→Sản phẩm`.
- Local + Railway **dùng chung 1 cloud Supabase** → nạp 1 lần là live cả hai; "deploy
  Railway" cho task data là no-op, chỉ code (generator) mới đẩy lên main.

## Thành phần

### 1. `pipeline/scripts/generate_synthetic_reviews.py` (mới)

- Gọi `agent.model_router.chat_completion(..., response_json=True, temperature=0.9)`
  (bỏ qua `call_llm` vì nó ghim temp 0.1 + cache → trùng lặp).
- Sinh theo batch 25 review/lần; mỗi batch cố định `(topic, sentiment, theme, area)`,
  kèm seed batch để tránh cache và tăng đa dạng.
- **Phân bổ 5000 (tổng đúng 5000)** — đủ volume âm mỗi cụm để spike:
  | topic | sentiment | phòng | n |
  |---|---|---|---|
  | App Issue | negative | IT | 900 |
  | Payment | negative | Tài chính & Thanh toán | 850 |
  | Pricing | negative | Quản lý Rủi ro & Gian lận | 850 |
  | Safety | negative | Vận hành | 550 |
  | Driver Behavior | negative | Vận hành | 550 |
  | Delay | negative | Vận hành | 450 |
  | Other | negative | CSKH | 450 |
  | Other | positive | Sản phẩm (override) | 400 |
- **PII (~25–30%)**: sau khi có text, **chèn xác định** (không phụ thuộc LLM) biển số
  VN (`30A-123.45`) và/hoặc SĐT (`09xx xxx xxx`) cho tỉ lệ theo topic:
  Safety/Driver Behavior 0.6, Other/Delay 0.25, còn lại 0.1.
- 16 khu vực tái dùng từ data thật (HN/HCM/DN...).
- Xuất `data/processed/synthetic_reviews_5000.json`:
  `[{text, topic, sentiment, area, source:"synthetic"}]`.
- Concurrency nhỏ (thread pool ~8) + progress; chế độ `--count`/`--out`/`--smoke`.

### 2. Ingest

`ingest_dataset("data/processed/synthetic_reviews_5000.json", defer_llm_scoring=True)`
→ +5000 feedback với severity ML (nhanh, không chấm Deep-Risk từng dòng).

### 3. Spike → alerts

Chạy `spike_detector.detect_spikes(max_spikes=...)` đủ lượt để mỗi phòng có alert.
Dedup theo cụm (area,team,topic) có thể chặn cụm đã có alert open — cụm/area mới sẽ spike.

## Data flow

LLM → JSON → `feedback` (ML classify trong ingest) → `spike_detector` gom (area, topic→team)
→ `alerts` (open) → hiện trên board "Phân loại Ticket".

## Kiểm thử

- Unit (không LLM): mỗi row đủ field + topic hợp lệ; tổng phân bổ = 5000; row gắn PII
  khớp regex biển số/SĐT; sinh biển số/SĐT đúng định dạng.
- Verify chạy thật: đếm feedback +5000; alert xuất hiện đủ **6 phòng**; spot-check text
  chứa PII và `mask_pii` xử lý được; đối chiếu count trên Railway (shared DB).

## Rủi ro / YAGNI

- Không crawler thật, không cột DB mới, không CSV mirror, không chấm Deep-Risk từng dòng.
- Chi phí chính: ~200 call sinh review (batch). `defer_llm_scoring` tránh call/row.
- Idempotency: sinh 1 lần, ingest 1 lần (chạy lại sẽ nhân đôi — không tự chống trùng ở tầng DB).
