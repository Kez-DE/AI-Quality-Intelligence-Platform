# Luồng xử lý phản hồi đầu cuối (E2E)

Tài liệu này mô tả đúng hiện trạng của hệ thống. Các chặng dưới đây phản ánh code thực đang chạy, không phải thiết kế mục tiêu.

Spec định tuyến liên quan: `docs/superpowers/specs/2026-06-25-router-accuracy-design.md`.

---

## Sơ đồ tổng quan

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

`cluster_alerts_into_tasks()` gom alert theo (team, area). Nếu đã có Task open cùng cặp đó, nó gán alert vào Task hiện có. Nếu chưa có, tạo Task mới và gọi LLM một lần để sinh title/summary. Kết quả ghi vào bảng `tasks`.

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

- Tất cả 6 chặng trên đang hoạt động trong production.
- HI-Loop Approval đã được triển khai đầy đủ (xem commit lịch sử gần nhất).
- Có 6 phòng ban: IT, CSKH, Vận hành, Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận.
- Accuracy định tuyến và cách đo trung thực: xem `docs/project/architecture/routing-taxonomy.md`.
