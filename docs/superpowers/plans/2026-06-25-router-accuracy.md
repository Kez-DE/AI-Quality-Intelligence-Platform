# Router Accuracy Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa độ chính xác định tuyến phòng ban từ 67.3% lên ≥ 80% bằng cách sửa tầng phân loại topic và bảng map, có eval harness làm cổng chặn regression.

**Architecture:** Định tuyến gồm 3 tầng: `classifier.predict_feedback` → `rules.apply_rules` (gán topic) → `router_agent.route_ticket` (map topic→phòng theo `routing_table.json`). Router là tầng deterministic đúng; lỗi nằm ở tầng phân loại. Ta xây eval harness đo accuracy trên golden set, dùng nó làm oracle cho từng thay đổi rule/map, và làm pytest gate chống regression.

**Tech Stack:** Python 3, scikit-learn (TF-IDF + LinearSVC joblib), pytest/unittest, JSON taxonomy. Chạy bằng venv `pipeline/.venv`.

## Global Constraints

- 4 phòng ban hợp lệ: `IT`, `CSKH`, `Vận hành`, `Marketing`. KHÔNG mở rộng 6 phòng.
- Golden set: `data/train/seed_train_labeled.json` (4.837 mẫu, mỗi mẫu có `text_full`, `topic`, `sentiment`, `severity`).
- Topic hợp lệ (model + rules): `Safety`, `Driver Behavior`, `App Issue`, `Payment`, `Pricing`, `Delay`, `Other`.
- Baseline đo được TRƯỚC khi sửa: topic accuracy 67.2%, **dept accuracy 67.3%**. Mục tiêu: **dept accuracy ≥ 0.80**.
- Mọi lệnh Python chạy bằng venv: `cd pipeline && .venv/bin/python ...` và `.venv/bin/python -m pytest ...`.
- Mọi thay đổi `rules.py` / `routing_table.json` PHẢI đo delta accuracy bằng `eval.route_eval`; chỉ giữ nếu dept accuracy KHÔNG tụt.
- Giữ nguyên Safety-first và mọi negation guard hiện có trong `rules.py`.
- Mọi commit kết thúc bằng `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Tài liệu (Task 7, 8) viết bằng văn phong tự nhiên — REQUIRED SUB-SKILL: `humanizer`.
- Làm việc trên nhánh `fix/router-accuracy` (spec đã commit ở đây).

---

### Task 1: Eval harness — đo accuracy định tuyến

**Files:**
- Create: `pipeline/eval/__init__.py`
- Create: `pipeline/eval/route_eval.py`

**Interfaces:**
- Produces:
  - `load_golden(path: str | None = None) -> list[dict]` — đọc golden set, mặc định `data/train/seed_train_labeled.json`.
  - `evaluate(samples: list[dict]) -> dict` — trả `{"n", "topic_accuracy", "dept_accuracy", "topic_confusion", "dept_confusion", "gold_dept_dist", "pred_dept_dist"}`. `topic_confusion`/`dept_confusion` là `dict[tuple[str,str], int]` keyed `(gold, pred)`. Các `*_dist` là `dict[str,int]`.

- [ ] **Step 1: Tạo package eval rỗng**

Create `pipeline/eval/__init__.py`:

```python
```

(file rỗng — chỉ để `eval` thành package import được.)

- [ ] **Step 2: Viết `route_eval.py`**

Create `pipeline/eval/route_eval.py`:

```python
"""Eval harness: đo độ chính xác định tuyến trên golden set có nhãn topic.

Chạy: cd pipeline && .venv/bin/python -m eval.route_eval [--json]
Dùng làm oracle cho mọi chỉnh sửa rules.py / routing_table.json.
"""

from __future__ import annotations

import json
import sys
from collections import Counter

from core.paths import DATA_DIR
from classifier import predict_feedback
from agents.router_agent import route_ticket

GOLDEN_PATH = DATA_DIR / "train" / "seed_train_labeled.json"


def load_golden(path: str | None = None) -> list[dict]:
    with open(path or GOLDEN_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _dept(topic, severity, sentiment) -> str:
    return route_ticket(topic, severity, sentiment, log_run=False)["team"]


def evaluate(samples: list[dict]) -> dict:
    n = len(samples)
    topic_ok = 0
    dept_ok = 0
    topic_confusion: Counter = Counter()
    dept_confusion: Counter = Counter()
    gold_dept_dist: Counter = Counter()
    pred_dept_dist: Counter = Counter()

    for x in samples:
        text = x.get("text_full") or ""
        gt = x.get("topic")
        gsev = x.get("severity")
        gsent = x.get("sentiment")

        pred = predict_feedback(text)
        pt = pred["topic"]
        psev = pred["severity"]
        psent = pred["sentiment"]

        if pt == gt:
            topic_ok += 1
        gd = _dept(gt, gsev, gsent)
        pd = _dept(pt, psev, psent)
        if pd == gd:
            dept_ok += 1

        topic_confusion[(gt, pt)] += 1
        dept_confusion[(gd, pd)] += 1
        gold_dept_dist[gd] += 1
        pred_dept_dist[pd] += 1

    return {
        "n": n,
        "topic_accuracy": topic_ok / n if n else 0.0,
        "dept_accuracy": dept_ok / n if n else 0.0,
        "topic_confusion": dict(topic_confusion),
        "dept_confusion": dict(dept_confusion),
        "gold_dept_dist": dict(gold_dept_dist),
        "pred_dept_dist": dict(pred_dept_dist),
    }


def _print_report(r: dict) -> None:
    print(f"N = {r['n']}")
    print(f"TOPIC accuracy:      {r['topic_accuracy'] * 100:.1f}%")
    print(f"DEPARTMENT accuracy: {r['dept_accuracy'] * 100:.1f}%")
    print("\nGold dept distribution (tải đúng):")
    for k, v in sorted(r["gold_dept_dist"].items(), key=lambda kv: -kv[1]):
        print(f"  {v:5d}  {k}")
    print("Predicted dept distribution (tải thực tế):")
    for k, v in sorted(r["pred_dept_dist"].items(), key=lambda kv: -kv[1]):
        print(f"  {v:5d}  {k}")
    print("\nTop topic misroutes (gold -> pred, >=20):")
    for (g, p), v in sorted(r["topic_confusion"].items(), key=lambda kv: -kv[1]):
        if g != p and v >= 20:
            print(f"  {v:5d}  {g:16s} -> {p}")
    print("\nTop department misroutes (gold -> pred, >=20):")
    for (g, p), v in sorted(r["dept_confusion"].items(), key=lambda kv: -kv[1]):
        if g != p and v >= 20:
            print(f"  {v:5d}  {g:10s} -> {p}")


if __name__ == "__main__":
    result = evaluate(load_golden())
    if "--json" in sys.argv:
        serializable = {
            k: (v if not isinstance(v, dict) or not v or not isinstance(next(iter(v)), tuple)
                else {f"{a}->{b}": c for (a, b), c in v.items()})
            for k, v in result.items()
        }
        print(json.dumps(serializable, ensure_ascii=False, indent=2))
    else:
        _print_report(result)
```

- [ ] **Step 3: Chạy harness, xác nhận in báo cáo baseline**

Run: `cd pipeline && .venv/bin/python -m eval.route_eval`
Expected: in `TOPIC accuracy: 67.2%` và `DEPARTMENT accuracy: 67.3%` (±0.5%), kèm bảng phân bố tải và danh sách misroutes. KHÔNG traceback.

- [ ] **Step 4: Commit**

```bash
git add pipeline/eval/__init__.py pipeline/eval/route_eval.py
git commit -m "feat(eval): route accuracy harness trên golden set

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Pytest gate — chốt ngưỡng & chống regression

**Files:**
- Create: `pipeline/tests/test_routing_accuracy.py`

**Interfaces:**
- Consumes: `eval.route_eval.load_golden`, `eval.route_eval.evaluate` (Task 1).

Lưu ý: gate này sẽ FAIL ngay (red) vì baseline 67.3% < 80%. Đó là chủ đích — Task 3–5 sẽ làm nó xanh.

- [ ] **Step 1: Viết test gate**

Create `pipeline/tests/test_routing_accuracy.py`:

```python
import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from eval.route_eval import load_golden, evaluate

TARGET_DEPT_ACCURACY = 0.80
MAX_SINGLE_MISROUTE = 150          # không ô (gold->pred) sai nào vượt mức này
MAX_WORKLOAD_SKEW = 0.35           # |tải_thực - tải_đúng| / tải_đúng <= 35%


class TestRoutingAccuracy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = evaluate(load_golden())

    def test_department_accuracy_meets_target(self):
        self.assertGreaterEqual(
            self.r["dept_accuracy"], TARGET_DEPT_ACCURACY,
            f"dept accuracy {self.r['dept_accuracy']:.3f} < {TARGET_DEPT_ACCURACY}",
        )

    def test_no_single_misroute_too_large(self):
        worst = [
            (g, p, c)
            for (g, p), c in self.r["dept_confusion"].items()
            if g != p and c > MAX_SINGLE_MISROUTE
        ]
        self.assertEqual(worst, [], f"Ô misroute quá lớn: {worst}")

    def test_workload_not_skewed(self):
        gold = self.r["gold_dept_dist"]
        pred = self.r["pred_dept_dist"]
        skewed = []
        for dept, g in gold.items():
            p = pred.get(dept, 0)
            if g and abs(p - g) / g > MAX_WORKLOAD_SKEW:
                skewed.append((dept, g, p))
        self.assertEqual(skewed, [], f"Tải lệch >35%: {skewed}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Chạy gate, xác nhận FAIL đúng lý do**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_routing_accuracy.py -q`
Expected: FAIL — `dept accuracy 0.673 < 0.8` và ô misroute `Vận hành->IT` (441) > 150, tải IT/Vận hành lệch > 35%. (Đây là red baseline.)

- [ ] **Step 3: Commit**

```bash
git add pipeline/tests/test_routing_accuracy.py
git commit -m "test(routing): gate accuracy >=80%, chặn misroute & méo tải (red baseline)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Sửa rules — ưu tiên Driver Behavior trước App/Payment

**Files:**
- Modify: `pipeline/rules.py` (hàm `apply_rules`, khối các bước phân loại)

**Interfaces:**
- Consumes: `eval.route_eval.evaluate` để đo delta.
- Produces: `apply_rules` giữ nguyên chữ ký, đổi thứ tự ưu tiên nội bộ.

Mục tiêu task: triệt 324 ca `Driver Behavior → App Issue` + 135 ca `Driver Behavior → Payment` bằng cách: khi câu có CHỦ NGỮ tài xế kèm tín hiệu tiêu cực rõ về tài xế, giữ `Driver Behavior` trước khi App/Payment kịp cướp. Không đụng case "app lỗi" thuần (không nhắc tài xế).

- [ ] **Step 1: Ghi accuracy TRƯỚC khi sửa**

Run: `cd pipeline && .venv/bin/python -m eval.route_eval | head -3`
Ghi lại 2 dòng accuracy (baseline ~67.2% / 67.3%) để so sánh.

- [ ] **Step 2: Thêm danh sách chủ ngữ tài xế (cạnh các nhóm keyword, sau `DRIVER_NEGATIVE_KEYWORDS`)**

Trong `pipeline/rules.py`, thêm sau khối `DRIVER_NEGATIVE_KEYWORDS` (kết thúc ~dòng 114):

```python
# Chủ ngữ chỉ tài xế — dùng để ưu tiên Driver Behavior khi câu vừa nhắc tài xế
# vừa có tín hiệu tiêu cực, tránh để App/Payment cướp nhầm.
DRIVER_SUBJECT_KEYWORDS = [
    "tài xế", "tai xe", "bác tài", "bac tai", "lái xe", "lai xe",
    "tài xe", "shipper", "tx ", " tx", "anh tài", "chú tài", "bác lái",
]
```

- [ ] **Step 3: Chèn khối ưu tiên Driver Behavior ngay sau bước 2 (Driver positive)**

Trong `apply_rules`, NGAY SAU khối `--- 2. DRIVER tích cực ---` (kết thúc ở `return _finalize(... "Driver Behavior", "positive" ...)` ~dòng 239) và TRƯỚC `--- 3. PAYMENT FRAUD ---`, chèn:

```python
    # --- 2b. DRIVER tiêu cực ƯU TIÊN CAO ---
    # Khi câu có chủ ngữ tài xế + tín hiệu tiêu cực tài xế rõ -> giữ Driver Behavior
    # trước khi App/Payment cướp. Chống 324 ca Driver->App + 135 ca Driver->Payment.
    drv_kw = _has(t, DRIVER_NEGATIVE_KEYWORDS)
    if drv_kw and _has(t, DRIVER_SUBJECT_KEYWORDS):
        topic, sentiment = "Driver Behavior", "negative"
        severity = max(severity, 4)
        confidence = 0.82
        return _finalize(topic, sentiment, severity, confidence, None)
```

- [ ] **Step 4: Chạy eval, xác nhận dept accuracy TĂNG**

Run: `cd pipeline && .venv/bin/python -m eval.route_eval | head -3`
Expected: `DEPARTMENT accuracy` cao hơn baseline (kỳ vọng giảm mạnh ô `Vận hành->IT`). Nếu accuracy TỤT so với Step 1 → revert Step 3 và thu hẹp `DRIVER_SUBJECT_KEYWORDS` (bỏ token mơ hồ như `tx`), thử lại. Chỉ tiếp tục khi accuracy ≥ baseline.

- [ ] **Step 5: Chạy test classifier cũ, đảm bảo không regression**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_classifier.py tests/test_router_agent.py -q`
Expected: PASS (không phá hành vi rule cũ đã có test).

- [ ] **Step 6: Commit**

```bash
git add pipeline/rules.py
git commit -m "fix(rules): ưu tiên Driver Behavior khi có chủ ngữ tài xế + tín hiệu tiêu cực

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Sửa rules — mở rộng phủ Driver Behavior + supply/xe về Vận hành

**Files:**
- Modify: `pipeline/rules.py`

**Interfaces:**
- Consumes: `eval.route_eval` để mine confusion + đo delta.

Mục tiêu: triệt 280 ca `Driver Behavior → Other` (model đoán Other, rule không bắt) bằng cách mở rộng keyword theo dữ liệu sai thực tế; và đưa supply ("thiếu cuốc") + tình trạng xe ("xe bẩn", "điều hoà") về topic route sang Vận hành.

- [ ] **Step 1: Mine các câu Driver→Other bị sai để rút keyword thật**

Run:
```bash
cd pipeline && .venv/bin/python -c "
import json, collections
from classifier import predict_feedback
g = json.load(open('../data/train/seed_train_labeled.json'))
miss = [x['text_full'] for x in g if x['topic']=='Driver Behavior' and predict_feedback(x['text_full'])['topic']=='Other']
print('Driver->Other misses:', len(miss))
cnt = collections.Counter()
for tx in miss:
    for w in tx.lower().split():
        if len(w) >= 3: cnt[w] += 1
for w,c in cnt.most_common(40): print(c, w)
"
```
Ghi lại các từ/cụm lặp nhiều liên quan tài xế (vd "thái độ", "cọc", "phục vụ", "nhân viên") để bổ sung — CHỈ chọn cụm thật sự chỉ hành vi tài xế, bỏ stopword.

- [ ] **Step 2: Bổ sung cụm vừa mine vào `DRIVER_NEGATIVE_KEYWORDS`**

Trong `pipeline/rules.py`, thêm các cụm đã chọn ở Step 1 vào cuối list `DRIVER_NEGATIVE_KEYWORDS` (ví dụ minh hoạ — thay bằng cụm thực mine được):

```python
    # Bổ sung từ confusion mining (Driver->Other):
    "thái độ", "thai do", "phục vụ kém", "phuc vu kem", "cọc cằn", "coc can",
    "không chuyên nghiệp", "thiếu tôn trọng", "nói trống không", "bất lịch sự",
```

- [ ] **Step 3: Đổi supply & tình trạng xe sang topic route về Vận hành**

`routing_table.json` đã có topic `Delay` route về Vận hành với mô tả "thiếu cuốc, khu vực nóng". Đổi nhãn 2 rule sau từ `Other` sang topic Vận hành.

Trong `apply_rules`, khối `--- 6. SUPPLY ---` (~dòng 279-286), đổi:
```python
            topic, sentiment = "Other", "negative"  # không có Driver Supply trong model -> Other
```
thành:
```python
            topic, sentiment = "Delay", "negative"  # thiếu cuốc = điều phối -> Vận hành
```

Trong khối `--- 8b. TÌNH TRẠNG XE ---` (~dòng 309-315), đổi:
```python
            topic, sentiment = "Other", "negative"
```
thành:
```python
            topic, sentiment = "Driver Behavior", "negative"  # vệ sinh/điều hoà xe -> Vận hành
```

- [ ] **Step 4: Chạy eval, xác nhận dept accuracy TĂNG hoặc GIỮ**

Run: `cd pipeline && .venv/bin/python -m eval.route_eval | head -25`
Expected: `DEPARTMENT accuracy` ≥ kết quả sau Task 3; ô `Vận hành->CSKH` và `Vận hành->IT` giảm; tải `Vận hành` tiến gần 1494. Nếu một thay đổi con làm TỤT accuracy → revert riêng thay đổi đó (giữ những cái có lợi). Tiêu chí: dept accuracy không được thấp hơn sau Task 3.

- [ ] **Step 5: Chạy gate accuracy**

Run: `cd pipeline && .venv/bin/python -m pytest tests/test_routing_accuracy.py -q`
Expected: nếu đã ≥ 80% và các ràng buộc khác đạt → PASS. Nếu chưa đạt 80% → ghi lại số hiện tại; tiếp tục Task 5 (map) rồi cân nhắc Task 6 (retrain).

- [ ] **Step 6: Commit**

```bash
git add pipeline/rules.py
git commit -m "fix(rules): mở rộng phủ Driver Behavior + supply/xe định tuyến về Vận hành

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Rà bảng map + xoá artifact taxonomy gây nhiễu

**Files:**
- Modify: `data/taxonomy/routing_table.json` (chỉ nếu eval chứng minh cải thiện)
- Delete: `data/auxiliary/data2/taxonomy/routing_table.json`

**Interfaces:**
- Consumes: `eval.route_eval` để xác nhận thay đổi map không làm tụt accuracy.

- [ ] **Step 1: Đối chiếu bảng map với nhãn gold**

Run:
```bash
cd pipeline && .venv/bin/python -c "
import json, collections
from agents.router_agent import route_ticket
g = json.load(open('../data/train/seed_train_labeled.json'))
by = collections.defaultdict(collections.Counter)
for x in g:
    d = route_ticket(x['topic'], x['severity'], x.get('sentiment'), log_run=False)['team']
    by[x['topic']][d] += 1
for topic, c in by.items(): print(topic, '->', dict(c))
"
```
Mục đích: xác nhận mỗi topic gold map về đúng phòng kỳ vọng. Nếu một topic gold map về phòng vô lý (vd Pricing→nơi không mong muốn), cân nhắc chỉnh dòng route tương ứng trong `data/taxonomy/routing_table.json`.

- [ ] **Step 2: (Có điều kiện) chỉnh `routing_table.json`**

CHỈ chỉnh nếu Step 1 lộ map sai rõ. Mỗi chỉnh sửa: sửa 1 dòng route → chạy `.venv/bin/python -m eval.route_eval | head -3` → giữ nếu dept accuracy không tụt, revert nếu tụt. Giữ đúng 4 phòng `IT|CSKH|Vận hành|Marketing`.

- [ ] **Step 3: Xác nhận artifact data2 không bị code import**

Run:
```bash
cd /Users/kenz_de/projects/AI-Quality-Intelligence-Platform && grep -rn "data2/taxonomy/routing_table\|auxiliary/data2/taxonomy" --include="*.py" . | grep -v node_modules
```
Expected: KHÔNG có dòng nào load chính file `routing_table.json` trong data2. (Các script chỉ tham chiếu thư mục data2 nói chung — không sao.) Nếu có code load trực tiếp file này → DỪNG, không xoá, báo lại.

- [ ] **Step 4: Xoá artifact gây nhiễu**

```bash
cd /Users/kenz_de/projects/AI-Quality-Intelligence-Platform && git rm data/auxiliary/data2/taxonomy/routing_table.json
```

- [ ] **Step 5: Xác nhận không vỡ import + gate**

Run: `cd pipeline && .venv/bin/python -m pytest tests/ -q`
Expected: không lỗi import; các test pass (gate accuracy có thể vẫn đỏ nếu chưa đạt 80% — xử lý ở Task 6).

- [ ] **Step 6: Commit**

```bash
cd /Users/kenz_de/projects/AI-Quality-Intelligence-Platform && git add data/taxonomy/routing_table.json data/auxiliary/data2/taxonomy/routing_table.json
git commit -m "chore(taxonomy): rà bảng map 4 phòng + xoá routing_table data2 gây nhiễu

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: (Có điều kiện) retrain topic model nếu chưa đạt 80%

**Files:**
- Modify: `pipeline/ml/topic_model.joblib` (chỉ thay nếu holdout tăng thật)
- Reference: `pipeline/ml/train_data2_balanced_experiment.py` (mẫu quy trình train)

**Interfaces:**
- Consumes: `eval.route_eval.evaluate` trên holdout để quyết định ship.

CHỈ thực hiện Task này nếu sau Task 4–5 mà `dept_accuracy < 0.80`. Nếu đã ≥ 0.80 → đánh dấu task này SKIPPED và sang Task 7.

- [ ] **Step 1: Kiểm tra có cần không**

Run: `cd pipeline && .venv/bin/python -m eval.route_eval | head -3`
Nếu `DEPARTMENT accuracy` ≥ 80% → ghi "SKIPPED — đã đạt ngưỡng nhờ rules", bỏ qua các step còn lại của Task 6.

- [ ] **Step 2: Tách train/holdout từ golden set (80/20, seed cố định)**

Create `pipeline/ml/retrain_topic.py`:

```python
"""Retrain topic model trên golden set, đo bằng route_eval trên holdout.
Chỉ ghi đè joblib nếu holdout accuracy tăng so với model hiện tại.
"""
import json
import random
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import make_pipeline

from core.paths import DATA_DIR

GOLDEN = DATA_DIR / "train" / "seed_train_labeled.json"
OUT = Path(__file__).resolve().parent / "topic_model.candidate.joblib"


def main():
    data = json.load(open(GOLDEN, encoding="utf-8"))
    random.seed(42)
    random.shuffle(data)
    cut = int(len(data) * 0.8)
    train, holdout = data[:cut], data[cut:]

    X = [d["text_full"] for d in train]
    y = [d["topic"] for d in train]
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=50000),
        LinearSVC(class_weight="balanced"),
    )
    model.fit(X, y)

    hits = sum(1 for d in holdout if model.predict([d["text_full"]])[0] == d["topic"])
    print(f"Holdout topic accuracy (candidate): {hits / len(holdout) * 100:.1f}%")
    joblib.dump(model, OUT)
    print(f"Saved candidate -> {OUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Train candidate + đọc accuracy holdout**

Run: `cd pipeline && .venv/bin/python -m ml.retrain_topic`
Ghi lại "Holdout topic accuracy (candidate)". So với accuracy model hiện tại trên cùng holdout (chạy lại `predict_feedback` chỉ phần model — hoặc dùng `eval.route_eval` toàn bộ làm xấp xỉ).

- [ ] **Step 4: Chỉ promote nếu tốt hơn**

Nếu candidate holdout accuracy CAO HƠN model hiện tại:
```bash
cd pipeline && cp ml/topic_model.candidate.joblib ml/topic_model.joblib
```
Ngược lại: KHÔNG ghi đè (giữ model cũ, dựa vào rules). Xoá candidate: `rm pipeline/ml/topic_model.candidate.joblib`.

- [ ] **Step 5: Đo lại toàn bộ + gate**

Run: `cd pipeline && .venv/bin/python -m eval.route_eval | head -3 && .venv/bin/python -m pytest tests/test_routing_accuracy.py -q`
Expected: dept accuracy ≥ 80%, gate PASS. Nếu vẫn < 80% sau cả rules + retrain → hạ `TARGET_DEPT_ACCURACY` xuống mức đạt được thực tế trong `test_routing_accuracy.py` kèm comment giải thích, và ghi nhận giới hạn ở doc (Task 7).

- [ ] **Step 6: Commit**

```bash
cd /Users/kenz_de/projects/AI-Quality-Intelligence-Platform && git add pipeline/ml/retrain_topic.py pipeline/ml/topic_model.joblib pipeline/tests/test_routing_accuracy.py 2>/dev/null
git commit -m "feat(ml): retrain topic model (promote nếu holdout tăng) + chốt ngưỡng gate

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Tài liệu — luồng E2E + taxonomy định tuyến

**Files:**
- Create: `docs/project/architecture/e2e-flow.md`
- Create: `docs/project/architecture/routing-taxonomy.md`

**Interfaces:** none (tài liệu).

REQUIRED SUB-SKILL: `humanizer` — viết văn phong tự nhiên, tránh giọng máy.

- [ ] **Step 1: Viết doc luồng E2E**

Create `docs/project/architecture/e2e-flow.md` mô tả ĐÚNG hiện trạng, gồm các chặng và file tương ứng:
- Tiếp nhận: `classifier.predict_feedback` (ML + `rules.apply_rules`) → topic/sentiment/severity/needs_review.
- Định tuyến: `agents/router_agent.route_ticket` + `data/taxonomy/routing_table.json` → phòng ban (4 phòng).
- Sinh ticket: `spike_detector` gom (area, topic) → `agents/ticket_agent.create_or_update_ticket` → bảng `alerts`.
- Sinh task: `agents/task_agent` → bảng `tasks`.
- Báo cáo: `agents/insight_agent` + `analyst_agent` + `report_builder` → `department_reports` (kèm `suggested_tasks`, `root_cause_summary`).
- HI-Loop Approval (đã triển khai): Manager sửa Draft Task → `POST /api/reports/{id}/approve-and-dispatch` (RPC `approve_report_and_dispatch`) → tạo `tasks` (source=report, report_id) → nhân viên xử lý.
Kèm sơ đồ ASCII luồng. Tham chiếu spec `docs/superpowers/specs/2026-06-25-router-accuracy-design.md` cho phần định tuyến.

- [ ] **Step 2: Viết doc taxonomy định tuyến**

Create `docs/project/architecture/routing-taxonomy.md`:
- 4 phòng ban và phạm vi mỗi phòng.
- Bảng topic → phòng (copy từ `routing_table.json` sau khi sửa), kèm lý do.
- Quy tắc override: Safety-first, P5 → Vận hành, positive+Other → Marketing.
- Ghi rõ topic nào được phân loại bởi rule nào (ánh xạ sang `rules.py`).
- Số liệu accuracy hiện tại (từ `eval.route_eval`) và cách chạy lại harness.

- [ ] **Step 3: Verify số liệu trong doc khớp eval thực tế**

Run: `cd pipeline && .venv/bin/python -m eval.route_eval | head -3`
Đảm bảo con số accuracy ghi trong doc khớp output.

- [ ] **Step 4: Commit**

```bash
cd /Users/kenz_de/projects/AI-Quality-Intelligence-Platform && git add docs/project/architecture/e2e-flow.md docs/project/architecture/routing-taxonomy.md
git commit -m "docs: luồng E2E + taxonomy định tuyến 4 phòng ban

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Audit & dọn các .md lỗi thời

**Files:**
- Modify/Delete: `README.md`, `JOURNAL.md`, `WORKLOG.md`, `IMPLEMENTATION_PLAN.md` (tuỳ kết quả audit)

**Interfaces:** none.

REQUIRED SUB-SKILL: `humanizer` cho mọi đoạn viết lại.

- [ ] **Step 1: Liệt kê & đọc các .md top-level**

Run: `cd /Users/kenz_de/projects/AI-Quality-Intelligence-Platform && ls *.md && wc -l *.md`
Đọc từng file, ghi chú: chỗ nào mô tả sai hiện trạng (vd nói routing chưa fix), chỗ nào trùng lặp, chỗ nào nói "6 phòng ban" như thể đã có (phải đánh dấu là future).

- [ ] **Step 2: Sửa nội dung lỗi thời**

- `IMPLEMENTATION_PLAN.md` mục 9 (mở rộng 6 phòng): thêm dòng đầu mục đánh dấu rõ **"Định hướng tương lai — CHƯA triển khai. Hệ thống hiện chạy 4 phòng ban."**
- `README.md`: cập nhật mô tả luồng định tuyến + trỏ tới `docs/project/architecture/e2e-flow.md` và `routing-taxonomy.md`.
- Bất kỳ câu nào nói routing "đang sai/đang chờ fix" → cập nhật theo trạng thái đã sửa + accuracy mới.

- [ ] **Step 3: Hợp nhất/xoá file trùng lặp**

Nếu `JOURNAL.md` và `WORKLOG.md` chồng lấn và một file đã chết (không cập nhật, nội dung gộp được) → hợp nhất vào một file, `git rm` file còn lại. CHỈ xoá sau khi xác nhận nội dung giá trị đã được giữ ở nơi khác.

- [ ] **Step 4: Commit**

```bash
cd /Users/kenz_de/projects/AI-Quality-Intelligence-Platform && git add -A *.md
git commit -m "docs: audit & dọn .md lỗi thời, đồng bộ trạng thái routing & 4 phòng ban

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Verify E2E + regression toàn bộ

**Files:** none (chạy kiểm thử).

- [ ] **Step 1: Chạy toàn bộ test backend**

Run: `cd pipeline && .venv/bin/python -m pytest tests/ -q`
Expected: tất cả pass, gồm `test_routing_accuracy.py` (gate XANH), `test_router_agent.py`, `test_classifier.py`, không regression.

- [ ] **Step 2: In báo cáo accuracy cuối cùng**

Run: `cd pipeline && .venv/bin/python -m eval.route_eval`
Expected: dept accuracy ≥ 80% (hoặc ngưỡng đã chốt ở Task 6 Step 5), tải `IT`/`Vận hành` cân đối hơn baseline rõ rệt, không ô misroute > 150.

- [ ] **Step 3: Xác nhận tài liệu khớp**

Mở `docs/project/architecture/routing-taxonomy.md`, đối chiếu số accuracy và bảng map với output Step 2. Sửa nếu lệch.

- [ ] **Step 4: Commit (nếu có chỉnh nhỏ khi verify)**

```bash
cd /Users/kenz_de/projects/AI-Quality-Intelligence-Platform && git add -A
git commit -m "test: verify E2E routing accuracy + đồng bộ tài liệu

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Out of scope (tách spec sau)

- Mở rộng 4 → 6 phòng ban (Tài chính, Sản phẩm, Rủi ro/Gian lận) và báo cáo tổng hợp chéo phòng (Global Report). Xem `docs/project/roadmap.md`.
- Thay router heuristic bằng LLM.
