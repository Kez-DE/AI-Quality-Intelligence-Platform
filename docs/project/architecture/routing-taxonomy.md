# Taxonomy định tuyến phản hồi

Tài liệu này mô tả cách hệ thống phân loại phản hồi khách hàng thành topic, rồi quyết định phòng ban nào tiếp nhận. Mọi con số dưới đây đến từ dữ liệu thực, không phải ước tính.

Spec liên quan: `docs/superpowers/specs/2026-06-25-router-accuracy-design.md`.

---

## 4 phòng ban và phạm vi xử lý

| Phòng | Phạm vi |
|-------|---------|
| **Vận hành** | Sự cố an toàn, tai nạn, hành vi tài xế, chậm trễ, thiếu cuốc, điều phối. Đây là đội phản ứng nhanh -- mọi ticket P5 đều đến đây trước. |
| **IT** | Lỗi ứng dụng, sự cố bản đồ/GPS, crash, lag, đăng nhập. |
| **CSKH** | Thanh toán, hoàn tiền, khiếu nại giá cước, phản hồi chung chưa phân loại được. |
| **Marketing** | Phản hồi tích cực chung (topic "Other" + sentiment positive) -- tín hiệu thương hiệu để khai thác truyền thông, không phải khiếu nại. |

Không có phòng ban thứ 5. Bảng routing chỉ định nghĩa 4 phòng này.

---

## Bảng topic -> phòng ban

Sao chép trực tiếp từ `data/taxonomy/routing_table.json`:

| Topic | Phòng | SLA (giờ) | Priority mặc định | Lý do |
|-------|-------|-----------|-------------------|-------|
| Safety | Vận hành | 1 | P5 | Sự cố an toàn, tai nạn, đe doạ -- cần phản ứng tại hiện trường, ưu tiên tính mạng. |
| Driver Behavior | Vận hành | 8 | P3 | Hành vi và thái độ tài xế, điều phối cung cầu. |
| App Issue | IT | 12 | P3 | Lỗi ứng dụng, bản đồ, sự cố kỹ thuật. |
| Payment | CSKH | 12 | P3 | Thanh toán, hoàn tiền -- CSKH hỗ trợ khách trực tiếp. |
| Pricing | CSKH | 12 | P3 | Giá cước, voucher, trừ tiền không rõ lý do -- CSKH hỗ trợ, phối hợp IT khi có lỗi kỹ thuật. |
| Delay | Vận hành | 8 | P3 | Chậm trễ, thiếu cuốc, khu vực nóng. |
| Other | CSKH | 24 | P4 | Phản hồi chung chưa phân loại rõ. |

**Default (không khớp topic nào):** CSKH.

---

## Quy tắc override

Override chạy trước topic match. Thứ tự ưu tiên:

### 1. Severity override: P5 -> Vận hành

Bất kỳ ticket nào có severity P5, bất kể topic hay sentiment, đều về Vận hành với SLA 1 giờ. Đây là quy tắc thắng tất cả, được kích hoạt sớm nhất trong `route_ticket()`.

P5 thường đến từ rule Safety trong `rules.py` (xem bên dưới), nhưng về lý thuyết bất kỳ đường nào sinh ra P5 cũng sẽ bị override này bắt.

### 2. Sentiment override: positive + Other -> Marketing

Chỉ áp dụng khi hai điều kiện cùng đúng:
- sentiment = "positive"
- topic = "Other" (topic phải có trong danh sách `["Other"]` khai báo trong `routing_table.json`)

Phản hồi positive về App Issue, Payment, hay Driver Behavior không khớp điều kiện trên, nên vẫn route theo topic về đúng phòng chuyên môn. Đây là thiết kế có chủ ý -- khen ngợi ứng dụng vẫn là tín hiệu cho IT, khen tài xế vẫn là tín hiệu cho Vận hành.

### 3. Topic match

Tra bảng routes theo topic. Deterministic, không có xác suất.

### 4. Default

CSKH nếu topic không khớp bất kỳ route nào.

---

## Ánh xạ rule trong `rules.py` -> topic

Các rule trong `apply_rules()` chạy theo thứ tự ưu tiên từ cao đến thấp. Mỗi rule ghi đè kết quả của model ML khi keyword khớp.

| Nhóm keyword | Topic được gán | Severity | Ghi chú |
|---|---|---|---|
| `SAFETY_KEYWORDS` | Safety | P5 | Ưu tiên cao nhất. Safety equipment keyword (dây an toàn, ghế trẻ em...) không có negation guard -- "không thắt dây" vẫn là Safety. Các keyword khác có negation guard (window 16 ký tự). |
| `DRIVER_POSITIVE_KEYWORDS` | Driver Behavior | P1 | Chạy trước Driver tiêu cực. Có negation guard. |
| `DRIVER_NEGATIVE_KEYWORDS` + `DRIVER_SUBJECT_KEYWORDS` | Driver Behavior | P4 | Rule 2b: chủ ngữ tài xế rõ + tín hiệu tiêu cực. Chạy sớm để tránh App/Payment cướp nhầm. |
| `PAYMENT_FRAUD_KEYWORDS` | Payment | P4 | Gian lận, mất tiền, lừa đảo. |
| `APP_KEYWORDS` | App Issue | P3 | Crash, lag, đơ, lỗi app. |
| `MAP_KEYWORDS` | App Issue | P3 | GPS, bản đồ sai, Google Maps -- không có topic Map riêng, gộp vào App Issue. |
| `PAYMENT_KEYWORDS` | Payment | P3 | Thanh toán thông thường (không phải gian lận). |
| `SUPPLY_KEYWORDS` | Delay | P3 | Tài xế thiếu cuốc -> Vận hành điều phối. |
| `DRIVER_NEGATIVE_KEYWORDS` (không có chủ ngữ) | Driver Behavior | P4 | Rule 7: fallback khi không có chủ ngữ tài xế rõ. |
| `LOST_ITEM_KEYWORDS` | Other | P3 | Để quên đồ, hỗ trợ CSKH. Chạy trước Delay vì hay kèm "chờ mãi gọi tổng đài". |
| `VEHICLE_CONDITION_KEYWORDS` | Other | P3 | Điều hoà, xe bẩn, mùi hôi. |
| `PRICING_KEYWORDS` | Pricing | P3 | Giá đắt, phụ phí, giá ảo. |
| `DELAY_KEYWORDS` | Delay | P3 | Chờ lâu, đến muộn, chưa tới. |
| `NEUTRAL_KEYWORDS` / `POSITIVE_KEYWORDS` / `NEGATIVE_KEYWORDS` | (giữ topic model) | P2/P1/P3 | Chỉ điều chỉnh sentiment + severity, không đổi topic. |

Nếu không có keyword nào khớp, topic giữ nguyên kết quả từ model ML.

---

## Accuracy định tuyến: số trung thực

### Tại sao không dùng full golden set

Sau lần retrain model (TF-IDF + LinearSVC), model đã học trên 80% golden set (`seed_train_labeled.json`). Chạy `python -m eval.route_eval` trên toàn bộ golden set sẽ cho con số cao hơn thực tế vì model đã thấy hầu hết dữ liệu đó trong lúc train. Con số đó bị inflate và không phản ánh khả năng tổng quát hóa.

### Holdout accuracy (con số trung thực)

`eval/splits.py` tách deterministic 20% holdout (`HOLDOUT_FRAC = 0.2`, `SEED = 42`) -- phần này không bao giờ được dùng để train. Đây là số trung thực:

| Metric | Giá trị |
|--------|---------|
| Topic accuracy (holdout) | 75.0% |
| **Dept accuracy (holdout)** | **75.4%** |
| Baseline trước khi cải tiến | ~68% |
| Mục tiêu tiếp theo | 80% |

### Cách chạy lại

```bash
cd pipeline && .venv/bin/python -c "
from eval.splits import golden_split
from eval.route_eval import evaluate
r = evaluate(golden_split()[1])
print('holdout topic', round(r['topic_accuracy'], 4), 'dept', round(r['dept_accuracy'], 4))
"
```

### Hạn chế đã biết: IT-overload

Phân phối topic trong golden set có số lượng "App Issue" lớn hơn thực tế so với phân phối thực của phản hồi khách hàng. Hậu quả: model và rule layer có xu hướng gán App Issue nhiều hơn mức cần, đẩy ticket về IT nhiều hơn cần thiết. Đây là lý do dept accuracy khó vượt 80% mà không điều chỉnh cân bằng training data. Khi có thêm dữ liệu thực, cần re-evaluate phân phối topic trước khi retrain.
