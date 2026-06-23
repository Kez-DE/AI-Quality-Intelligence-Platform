# Advanced Analytics Charts — Design Spec

**Date:** 2026-06-23  
**Project:** C2-App-116 · AI Quality Intelligence Platform (xanhSM)  
**Scope:** Thêm section "Phân tích nâng cao" vào tab Cockpit với 4 biểu đồ mới.  
**Status:** Approved, pending implementation.

---

## Tổng quan

Thêm một section có thể collapse/expand phía dưới `TicketBoard` trong `CockpitView`. Section này chứa 4 biểu đồ nâng cao giúp phân tích sâu hơn dữ liệu feedback — bổ sung cho các widget vận hành hiện tại (không thay thế).

---

## Layout

```
CockpitView (tab Cockpit)
├── KpiStrip
├── Grid 12 cols (TrendCard, AlertsPanel, Heatmap, LiveFeed, ...)
├── TicketBoard
└── AdvancedAnalytics   ← MỚI (collapsible)
    ├── SentimentLineChart  (full width)
    ├── RiskHistogram       (lg:col-span-7)
    ├── PipelineFunnel      (lg:col-span-5)
    └── SankeyFlow          (full width)
```

**Default state:** đóng (`isOpen = false`). Header hiển thị "▼ Phân tích nâng cao · 4 biểu đồ". Khi mở: 4 chart render lazy (không mount khi đóng → tiết kiệm query).

---

## Cấu trúc file

```
app/src/components/cockpit/widgets/
└── charts/
    ├── SentimentLineChart.tsx
    ├── RiskHistogram.tsx
    ├── PipelineFunnel.tsx
    └── SankeyFlow.tsx
app/src/components/cockpit/widgets/
└── AdvancedAnalytics.tsx       ← wrapper collapsible
```

Không thêm dependency mới. Recharts v2.15.4 đã cài. Sankey dùng SVG thủ công.

---

## Backend — Mở rộng `/api/cockpit/overview`

### Fields mới thêm vào response

```python
{
  # ... các field hiện tại giữ nguyên ...

  # Chart 1: SentimentLineChart
  "trend_sentiment": [
    {"date": "YYYY-MM-DD", "positive": int, "neutral": int, "negative": int},
    # × window_days phần tử
  ],

  # Chart 2: RiskHistogram  
  "risk_distribution": [
    {"score": 1, "count": int},
    # score 1..10, count = 0 nếu không có
  ],

  # Chart 3: PipelineFunnel
  "funnel": {
    "total": int,            # tổng feedback trong cửa sổ
    "classified": int,        # có topic != null
    "needs_review": int,      # needs_review = True
    "alerts_triggered": int,  # đếm alerts trong khoảng thời gian
    "tickets_created": int,   # đếm tasks trong khoảng thời gian
    "resolved": int           # tasks với status = 'resolved'
  },

  # Chart 4: SankeyFlow
  "sankey_flows": [
    {"from": str, "to": str, "value": int},
    # Layer 1→2: sentiment × severity cross-tab từ feedback table
    #   from ∈ {"positive", "neutral", "negative"}
    #   to   ∈ {"P1", "P2", "P3", "P4", "P5"}
    # Layer 2→3: severity × status từ tasks table (priority → status)
    #   from ∈ {"P1", "P2", "P3", "P4", "P5"}
    #   to   ∈ {"open", "in_progress", "resolved"}
  ]
}
```

### Tính toán

**`trend_sentiment`:** Cùng loop feedback đã có, thêm bucket theo `sentiment`. O(n) không cần query thêm.

**`risk_distribution`:** `Counter(row["overall_risk"] for row in feedback_rows)` — cùng dataset.

**`funnel`:**
- `total`, `classified` (có topic), `needs_review` — từ `feedback_rows` đã load.
- `alerts_triggered` — query `alerts` table đếm theo `created_at >= window_start` (scoped).
- `tickets_created` — query `tasks` table tương tự.
- `resolved` — filter `tasks` thêm `status = 'resolved'`.

**`sankey_flows`:**
- Layer 1→2: `Counter((row["sentiment"], row["severity"]) for row in feedback_rows)` → list links.
- Layer 2→3: query `tasks` group by `(priority, status)` (scoped).
- Lọc value = 0 để tránh noise.

**Guest scope:** `sankey_flows`, `funnel` chỉ trả `[]`/`{}` cho guest (không có tasks/alerts). `trend_sentiment` và `risk_distribution` trả full.

---

## Chart 1 — SentimentLineChart

**Component:** `recharts LineChart`  
**Data source:** `overview.trend_sentiment`  
**Wrapper:** dùng `ui/chart.tsx` (`ChartContainer`, `ChartTooltip`, `ChartLegend`)

```
Series:
  - positive  → stroke: var(--xanh-green),  strokeWidth: 2
  - neutral   → stroke: var(--xanh-cyan),   strokeWidth: 1.5, strokeDasharray: "4 2"
  - negative  → stroke: var(--xanh-coral),  strokeWidth: 2,   strokeDasharray: "3 3"

Axes:
  - XAxis: dates (MM/DD), tick mỗi 3 ngày
  - YAxis: count, auto domain
  - CartesianGrid: stroke="#e5e7eb" strokeDasharray="2 4"

Tooltip: custom — hiện 3 giá trị + ngày
Height: 220px
```

---

## Chart 2 — RiskHistogram

**Component:** `recharts BarChart` (layout="vertical")  
**Data source:** `overview.risk_distribution`

```
Bars:
  - Score 1–6: fill: var(--xanh-green) (opacity 0.7–1 theo score)
  - Score 7–8: fill: var(--xanh-amber)
  - Score 9–10: fill: var(--xanh-coral)

Axes:
  - YAxis (category): score labels "Risk 1" … "Risk 10"  
  - XAxis (value): count
  - Tooltip: "N phản hồi có rủi ro X"

Height: 280px
Orientation: horizontal bars (dễ đọc label hơn vertical)
```

---

## Chart 3 — PipelineFunnel

**Component:** `recharts FunnelChart`  
**Data source:** `overview.funnel`

```
Stages (top → bottom, thu hẹp dần):
  1. Tất cả feedback    → total          (màu: var(--xanh-deep))
  2. Đã phân loại       → classified     (màu: var(--xanh-cyan))
  3. Cần review         → needs_review   (màu: var(--xanh-amber))
  4. Sinh alert         → alerts_triggered (màu: var(--xanh-coral)/60%)
  5. Tạo ticket         → tickets_created  (màu: var(--xanh-coral))
  6. Đã giải quyết      → resolved         (màu: var(--xanh-green))

Label: hiện số lượng + tỷ lệ % so với stage trước ("95% → 4.6% → ...")
Tooltip: "X / total = Y%"
Height: 280px
```

---

## Chart 4 — SankeyFlow (SVG thủ công)

**Không dùng thư viện.** Viết React component thuần SVG.

```
Layout:
  Cột 1 (Sentiment): positive / neutral / negative   — màu green/cyan/coral
  Cột 2 (Severity):  P1 / P2 / P3 / P4 / P5         — màu gradient xanh→đỏ
  Cột 3 (Status):    open / in_progress / resolved   — màu amber/cyan/green

Links:
  - Path SVG bezier cubic: C x1,y1 x2,y2 x,y
  - fill: màu node nguồn (opacity 0.35)
  - width ∝ value (min 2px, max = node height)
  - Hover: opacity lên 0.65 + tooltip "{from} → {to}: N"

Node:
  - rect: width=16px, height ∝ tổng value qua node
  - label bên trái/phải tuỳ cột

Xử lý edge cases:
  - value = 0: không vẽ link
  - overall_risk = null: bỏ qua (không crash)

Height: 300px, viewBox responsive
```

---

## Tương tác

| Hành động | Kết quả |
|-----------|---------|
| Hover điểm LineChart | Tooltip 3 giá trị sentiment + ngày |
| Hover bar Histogram | Tooltip "N phản hồi · Risk score X" |
| Hover stage Funnel | Tooltip "X · Y% của tổng" |
| Hover link Sankey | Tooltip "A → B: N" + highlight link |
| Click section header | Toggle collapse/expand (state local) |

**Cross-filter:** Phase này chưa kết nối `CockpitFilterContext` — các chart analytics là read-only. Cross-filter có thể thêm ở phase sau.

---

## RBAC

| Role | SentimentLine | Histogram | Funnel | Sankey |
|------|---------------|-----------|--------|--------|
| admin | ✓ full | ✓ full | ✓ full | ✓ full |
| manager/staff (có phòng) | ✓ scoped | ✓ scoped | ✓ (no alerts/tickets nếu khác phòng) | ✓ scoped |
| guest | ✓ limited | ✓ limited | ✗ ẩn | ✗ ẩn |
| unassigned ops | section ẩn | section ẩn | section ẩn | section ẩn |

---

## Loading states

Mỗi chart có skeleton riêng:
- LineChart: 3 đường nhạt animate pulse
- Histogram: bars nhạt
- Funnel: trapezoid shapes nhạt
- Sankey: placeholder rect nhạt

Nếu `overview.trend_sentiment` chưa có (backend cũ): hiện badge "Cần cập nhật backend".

---

## Test plan

**Backend:**
- `test_cockpit_overview.py`: thêm test cho admin thấy `trend_sentiment`, `risk_distribution`, `funnel`, `sankey_flows`.
- Test guest: `sankey_flows = []`, `funnel = {}`.
- Test risk_distribution: scores missing → fill 0.

**Frontend:**
- TypeScript: `tsc --noEmit` không lỗi.
- Manual: mở cockpit, expand section, kiểm tra 4 chart render với data.
- Manual: hover các chart hiện tooltip đúng.

---

## Không nằm trong scope này

- Cross-filter (click chart → lọc widget khác) — phase sau.
- Export chart (PNG/SVG) — phase sau.
- Thay thế TrendCard hiện tại bằng SentimentLineChart — giữ nguyên TrendCard.
- Drill-down từ Funnel sang trang liên quan — phase sau.
