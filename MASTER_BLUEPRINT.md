# MASTER BLUEPRINT: AI Quality Intelligence Platform (AI20K-223)
**Lĩnh vực:** Smart Mobility — Feedback Analytics | **Tech Stack:** React, FastAPI, Supabase, NLP, Multi-Agent AI (Groq Llama 3.3)

Bản tài liệu này là Thiết kế Thi công Tổng thể (Master Blueprint) — phiên bản 2.1, bao phủ **toàn bộ 3 tầng của dự án**: Backend Multi-Agent (Python/FastAPI), Frontend (React/TanStack), và Supabase (Database/Auth/Realtime). Nó tổng hợp bài toán thực tế, khoá chặt phạm vi sản phẩm, và mô tả kiến trúc **Hệ thống Multi-Agent** đã được hiện thực hóa: từ ticket được định tuyến về phòng ban → tổng hợp insight → phân tích sâu → cảnh báo thông minh, tất cả chạy **tự động khép kín** và đẩy realtime xuống Dashboard.

**Mục lục:** [1] Pain Points · [2] Kiến trúc Multi-Agent · [3] Luồng End-to-End · [4] API Surface · [5] Scope · [6] Cấu trúc Backend · [7] Kiến trúc Frontend · [8] Supabase · [9] Sprint Plan · [10] Kịch bản Demo Day

---

## 1. Phân Tích User Pain Points (Nỗi đau của người dùng)

| Chân dung User | Pain Point (Vấn đề) | Giải pháp của hệ thống (Tính năng) |
| :--- | :--- | :--- |
| **Quản lý Vận hành (Ops)** | Đọc báo cáo thủ công quá chậm, thường chỉ biết đến khủng hoảng khi nó đã bùng phát mạng xã hội. | **Orchestrator chạy tự động mỗi 10 phút:** Phát hiện spike, phân cấp cảnh báo, tạo alert realtime — không cần ai bấm nút. |
| **Đội An toàn (Safety)** | Dễ bị sót các phản hồi nghiêm trọng như "tài xế say xỉn", "tai nạn" giữa hàng ngàn review rác. | **Rule-based + Severity Override:** Keyword an toàn ép Severity P5. Router Agent ép mọi case P5 về Safety với SLA 1 giờ, kích hoạt mức 🔴 CRITICAL bất kể số lượng. |
| **Đội CSKH (CS Team)** | Nhận luồng ticket khổng lồ, không biết ưu tiên xử lý cái nào trước, mất thời gian tự tóm tắt vấn đề. | **Router Agent + Insight Agent:** AI gom phản hồi lỗi → sinh báo cáo nguyên nhân lõi → giao ticket đúng Team kèm SLA → tổng hợp insight riêng cho từng phòng. |
| **Trưởng phòng các Team** | Nhận ticket rời rạc, không có bức tranh tổng thể: phòng mình đang "nóng" đến đâu, xu hướng tăng hay giảm, nên ưu tiên gì. | **Analyst Agent (Phân tích sâu):** LLM đọc insight tổng hợp của phòng → chỉ ra nguyên nhân gốc rễ xuyên ticket, mức rủi ro, dự báo 24-48h, và 3 hành động ưu tiên kèm deadline. |
| **Đội IT / Product** | Khó theo dõi kịp thời các lỗi kỹ thuật (app lag, crash, lỗi GPS) ngay sau các đợt cập nhật app. | **Topic "App Issue" → Route về IT:** Phân loại riêng phàn nàn kỹ thuật, insight phòng IT hiển thị top khu vực lỗi để fix bug khẩn cấp. |
| **Toàn hệ thống** | Spike detector cũ spam alert trùng lặp, mọi spike đều bị gắn P1 khiến cảnh báo "nhờn". | **Alert Agent:** Phân cấp 3 mức (WATCH/WARNING/CRITICAL) + chống trùng lặp (cooldown 60 phút/khu vực). |

---

## 2. Kiến Trúc Multi-Agent (Trái tim của hệ thống)

Hệ thống gồm **6 Agent nghiệp vụ** đặt tại `pipeline/agents/`, phối hợp qua một Orchestrator trung tâm (Orchestrator không tính là agent nghiệp vụ — chỉ điều phối):

| # | Agent | File | Nhiệm vụ |
| :--- | :--- | :--- | :--- |
| 1 | 📥 **Ingestion/Classifier Agent** | `ingestion_agent.py` | Nhận feedback mới → clean PII → chạy ML topic/sentiment/severity → áp rule safety keyword → ghi DB. Fallback heuristic khi model lỗi. |
| 2 | 🧭 **Router Agent** | `router_agent.py` | Định tuyến ticket về đúng phòng ban dựa trên `data/taxonomy/routing_table.json` (topic → team + SLA). P5 **luôn** ép về Safety. Config-driven, đổi routing chỉ sửa JSON. |
| 3 | 🎫 **Ticket Agent** | `ticket_agent.py` | Tạo/cập nhật ticket, dedup ticket trùng (cùng area + topic + severity trong cooldown), gán SLA/owner/team/status/priority. State machine: open → triaged → in_progress → resolved → closed. |
| 4 | 📊 **Insight Agent** | `insight_agent.py` | Tổng hợp insight cho **từng phòng ban**: tổng feedback, tỷ lệ tiêu cực, phân bố severity, top topic/khu vực, xu hướng % so kỳ trước, trạng thái ticket, trích dẫn tiêu biểu. |
| 5 | 🔬 **Analyst Agent** | `analyst_agent.py` | Phân tích sâu insight bằng LLM: nguyên nhân gốc rễ **xuyên nhiều ticket**, mức rủi ro (LOW→CRITICAL), dự báo 24-48h, 3 hành động ưu tiên kèm deadline. Fallback heuristic khi không có API key. |
| 6 | 🚨 **Alert/Escalation Agent** | `alert_agent.py` | Cảnh báo thông minh: phân cấp 🟡 WATCH (≥3 case) / 🟠 WARNING (≥5) / 🔴 CRITICAL (≥10 hoặc có P5) theo `severity_rules.json` + **dedup** cooldown 60 phút/khu vực. Escalation khi quá SLA. |

| Thành phần hỗ trợ | File | Vai trò |
| :--- | :--- | :--- |
| 🎯 **Scoring Agent** | `scoring_agent.py` | Sử dụng LLM (Llama 3) chấm điểm rủi ro đa chiều (Deep Risk Matrix 5 vector) ngay lúc Ingestion. Tối ưu chi phí bằng phễu lọc ML, Caching, và Batching LLM calls. |
| 🎼 **Orchestrator** | `orchestrator.py` | Điều phối pipeline 6 agent theo thứ tự: Ingestion → Router → Ticket → Alert → Insight → Analyst. Chạy tự động mỗi 10 phút (APScheduler) hoặc kích hoạt thủ công qua API. Retry + logging + schedule. |

**Nguyên tắc thiết kế:**
- **Hybrid Fast/Slow Layer:** Ingestion Agent dùng ML Model truyền thống để càn quét nhanh 100% dữ liệu (Fast Layer, chi phí API = 0). Analyst Agent dùng LLM để phân tích sâu khi có cảnh báo (Slow Layer).
- **Config-driven:** Định tuyến và ngưỡng cảnh báo nằm trong `data/taxonomy/*.json` — chạy chuẩn 100% cấu trúc nghiệp vụ thực tế của Ops.
- **Graceful degradation:** Mọi agent đều có chế độ fallback (mock/heuristic) khi thiếu API key — demo không bao giờ chết.
- **Tiết kiệm quota:** Analyst Agent chỉ phân tích sâu các phòng có feedback tiêu cực hoặc ticket đang mở.
- **Dedup + Cooldown:** Ticket Agent dedup cùng area+topic+severity trong cooldown. Alert Agent dedup alert 60 phút/khu vực.
- **Input/Output schema rõ ràng:** Mỗi agent định nghĩa input/output riêng, ghi `agent_run_log` cho mọi lần chạy.
- **Tương thích ngược:** Format alert giữ chuẩn `**Action Plan:** / **Assigned Team:**` nên Frontend không cần sửa.

### 2.1. Hệ Thống Chấm Điểm Đa Chiều & Ma Trận Rủi Ro (Deep Risk Matrix)

**Bài toán:** Việc sử dụng một nhãn `severity` chung chung hoặc tính điểm trung bình (average) là một **lỗ hổng nghiêm trọng** trong nghiệp vụ Vận tải. Một chuyến xe sạch sẽ, đúng giờ nhưng tài xế có hành vi quấy rối thì điểm trung bình vẫn cao, dẫn đến lọt rủi ro khẩn cấp. 

**Giải pháp:** Chuyển đổi từ `Single Severity` sang `Multi-dimensional Risk Vector` (Vector 5 chiều) bóc tách trực tiếp bằng **LLM (Scoring Agent)**. Sau đó tính điểm tổng hợp (Thang 1-5) bằng **Thuật toán Max-Pooling Rule-based Waterfall (Thác rơi ưu tiên rủi ro cao nhất)**. Tuyệt đối KHÔNG cộng trung bình.

> 💡 **Chiến lược Tối ưu Ingestion (Phễu Lọc 3 Tầng Vàng):** Để không tốn chi phí API cho 100% data, hệ thống áp dụng 3 lớp lọc:
> 1. **Lọc ML (Tầng 1):** Mô hình `.joblib` quét siêu tốc 100% data. Chỉ các feedback `negative` mới được xem xét. Khen/Bình thường auto rủi ro = 0.
> 2. **LLM Batching (Tầng 2):** Gom 20-50 feedback tiêu cực vào 1 cụm gửi lên API trong 1 lần duy nhất, tiết kiệm 95% số lần gọi API và token cấu trúc prompt.
> 3. **Caching (Tầng 3):** Lưu bộ đệm (Hash) các câu review giống nhau. Lặp lại là tốn 0 token. Dùng cơ chế **Review Queue** làm Fallback khi gọi API thất bại.

#### 1. Định nghĩa Vector 5 Chiều (Chấm rủi ro từ 0-10)
| Tiêu chí | Biến số | Định nghĩa (Độ nguy hiểm 0 ➔ 10) | Từ khóa đặc trưng (Ví dụ) |
| :--- | :--- | :--- | :--- |
| **An toàn** | `risk_safety` | Đe dọa tính mạng, thân thể, quấy rối, tai nạn. | "Tai nạn", "tông xe", "sờ đùi", "cướp", "say xỉn". |
| **Gian lận** | `risk_fraud` | Hành vi chiếm đoạt tài sản, gian lận cước, vòi vĩnh. | "Thu thêm tiền", "đòi thêm", "chuyển khoản riêng". |
| **Thái độ** | `risk_attitude` | Hành vi cư xử không chuẩn mực, chửi bới, xúc phạm. | "Chửi", "thái độ lồi lõm", "vô văn hóa". |
| **Phương tiện**| `risk_vehicle` | Xuống cấp phương tiện, hỏng hóc, mất vệ sinh. | "Xe hôi", "bẩn", "máy lạnh hỏng", "ồn". |
| **Tuân thủ** | `risk_compliance`| Vi phạm quy trình dịch vụ, đi sai đường, trễ giờ. | "Cao su", "đón sai", "đi lòng vòng", "ép hủy". |

#### 2. Thuật toán Tính điểm chung (Overall Risk Score: Thang 1-5)
Hệ thống duyệt tuần tự từ bậc Khẩn cấp nhất (5) xuống An toàn (1). **Thỏa mãn ở đâu, chốt điểm ở đó.**

```python
def calculate_overall_risk(risk_safety, risk_fraud, risk_attitude, risk_vehicle, risk_compliance):
    # BẬC 5: KHẨN CẤP (🚨) - Cảnh sát, Khóa tài khoản
    if risk_safety >= 8 or risk_fraud >= 8: return 5

    # BẬC 4: NGUY HIỂM (🔴) - Team Ops can thiệp khẩn
    if risk_safety >= 5 or risk_fraud >= 5 or risk_attitude >= 8: return 4

    # BẬC 3: RỦI RO TRUNG BÌNH (🟠) - CSKH gọi xin lỗi, Trừ điểm
    count_medium = sum(1 for x in [risk_safety, risk_fraud, risk_attitude, risk_vehicle, risk_compliance] if x >= 4)
    if risk_vehicle >= 6 or risk_compliance >= 6 or risk_attitude >= 6 or count_medium >= 3: return 3

    # BẬC 2: RỦI RO THẤP (🟡) - Gửi voucher tự động
    if max(risk_safety, risk_fraud, risk_attitude, risk_vehicle, risk_compliance) >= 3: return 2

    # BẬC 1: AN TOÀN / BÌNH THƯỜNG (🟢) - Ghi nhận
    return 1
```

#### 3. Phân tích Tình huống (Edge Cases)
- **Tài xế biến thái:** Xe xịn (`risk_vehicle=0`), đúng giờ (`risk_compliance=0`), không gian lận (`risk_fraud=0`), sàm sỡ khách (`risk_safety=9`). 
  - *Average:* Tổng 9/50 -> Trung bình < 2. Hệ thống báo An toàn. ❌
  - *Waterfall:* `risk_safety >= 8` -> **BẬC 5 KHẨN CẤP**. ✅
- **Tài xế chửi tục:** Đúng quy trình (`risk_compliance=0`), chửi mắng khách (`risk_attitude=8`).
  - *Waterfall:* `risk_attitude >= 8` -> **BẬC 4 NGUY HIỂM**. ✅

---

## 3. Luồng Xử Lý End-to-End (Quy trình khép kín)

Hệ thống được thiết kế linh hoạt với **2 chế độ chạy**:
1. **Production:** Orchestrator tự chạy mỗi 10 phút (APScheduler) — phát hiện, phân tích, cảnh báo, tổng hợp insight hoàn toàn tự động.
2. **Demo Day:** API bắn 150 phản hồi giả lập + `POST /api/agent/run` kích hoạt vòng pipeline ngay lập tức trên sân khấu.

Ngoài ra, luồng xử lý Feedback có sự phân tách rõ ràng (Human-in-the-loop):
- **Luồng Stream:** Mọi dữ liệu đi vào (từ App) sẽ được đẩy realtime lên UI ngay lập tức.
- **Luồng Review Queue:** Nếu model chấm điểm độ tin cậy thấp, ticket sẽ được đánh cờ `needs_review` và đưa vào hàng chờ kiểm duyệt. Human Admin sẽ vào Review Queue để sửa nhãn. Nhãn hiển thị trên UI đã được **i18n hoá sang Tiếng Việt** để người dùng dễ thao tác.

```mermaid
sequenceDiagram
    participant Cron as APScheduler (10m) / Demo API
    participant Orch as 🎼 Orchestrator
    participant IngestA as 🔄 Ingestion Agent
    participant ML as ML Models + Rules
    participant DB as Supabase DB
    participant AlertA as 🚨 Alert Agent
    participant LLM as Groq Llama 3.3
    participant Router as 🧭 Router Agent
    participant TicketA as 🎫 Ticket Agent
    participant Insight as 📊 Insight Agent
    participant Analyst as 🔬 Analyst Agent
    participant FE as React Dashboard

    Note over ML,DB: Tầng 1 — Ingestion Agent: Clean PII → Topic/Sentiment → Safety Rule → bảng 'feedback'

    Cron->>Orch: Kích hoạt vòng pipeline
    Orch->>IngestA: [1] Nhận feedback mới, clean PII, phân loại ML + rule Safety
    IngestA->>DB: Ghi feedback đã gán nhãn vào Supabase
    Orch->>DB: [2] Quét feedback P4/P5 trong 1h, gom theo khu vực
    Orch->>AlertA: [3] Tính mức cảnh báo từng khu vực
    AlertA-->>Orch: WATCH / WARNING / CRITICAL (hoặc bỏ qua + dedup)
    Orch->>LLM: [4] Phân tích root cause khu vực vượt ngưỡng
    LLM-->>Orch: JSON (title, root cause, action, team)
    Orch->>Router: [5] Xác nhận phòng ban (routing_table.json, P5→Safety)
    Orch->>TicketA: [6] Tạo/cập nhật ticket, dedup, gán SLA + owner
    TicketA->>DB: Ghi ticket vào bảng 'alerts'
    Orch->>Insight: [7] Tổng hợp insight TẤT CẢ phòng ban
    Insight->>DB: Đọc feedback + tickets 24h
    Insight-->>Orch: Insight per-department (trend, severity, tickets...)
    Orch->>Analyst: [8] Phân tích sâu các phòng có rủi ro
    Analyst->>LLM: Root cause xuyên ticket + dự báo + đề xuất
    Analyst-->>Orch: risk_level, forecast, 3 recommendations

    FE->>DB: Realtime subscription bảng 'alerts'
    DB-->>FE: Dashboard đỏ rực + Ticket Triage theo phòng ban
```

---

## 4. API Surface (FastAPI)

| Endpoint | Method | Mô tả |
| :--- | :--- | :--- |
| `/api/trigger-demo-batch` | POST | 🎯 Demo Day: bắn 150 review giả lập vào DB tạo Spike |
| `/api/trigger-spike-detect` | POST | Spike detection bản cũ (giữ tương thích) |
| `/api/agent/run` | POST | **Chạy ngay một vòng Multi-Agent pipeline**, trả về báo cáo đầy đủ |
| `/api/agent/last-run` | GET | Báo cáo lượt chạy pipeline gần nhất |
| `/api/insights/departments?hours=24` | GET | Insight tổng hợp của **tất cả** phòng ban |
| `/api/insights/departments/{team}` | GET | Insight của một phòng (Safety, IT, CSKH, Vận Hành...) |
| `/api/insights/departments/{team}/deep-analysis` | GET | **Phân tích sâu bằng LLM** cho một phòng ban |

---

## 5. Phạm Vi Sản Phẩm (Scope)

**✅ NHỮNG GÌ CHẮC CHẮN LÀM (IN SCOPE):**
1. **Kiến trúc Cloud:** Triển khai 100% online (Vercel cho Frontend, Railway/Render cho Backend, Supabase cho Database).
2. **Auth & Roles:** Đăng nhập, đăng ký an toàn.
3. **Data Pipeline Dual-Mode:** APScheduler tự động (5-10 phút) và Endpoint phục vụ Demo 150 reviews.
4. **NLP Processing:** 2 model `.joblib` gán nhãn Topic/Sentiment kết hợp Rule-based Safety (keyword → P5).
5. **Hệ thống Multi-Agent (6 agents):** Ingestion → Router → Ticket → Insight → Analyst → Alert, điều phối bởi Orchestrator, chạy tự động khép kín mỗi 10 phút.
6. **Cảnh báo phân cấp + chống trùng:** WATCH/WARNING/CRITICAL theo `severity_rules.json`, cooldown 60 phút.
7. **Insight & Deep Analysis per-department:** API trả về số liệu tổng hợp + phân tích LLM cho từng phòng ban.
8. **Config-driven Routing:** `routing_table.json` + `severity_rules.json` trong `data_real/taxonomy/` — tích hợp hoàn chỉnh với dataset thật của tổ chức.
9. **Frontend 3 Màn hình:** `Dashboard` (Trend, Heatmap), `Alerts/Ticket Triage` (lọc theo phòng ban, realtime), `Feedback List` (sửa nhãn — Human-in-the-loop), và thêm màn `Department Insights` dùng Promise.all loại bỏ waterfall loading.

**❌ NHỮNG GÌ KHÔNG LÀM (OUT OF SCOPE):**
1. Không code hệ thống streaming data phức tạp (như Kafka). Dùng kiến trúc Batch qua Scheduler.
2. Không train lại mô hình NLP từ số 0. Tái sử dụng `.joblib` có sẵn.
3. Chưa tích hợp App thật của tài xế.
4. Chưa gửi notification ra kênh ngoài (Slack/Email) — alert hiển thị qua Dashboard realtime.

---

## 6. Cấu Trúc Repo Mới (Sau khi Refactor)

Cấu trúc thư mục theo chuẩn One-Repo Blueprint:

```
pipeline/                    # HỆ THỐNG BACKEND & MULTI-AGENT
├── main.py                  # FastAPI + APScheduler (agent pipeline mỗi 10 phút)
├── clean.py                 # Làm sạch text, giấu PII (SĐT, Email)
├── classifier.py            # ML Topic/Sentiment + Rule-based Safety Override
├── ingest.py                # Ghi feedback đã gán nhãn vào Supabase
├── spike_detector.py        # Spike detection bản cũ (giữ tương thích)
├── llm_agent.py             # Gọi Groq Llama 3.3 phân tích root cause (có mock)
├── ml/                      # Data ML training scripts (train Data_2 balanced)
└── agents/                  # 🤖 HỆ THỐNG MULTI-AGENT
    ├── common.py            # Supabase client (lazy) + LLM helper dùng chung
    ├── scoring_agent.py     # LLM chấm điểm rủi ro đa chiều (có Batching & Caching)
    ├── router_agent.py      # Định tuyến ticket theo routing_table.json
    ├── insight_agent.py     # Tổng hợp insight per-department
    ├── analyst_agent.py     # Phân tích sâu LLM (fallback heuristic)
    ├── alert_agent.py       # Cảnh báo phân cấp + dedup
    └── orchestrator.py      # Vòng pipeline khép kín 7 bước

data/                        # DỮ LIỆU & TAXONOMY
├── auxiliary/data2/         # Bộ data mới cân bằng (Balanced Data_2) cho ML
└── taxonomy/
    ├── routing_table.json   # Topic → Phòng ban + SLA (P5 override → Safety)
    ├── severity_rules.json  # Ngưỡng WATCH/WARNING/CRITICAL + cooldown
    ├── taxonomy.json        # Cây phân loại chủ đề
    └── safety_keywords.json # Từ khóa Rule-based Safety
```

---

## 7. Kiến Trúc Frontend (React — Quality Operation Cockpit)

### 7.1. Tech Stack

| Thành phần | Công nghệ | Ghi chú |
| :--- | :--- | :--- |
| Framework | **React 19 + TypeScript** | Build bằng Vite |
| Routing | **TanStack Router + TanStack Start** | File-based routing, có Server Functions (SSR-capable) |
| UI Kit | **TailwindCSS 4 + shadcn/ui (Radix)** | ~50 component dựng sẵn trong `components/ui/` |
| Biểu đồ | **Recharts** | Line/Bar chart cho Dashboard |
| Data & Auth | **@supabase/supabase-js** | Client browser + client server riêng biệt |
| Thông báo | **sonner** (toast) + **lucide-react** (icons) | |

### 7.2. Cấu trúc Routes & Màn hình

```
app/src/routes/
├── index.tsx                    # Landing page
├── auth.tsx                     # Đăng nhập / Đăng ký (Supabase Auth)
└── _authenticated/              # 🔒 Layout có Auth Guard
    ├── route.tsx                #    beforeLoad: chưa đăng nhập → redirect /auth
    ├── dashboard.tsx            # Tổng hợp biểu đồ, danh sách ticket mới.
    ├── department-insights.tsx  # Báo cáo root cause do LLM Analyst viết cho riêng từng phòng ban.
    ├── feedback.tsx             # 📝 Phân tách Stream (Live) & Review Queue (Lọc needs_review HITL)
    └── chat.tsx                 # 💬 AI Assistant (Groq Llama 3.3)
```

**Auth Guard** (`_authenticated/route.tsx`): mọi trang con đều chạy `supabase.auth.getUser()` trong `beforeLoad` — không có session hợp lệ thì redirect về `/auth`. Layout bọc chung bằng `AppShell` (sidebar điều hướng).

### 7.3. Chi tiết 4 màn hình chính

| Màn hình | Thành phần chính | Nguồn dữ liệu |
| :--- | :--- | :--- |
| **Dashboard** (`QualityCockpit.tsx`) | KPI Strip, Trend Chart, Category Breakdown, **Live Feed (realtime)**, Alerts Panel, **Heatmap khu vực × giờ** | Bảng `feedback` + `alerts`, subscribe realtime channel `dashboard-live-feedback` |
| **Alerts / Ticket Triage** (`alerts.tsx`) | Tab lọc theo phòng ban, thẻ alert có icon + màu riêng từng team, nút chuyển trạng thái `open → in_progress → resolved` | Bảng `alerts`, realtime subscription. Parse `assigned_team` từ format `**Assigned Team:**` |
| **Feedback** (`feedback.tsx`) | **Split 2 luồng:** <br/> 1. **Stream:** Toàn bộ feedback đổ về realtime. <br/> 2. **Review Queue:** Hàng đợi dành riêng cho các feedback có cờ `needs_review` cần con người duyệt và sửa nhãn sai (Human-in-the-loop). Hiển thị **i18n Tiếng Việt** cho các nhãn. | Bảng `feedback` với RLS và filter theo `needs_review` |
| **Chat AI** (`chat.tsx` + `ai.functions.ts`) | Chat với AI Assistant chuyên về quality ops, có câu hỏi gợi ý sẵn, lưu lịch sử | **Server Function** (TanStack Start) gọi Groq API phía server |

### 7.4. Hai đường dữ liệu của Frontend

```
┌──────────────────────────────────────────────────────────────┐
│  Đường 1 — TRỰC TIẾP (đọc/ghi dữ liệu):                      │
│  React ──@supabase/supabase-js──▶ Supabase (anon key + RLS)  │
│  Dùng cho: dashboard, alerts, feedback, lịch sử chat          │
│  + Realtime subscription: alert/feedback mới tự đẩy về UI    │
│                                                                │
│  Đường 2 — QUA SERVER (việc cần bí mật API key):             │
│  React ──Server Function──▶ Groq API (chat AI)               │
│  React ──HTTP──▶ FastAPI Backend (trigger demo, agent run)   │
└──────────────────────────────────────────────────────────────┘
```

> 💡 **Điểm hay của kiến trúc này:** Backend Python ghi alert vào Supabase → Supabase Realtime đẩy thẳng xuống browser. Frontend và Backend **không cần gọi API trực tiếp cho nhau** trong luồng chính — Supabase là "trạm trung chuyển" realtime.

---

## 8. Supabase — Database, Auth & Realtime

### 8.1. Sơ đồ 4 bảng (PostgreSQL)

```
auth.users (Supabase Auth quản lý)
    │ 1-1 (trigger tự tạo khi signup)
    ▼
profiles ◀────────────┐
  id (PK→auth.users)  │ user_id (FK)
  email, full_name    │
                      │
feedback ─────────────┤      alerts ──────────────┐    chat_messages
  id uuid PK          │        id uuid PK          │      id uuid PK
  user_id FK ─────────┘        user_id FK ─────────┘      user_id FK
  source, channel              title                      role (user/assistant/system)
  text (đã mask PII)           description (chứa Action   content
  topic, sentiment              Plan + Assigned Team +    created_at
  severity (P1→P5)              Escalation Level)
  area, confidence             severity (P1/P2/P3)
  created_at                   area, status (open→in_progress→resolved)
                               created_at
```

| Bảng | Ai ghi | Ai đọc | Realtime |
| :--- | :--- | :--- | :--- |
| `profiles` | Trigger `handle_new_user` (tự động khi signup) | Frontend | — |
| `feedback` | **Backend** (`ingest.py`) + Frontend (form nhập tay, sửa nhãn) | Dashboard, Feedback page | ✅ (publication `supabase_realtime`) |
| `alerts` | **Backend** (Alert Agent / spike_detector) + Frontend (đổi status) | Ticket Triage, Dashboard | ✅ |
| `chat_messages` | Frontend (sau mỗi lượt chat) | Chat page | — |

### 8.2. Bảo mật — Row Level Security (RLS) & 2 loại key

Tất cả 4 bảng đều bật **RLS** với policy `auth.uid() = user_id` — user chỉ thấy/sửa dữ liệu của chính mình.

| Key | Ai dùng | Quyền |
| :--- | :--- | :--- |
| **Anon Key** (`VITE_SUPABASE_URL` + anon) | Frontend (browser) | Bị RLS ràng buộc — chỉ thao tác dữ liệu của user đang đăng nhập |
| **Service Role Key** (`SUPABASE_SERVICE_ROLE_KEY`) | Backend Python (server-only) | **Bypass RLS** — ghi feedback/alerts hàng loạt. Tuyệt đối không để lộ ra browser/Git |

> ⚠️ Vì bảng `feedback`/`alerts` yêu cầu `user_id NOT NULL`, backend lấy 1 user bất kỳ trong `profiles` làm "user hệ thống" khi insert. Đây là lý do **phải đăng ký ít nhất 1 tài khoản trên Frontend trước khi chạy demo batch**.

### 8.3. Auth Flow & Trigger tự động

1. User đăng ký qua `/auth` → Supabase Auth tạo record trong `auth.users`.
2. Trigger `on_auth_user_created` → function `handle_new_user()` (SECURITY DEFINER) tự insert vào `profiles` (lấy `full_name` từ metadata, fallback từ email).
3. Mọi request sau đó mang JWT của user → RLS tự lọc dữ liệu.

### 8.4. Realtime — Trái tim của trải nghiệm "Dashboard tự đỏ"

```sql
-- Migration: enable_feedback_realtime.sql
ALTER PUBLICATION supabase_realtime ADD TABLE public.feedback;
```

- Dashboard subscribe channel `dashboard-live-feedback` trên bảng `feedback` → demo bắn 150 review là Live Feed nhảy số ngay.
- Trang Alerts subscribe `postgres_changes` trên bảng `alerts` → Alert Agent tạo ticket là thẻ cảnh báo **tự xuất hiện trên màn chiếu**, không ai phải bấm refresh.

### 8.5. Migrations & Biến môi trường

Schema quản lý bằng SQL migrations tại `supabase/migrations/` (các file: tạo bảng + RLS, policies bổ sung, bật realtime, correction logs). Áp dụng bằng Supabase CLI (đã đẩy ra root) hoặc dán vào SQL Editor.

| Biến | Frontend (`app/.env`) | Backend (`pipeline/.env` hoặc `.env` gốc) |
| :--- | :---: | :---: |
| `VITE_SUPABASE_URL` | ✅ | ✅ |
| Anon key (public) | ✅ | — |
| `SUPABASE_SERVICE_ROLE_KEY` | ❌ KHÔNG BAO GIỜ | ✅ |
| `GROQ_API_KEY` | ✅ (chỉ server function đọc) | ✅ |
| `GROQ_MODEL_NAME` | ✅ | ✅ |

---

## 9. Kế Hoạch Lập Trình Chi Tiết (Sprint Plan)

### Tuần 1: Cấu trúc hạ tầng & Đưa dự án lên Cloud ✅
*Mục tiêu: Đập tan rủi ro Deployment. Web phải truy cập được trên internet bằng URL thật.*
- Áp dụng file `.sql` lên Supabase Cloud tạo 4 bảng (`feedback`, `alerts`, `profiles`, `chat_messages`).
- Kết nối `supabase.ts` → Deploy **Vercel**. Kiểm tra luồng Auth.
- Tạo API gốc **FastAPI** (`main.py`) → Deploy **Railway/Render**.

### Tuần 2: Xây dựng Não trái (Data Pipeline & NLP) ✅
*Mục tiêu: Dữ liệu thô đi vào → Dữ liệu sạch có nhãn AI đi ra.*
- `pipeline/clean.py`: Regex giấu PII (SĐT, Email).
- `pipeline/classifier.py`: Load `.joblib` models + Rule-based (keyword "tai nạn" → severity P5).
- `pipeline/ingest.py`: Luồng Production (APScheduler) và Demo (API trigger 150 JSON) → Supabase.

### Tuần 3: Xây dựng Não phải (Multi-Agent System) ✅
*Mục tiêu: Hệ thống tự phát hiện "biến", tự phân luồng, tự tổng hợp insight và phân tích sâu.*
- `agents/router_agent.py`: Định tuyến config-driven từ `routing_table.json`, P5 ép về Safety SLA 1h.
- `agents/alert_agent.py`: Phân cấp WATCH/WARNING/CRITICAL + dedup cooldown — thay thế cơ chế "mọi spike đều P1".
- `agents/insight_agent.py`: Gom feedback + tickets 24h theo phòng ban, tính trend % so kỳ trước.
- `agents/analyst_agent.py`: Prompt LLM phân tích xuyên ticket → risk level, forecast, 3 recommendations.
- `agents/orchestrator.py`: Nối 7 bước thành vòng khép kín, cắm vào APScheduler (10 phút/lần).
- `main.py`: Mở 5 API mới (`/api/agent/*`, `/api/insights/*`).

### Tuần 4: Đánh bóng Front-end & Luyện Kịch Bản Demo
*Mục tiêu: Giao diện trực quan, chuyên nghiệp, vượt qua vòng nghiệm thu.*
- `Dashboard`: Biểu đồ Recharts (Line Chart, Bar Chart) + Heatmap khu vực.
- `Alerts/Ticket Triage`: Thẻ cảnh báo phân cấp màu (🟡🟠🔴), lọc theo tab phòng ban, realtime subscription.
- `Feedback`: Nút **[Edit Label]** sửa nhãn AI sai → Update Supabase (Human-in-the-loop).
- *(Gợi ý mở rộng)* Trang **Department Insights**: gọi `/api/insights/departments` vẽ bảng điều khiển riêng cho từng trưởng phòng.

---

## 10. Kịch Bản Demo Day (5 phút)

1. **Bật server** → APScheduler tự chạy nền.
2. **Bắn dữ liệu:** `POST /api/trigger-demo-batch` → 150 reviews đổ vào DB, dồn về `HN-Cau-Giay`.
3. **Kích hoạt Agent:** `POST /api/agent/run` → Orchestrator quét, Alert Agent phân cấp 🔴 CRITICAL, LLM sinh root cause, Router giao về đúng phòng.
4. **Dashboard đỏ rực** → Ticket Triage hiện alert theo từng phòng ban (realtime, không cần F5).
5. **Show Insight:** Mở `/api/insights/departments/Safety/deep-analysis` → AI chỉ ra nguyên nhân gốc rễ, dự báo 48h, 3 hành động kèm deadline.
6. **Human-in-the-loop:** Sửa 1 nhãn AI nhận diện nhầm trên trang Phản hồi.
7. **Chốt hạ:** Bắn thêm 1 đợt dữ liệu cùng khu vực → hệ thống **không spam alert trùng** (dedup hoạt động) — chứng minh đây là hệ thống production-ready, không phải demo "đốt pháo".
