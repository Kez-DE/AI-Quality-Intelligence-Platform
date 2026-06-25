# Thiết kế: Sửa định tuyến phòng ban + Eval harness + Dọn tài liệu

> Spec — AI Quality Intelligence Platform (greenSM). Ngày 2026-06-25.
> Hướng đã duyệt: **A — Rules-first + eval gate + chỉnh map + docs.**

## 1. Bài toán

Router định tuyến ticket về sai phòng ban. Đo trên golden set `data/train/seed_train_labeled.json` (4.837 mẫu có nhãn `topic`):

- **Độ chính xác topic: 67.2%**
- **Độ chính xác phòng ban: 67.3%** — cứ 3 ticket thì 1 sai phòng.

Méo tải trọng (triệu chứng người dùng thấy):

| Phòng | Tải đúng | Tải thực tế | Lệch |
|---|---|---|---|
| IT | 1053 | 1676 | **+59% quá tải** |
| Vận hành | 1494 | 700 | **−53% bị bỏ đói** |
| CSKH | 1733 | 1752 | ~đúng |
| Marketing | 557 | 709 | +27% |

Thủ phạm chính (đo được, top confusions):

| Số ca | Misroute topic | Hệ quả phòng ban |
|---|---|---|
| 324 | Driver Behavior → App Issue | Vận hành → IT |
| 280 | Driver Behavior → Other | Vận hành → CSKH |
| 207 | Other → App Issue | CSKH → IT |
| 135 | Driver Behavior → Payment | Vận hành → CSKH |
| 114 | Delay → App Issue | Vận hành → IT |
| 111 | Payment → App Issue | CSKH → IT |

Gộp lại: **441 ca "Vận hành → IT"** và **351 ca "Vận hành → CSKH"** sai.

## 2. Nguyên nhân gốc

Định tuyến gồm 3 tầng; router_agent là tầng deterministic cuối, không phải nguồn lỗi:

```
text → classifier.predict_feedback() → rules.apply_rules() → topic
     → spike_detector → route_ticket(topic, severity, sentiment)
     → router_agent → routing_table.json → team
```

Lỗi nằm ở **tầng phân loại topic** (`pipeline/rules.py` + model ML), cụ thể:

1. **Thứ tự ưu tiên rule sai.** `apply_rules` chạy `App Issue` (bước 3) và `Payment` (bước 5) TRƯỚC `Driver Behavior` (bước 7). Phàn nàn tài xế có lẫn từ "lag/đơ/lỗi/phí" bị App/Payment cướp mất → rời khỏi Vận hành. Đây là gốc của 324 + 135 ca.
2. **Độ phủ Driver Behavior thiếu.** 280 ca model đoán `Other`, rule tài xế không bắt được → trôi về CSKH.
3. **Supply & tình trạng xe gán nhầm `Other`.** "Tài xế thiếu cuốc", "xe bẩn", "điều hoà hỏng" là việc Vận hành nhưng rule hiện đặt topic `Other` → routing về CSKH.
4. **Trần model ML.** Một phần lỗi đến từ `topic_model.joblib`. Tầng rule là đòn bẩy nhanh nhất; retrain là phương án dự phòng có điều kiện.

## 3. Phạm vi

- Giữ **4 phòng ban**: `IT`, `CSKH`, `Vận hành`, `Marketing`. Không mở rộng 6 phòng (để spec sau).
- Sửa **cả hai tầng**: phân loại topic (`rules.py`) và bảng map (`routing_table.json`).
- Xây **eval harness** làm cổng chặn regression.
- **Dọn tài liệu** toàn diện (toàn quyền sửa/xoá .md sai), viết bằng văn phong tự nhiên (skill humanizer).

Ngoài phạm vi: mở rộng 4→6 phòng ban, báo cáo tổng hợp chéo phòng (Global Report), thay router bằng LLM.

## 4. Thành phần & thiết kế

### 4.1 Eval harness (mới)

**File:** `pipeline/eval/route_eval.py`, `pipeline/eval/__init__.py`

Một module độc lập, đo được, tái lập:

- Đọc golden set, chạy `predict_feedback` → `route_ticket` cho từng mẫu.
- Tính: accuracy topic, accuracy phòng ban; precision/recall theo từng topic; confusion matrix topic và phòng ban; phân bố tải gold vs predicted.
- `python -m eval.route_eval` in báo cáo dạng bảng; cờ `--json` xuất số liệu cho CI.
- Hàm thuần `evaluate(samples) -> dict` để test gọi trực tiếp (không phụ thuộc in ấn).

**Interface:**
- `evaluate(samples: list[dict]) -> dict` trả `{topic_accuracy, dept_accuracy, topic_confusion, dept_confusion, gold_dept_dist, pred_dept_dist}`.
- `load_golden(path=None) -> list[dict]` mặc định đọc `data/train/seed_train_labeled.json`.

### 4.2 Pytest gate (mới)

**File:** `pipeline/tests/test_routing_accuracy.py`

- Khẳng định `dept_accuracy >= NGƯỠNG`. Baseline đo được 0.673; **mục tiêu ≥ 0.80**. Đặt hằng `TARGET_DEPT_ACCURACY = 0.80`.
- Khẳng định không ô misroute đơn lẻ nào (gold→pred, gold≠pred) vượt **150 ca** (chặn lại lỗi Driver Behavior→App Issue khổng lồ).
- Khẳng định không phòng nào lệch tải > **35%** so với tải đúng (chặn méo tải IT/Vận hành).
- Chạy trên toàn golden set (≈2.5s, chấp nhận được).

Test này là HỢP ĐỒNG: mọi thay đổi rule/map phải đẩy số liệu qua ngưỡng và giữ qua ngưỡng.

### 4.3 Sửa phân loại — `pipeline/rules.py`

Nguyên tắc: thay đổi nhỏ, từng bước, mỗi bước đo delta bằng `route_eval`. Không "đại tu" rule một lần.

1. **Nâng ưu tiên Driver Behavior tiêu cực** lên trước App Issue/Payment khi tín hiệu tài xế rõ. Cách an toàn: thêm guard "nếu có cụm chủ ngữ tài xế (`tài xế`, `bác tài`, `lái xe`) đi kèm tín hiệu tiêu cực thì giữ Driver Behavior, không để App/Payment cướp". Tránh phá case 'app lỗi' thuần.
2. **Mở rộng `DRIVER_NEGATIVE_KEYWORDS`** phủ các biến thể đang rơi vào `Other` (đối chiếu từ confusion matrix 280 ca Driver→Other; trích cụm phổ biến từ chính các mẫu sai).
3. **Supply & tình trạng xe → topic route sang Vận hành.** Đổi nhãn rule supply (`SUPPLY_KEYWORDS`) và `VEHICLE_CONDITION_KEYWORDS` từ `Other` sang một topic định tuyến tới Vận hành (ví dụ `Driver Behavior` hoặc `Delay` — chọn theo ngữ nghĩa điều phối, xác nhận bằng eval).
4. Giữ nguyên Safety-first và mọi negation guard hiện có.

Tiêu chí dừng: `dept_accuracy ≥ 0.80` và méo tải IT/Vận hành ≤ 35%. Nếu rule chạm trần dưới ngưỡng → kích hoạt 4.6 (retrain).

### 4.4 Rà bảng map — `data/taxonomy/routing_table.json`

- Giữ đúng 4 phòng; đối chiếu từng dòng route với nhãn gold (gold dept = map của gold topic) để bảng không tự mâu thuẫn.
- Xem lại Marketing (chỉ nhận positive+Other — kiểm tra có nên mở thêm tín hiệu thương hiệu) và ranh giới Payment (khiếu nại hoàn tiền → CSKH; lỗi xuất hoá đơn kỹ thuật → App Issue→IT qua rule).
- Mọi chỉnh sửa bảng đo lại bằng eval; không đổi nếu làm tụt accuracy.

### 4.5 Dọn artifact gây nhiễu

- **Xoá** `data/auxiliary/data2/taxonomy/routing_table.json` — bảng cũ dùng 6 tên phòng tiếng Việt ("Quản lý đối tác tài xế", "Chính sách giá"...) mâu thuẫn với chuẩn 4 phòng, gây nhiễu khi đọc. Xác nhận không file code nào import trước khi xoá.

### 4.6 Retrain ML (tuỳ chọn, có điều kiện)

CHỈ thực hiện nếu sau 4.3 + 4.4 mà `dept_accuracy < 0.80`:
- Retrain `topic_model.joblib` trên 4.837 mẫu, cân bằng lớp, đo bằng cùng eval harness, chia train/holdout để tránh overfit.
- Chỉ thay artifact nếu holdout accuracy tăng thật.

### 4.7 Tài liệu — `docs/`

Viết bằng văn phong tự nhiên (humanizer). Toàn quyền sửa/xoá .md sai.

1. **Doc luồng E2E chuẩn** (`docs/project/architecture/` hoặc `docs/project/`): Feedback → phân loại (classifier+rules) → định tuyến (router_agent) → ticket (spike_detector) → task → báo cáo → **HI-Loop approval** (đã triển khai). Mô tả đúng trạng thái hiện tại, kèm sơ đồ.
2. **Doc taxonomy định tuyến**: 4 phòng, bảng topic→phòng, rule override (Safety, P5, positive sentiment), kèm lý do từng quyết định map.
3. **Audit .md hiện có** (`README.md`, `JOURNAL.md`, `WORKLOG.md`, `IMPLEMENTATION_PLAN.md`, `AGENTS.md`): liệt kê chỗ lỗi thời/mâu thuẫn, hợp nhất hoặc xoá. `IMPLEMENTATION_PLAN.md` mục 9 (mở rộng 6 phòng) giữ làm "future direction", đánh dấu rõ là chưa triển khai.

## 5. Lát cắt triển khai (vertical slices)

| # | Lát cắt | File chính | Phụ thuộc |
|---|---|---|---|
| 1 | Eval harness `evaluate()` + `load_golden()` | `pipeline/eval/route_eval.py` | — |
| 2 | Pytest gate ghi baseline + ngưỡng | `pipeline/tests/test_routing_accuracy.py` | 1 |
| 3 | Sửa rules: ưu tiên + phủ Driver Behavior | `pipeline/rules.py` | 1 |
| 4 | Sửa rules: supply/xe → Vận hành | `pipeline/rules.py` | 1, 3 |
| 5 | Rà `routing_table.json` + xoá artifact data2 | `data/taxonomy/...`, xoá data2 | 1 |
| 6 | (Điều kiện) retrain model | `pipeline/ml/...` | 1–5 |
| 7 | Doc luồng E2E + taxonomy (humanizer) | `docs/...` | 3–5 |
| 8 | Audit + dọn .md | `*.md` | 7 |
| 9 | Verify: eval qua ngưỡng + `pytest -q` toàn bộ | — | tất cả |

Mỗi lát 3, 4, 5 đo delta accuracy trước/sau; chỉ giữ thay đổi nếu số liệu cải thiện hoặc giữ nguyên (không bao giờ tụt).

## 6. Rủi ro & giảm thiểu

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Nâng ưu tiên Driver Behavior làm tụt accuracy App Issue | Trung bình | Guard theo chủ ngữ tài xế; đo delta từng bước, rollback nếu tụt |
| Golden set lệch phân bố so với production | Trung bình | Eval là tương đối (so baseline); không tuyên bố tuyệt đối |
| Overfit khi mở rộng keyword theo đúng mẫu sai | Trung bình | Giữ ngưỡng và kiểm tra méo tải, không chỉ accuracy |
| Xoá file .md/artifact còn được dùng | Cao | Grep import/tham chiếu trước khi xoá; commit tách biệt dễ revert |
| Retrain model phá rule layer | Trung bình | Chỉ retrain nếu cần; đo bằng cùng harness, có holdout |

## 7. Tiêu chí hoàn thành

- [ ] `python -m eval.route_eval` chạy được, in báo cáo accuracy + confusion + tải.
- [ ] `dept_accuracy ≥ 0.80` (từ baseline 0.673).
- [ ] Không ô misroute đơn lẻ > 150 ca; không phòng nào lệch tải > 35%.
- [ ] `cd pipeline && python -m pytest tests/ -q` pass toàn bộ (gồm gate mới, không regression).
- [ ] Artifact `data2/taxonomy/routing_table.json` đã xoá, không vỡ import.
- [ ] Doc luồng E2E + taxonomy tồn tại, mô tả đúng hiện trạng; .md cũ đã audit/dọn.
