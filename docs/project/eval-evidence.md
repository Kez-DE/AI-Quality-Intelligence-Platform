# Eval Evidence — Gate G2 (MVP)

> **Cập nhật 2026-06-27** — Bổ sung bằng chứng e2e thật (pytest, eval router/model, health, pipeline smoke, frontend build).

## Bằng chứng e2e — 2026-06-27

**Ground truth đã xác minh từ code:**
- 6 phòng ban: IT, CSKH, Vận hành, Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận.
- Agent: 8 nghiệp vụ (*_agent.py) + Orchestrator + report_builder (helper).
- RAG hybrid: Cohere embed-multilingual-v3.0 + BM25-lite + RRF (k=60).
- 4 worker: ticket/ingest/ml/agent; API scheduler on-demand.

**Kết quả chạy:**
- pytest: **132 passed, 3 skipped, 2 xfailed, 0 failed** — exit code 0 (Python 3.14.6, pytest 9.1.0; chạy với `-p no:capture` do bug `ValueError: I/O operation on closed file` trong pytest capture layer trên Py3.14)
- route_eval (N=4837 seed_train_labeled): **topic accuracy 78.7%, dept accuracy 73.6%** — lệnh: `python -m eval.route_eval`
- evaluate_model (gold_dataset.json, N=40): **topic 92.5% (37/40), sentiment 100%, severity 100%** — lệnh: `python -m eval.evaluate_model eval/gold_dataset.json`
- /health: `{"status":"ok","message":"Backend service is running","version":"1.0.0","uptime_seconds":16297,"data_file_exists":true,"routing_taxonomy_loaded":true,"routing_routes":7,"llm_provider":"openrouter","llm_has_key":true}`
- pipeline smoke (5 bản ghi từ seed_demo_150.json): ingest→clean→classify chạy OK — module import OK; ví dụ record 1: `topic=Driver Behavior sentiment=negative severity=P3 conf=0.79`
- frontend build: **pass** — `npm run build` (bun không có trên CI host này); build hoàn thành trong 494ms, dist/server/assets/ tạo đủ

---

Bằng chứng đánh giá cho **user flow chính**: phản hồi thô → làm sạch PII → phân loại (model ML + rule engine) → gán topic/sentiment/severity/confidence + cờ `needs_review`.

> **Output thật, không mock.** Mọi kết quả dưới đây sinh trực tiếp từ pipeline phân loại của hệ thống (`clean.mask_pii` → `clean.clean_text` → `classifier.predict_feedback`, trong đó `predict_feedback` chạy model TF-IDF/LinearSVC `.joblib` rồi áp `rules.apply_rules`).

## Cách tái lập (reproduce)

```bash
cd pipeline
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
PYTHONIOENCODING=utf-8 python eval/manual_eval.py          # bảng người đọc
PYTHONIOENCODING=utf-8 python eval/manual_eval.py --json   # JSON
```

- Script: [`pipeline/eval/manual_eval.py`](../pipeline/eval/manual_eval.py)
- Model: `pipeline/ml/topic_model.joblib`, `pipeline/ml/sentiment_model.joblib`
- Ngày chạy: 2026-06-18 · Môi trường: Windows 11, Python 3.13, scikit-learn 1.6.1

---

## Tóm tắt kết quả

| # | Test case | Flow kiểm tra | Kỳ vọng | Output thật | Đạt |
|---|-----------|---------------|---------|-------------|:---:|
| TC-01 | Tài xế say xỉn gây tai nạn… | Safety override | Safety / negative / P5 / needs_review | `Safety / negative / P5 / needs_review=true` | ✅ |
| TC-02 | App bị lỗi không đặt được xe | Phân loại lỗi app | App Issue / negative | `App Issue / negative / P3 / conf 0.82` | ✅ |
| TC-03 | Tài xế thu tiền gấp đôi… | Gian lận thanh toán | Payment / negative | `Payment / negative / P3 / conf 0.75` | ✅ |
| TC-04 | Tài xế thân thiện, an toàn… | Phản hồi tích cực | positive / P1 / không cần duyệt | `Driver Behavior / positive / P1 / conf 0.88` | ✅ |
| TC-05 | Gọi xe mãi không có tài xế… | Thiếu cung / khó gọi xe | negative | `Other / negative / P3 / conf 0.662` | ✅ |
| TC-06 | SĐT 0912345678, email, biển số | PII masking | Ẩn SĐT + email + biển số | `[SĐT_ĐÃ_ẨN] [EMAIL_ĐÃ_ẨN] [BIỂN_SỐ_ĐÃ_ẨN]` | ✅ |

---

## Chi tiết từng test case

### TC-01 — Safety override (an toàn không nhường xác suất)

- **Input:** `Tài xế say xỉn gây tai nạn, xe tông vào người đi đường rồi bỏ chạy`
- **Output thật:**
  ```json
  {"topic": "Safety", "sentiment": "negative", "severity": "P5", "confidence": 0.55, "needs_review": true, "review_reason": "Từ khoá an toàn: 'tai nạn'"}
  ```
- **Nhận xét:** Rule Safety ghi đè model, ép `P5` + `needs_review=true`, kèm lý do để hiện badge trong Review Queue. Đúng thiết kế "rule luôn thắng model với tín hiệu nguy hiểm".

### TC-02 — Lỗi ứng dụng

- **Input:** `App bị lỗi không đặt được xe, bấm mãi không được`
- **Output thật:**
  ```json
  {"topic": "App Issue", "sentiment": "negative", "severity": "P3", "confidence": 0.82, "needs_review": false, "review_reason": null}
  ```
- **Nhận xét:** Bắt đúng topic `App Issue` với confidence cao (0.82), không đẩy vào hàng đợi duyệt vì tín hiệu rõ.

### TC-03 — Gian lận thanh toán

- **Input:** `Tài xế thu tiền gấp đôi, thu phí sai so với báo giá trên app`
- **Output thật:**
  ```json
  {"topic": "Payment", "sentiment": "negative", "severity": "P3", "confidence": 0.75, "needs_review": false, "review_reason": null}
  ```
- **Nhận xét:** Định tuyến đúng nhóm `Payment` để chuyển bộ phận xử lý phí/thanh toán.

### TC-04 — Phản hồi tích cực (negation/positive guard)

- **Input:** `Tài xế thân thiện, lái xe an toàn, rất hài lòng`
- **Output thật:**
  ```json
  {"topic": "Driver Behavior", "sentiment": "positive", "severity": "P1", "confidence": 0.88, "needs_review": false, "review_reason": null}
  ```
- **Nhận xét:** Dù có từ "an toàn" (gần nhóm Safety), hệ thống không kích Safety vì ngữ cảnh tích cực → gán `positive / P1`. Cho thấy rule phân biệt được khen ngợi với sự cố.

### TC-05 — Thiếu cung / khó gọi xe

- **Input:** `Gọi xe mãi không có tài xế nhận chuyến ở khu vực này`
- **Output thật:**
  ```json
  {"topic": "Other", "sentiment": "negative", "severity": "P3", "confidence": 0.662, "needs_review": false, "review_reason": null}
  ```
- **Nhận xét:** Bắt đúng sắc thái tiêu cực. Topic rơi về `Other` với confidence trung bình (0.662) — đây là vùng model còn yếu (câu mô tả gián tiếp). Ca này là ứng viên cho vòng Human-in-the-Loop để bổ sung nhãn `Supply`.

### TC-06 — PII masking trước khi phân loại

- **Input:** `Số điện thoại của tôi là 0912345678, email abc@gmail.com, xe biển 30A-12345`
- **Masked:** `Số điện thoại của tôi là [SĐT_ĐÃ_ẨN], email [EMAIL_ĐÃ_ẨN], xe biển [BIỂN_SỐ_ĐÃ_ẨN]`
- **Output thật (sau khi làm sạch):**
  ```json
  {"topic": "Other", "sentiment": "negative", "severity": "P3", "confidence": 0.657, "needs_review": false, "review_reason": null}
  ```
- **Nhận xét:** SĐT, email và biển số đều bị ẩn **trước** khi đưa vào model — dữ liệu cá nhân không lọt vào tầng phân loại/lưu trữ.

---

## Kết luận

6/6 test case cho output đúng kỳ vọng của user flow chính (làm sạch PII → phân loại → gán nhãn + cờ duyệt). Hệ thống chạy end-to-end với model ML thật + rule engine thật. TC-05 lộ rõ giới hạn đã biết của model ở câu mô tả gián tiếp — chính là lý do tồn tại vòng Human-in-the-Loop (`correction_logs`) và rule layer bù đắp.
