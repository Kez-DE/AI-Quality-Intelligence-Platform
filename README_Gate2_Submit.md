# 🎯 Gate G2 — First Working Agent (MVP) · Submission

**Team 116 — C2-App-116 · AI Quality Intelligence Platform (xanhSM)**
*AI20K Build Cohort 2*

Agent nhận **input** (phản hồi khách hàng) → **xử lý** (làm sạch PII → phân loại ML + rule engine → phát hiện spike → LLM phân tích) → trả **output có nghĩa** (topic / sentiment / severity + alert định tuyến đúng phòng ban). Chạy **end-to-end với LLM thật** — OpenRouter / OpenAI / Gemini / Groq, **không mock**.

> File này tổng hợp đúng các deliverable Gate G2 yêu cầu và trỏ tới vị trí từng phần.
> Hướng dẫn dự án đầy đủ: [`README.md`](README.md).

---

## ✅ Checklist Deliverables

| # | Deliverable yêu cầu | Trạng thái | Vị trí trong repo |
|---|---------------------|:----------:|-------------------|
| 1 | **MVP Demo** — video 3 phút show user flow end-to-end | 🎬 | [👉 Link Google Drive](https://drive.google.com/REPLACE_WITH_YOUR_LINK) _(cập nhật sau khi upload)_ |
| 2 | **Architecture diagram** — sơ đồ components, data flow | ✅ | [`docs/architecture-diagram.md`](docs/architecture-diagram.md) (Mermaid) · [`docs/architecture.md`](docs/architecture.md) (chi tiết) |
| 3 | **Repo ≥ 10 PR merged** | ✅ | [Pull Requests (merged)](https://github.com/AI20K-Build-Cohort-2/C2-App-116/pulls?q=is%3Apr+is%3Amerged) |
| 4 | **README** — setup, env vars, sample queries | ✅ | [`README.md`](README.md) · env: [`.env.example`](.env.example) · sample queries: [mục bên dưới](#-sample-queries) |
| 5 | **Eval evidence** — ≥ 5 test case, output thật | ✅ | [`docs/eval-evidence.md`](docs/eval-evidence.md) (6 case, tái lập bằng `pipeline/eval/manual_eval.py`) |

---

## 1. 🎬 MVP Demo (video 3 phút)

- **Link:** https://drive.google.com/REPLACE_WITH_YOUR_LINK
- Nội dung: review thô → tự gán nhãn → streaming → spike → alert định tuyến phòng ban → Human-in-the-Loop.
- Kịch bản tham chiếu: [`docs/demo-script.md`](docs/demo-script.md).

> ⚠️ Nhớ đặt quyền chia sẻ Google Drive = **"Anyone with the link can view"** và dán link thật thay cho `REPLACE_WITH_YOUR_LINK`.

## 2. 🗺️ Architecture diagram

- [`docs/architecture-diagram.md`](docs/architecture-diagram.md) — 4 sơ đồ Mermaid (GitHub render trực tiếp): component tổng quan, data flow user flow chính, Human-in-the-Loop, LLM failover.
- [`docs/architecture.md`](docs/architecture.md) — mô tả chi tiết từng module, 2 chế độ chạy, phân loại 2 tầng.

## 3. 🔀 Repo ≥ 10 PR merged

- Xem: [github.com/AI20K-Build-Cohort-2/C2-App-116/pulls?q=is:pr+is:merged](https://github.com/AI20K-Build-Cohort-2/C2-App-116/pulls?q=is%3Apr+is%3Amerged)
- Repo có 100+ commit, nhiều nhánh tính năng (`docs`, `kez/streaimg-poject`, `feat/admin-ui-vietnamese`, …) được merge qua PR.

## 4. 📖 README — setup & env vars

- Setup chi tiết: [`README.md`](README.md#cài-đặt-nhanh) · theo OS: [`docs/setup-windows.md`](docs/setup-windows.md), [`docs/setup-macos.md`](docs/setup-macos.md), [`docs/setup-supabase.md`](docs/setup-supabase.md).
- Biến môi trường mẫu: [`.env.example`](.env.example).

### 🔎 Sample queries

Backend chạy ở `http://127.0.0.1:8000`. Lấy `ADMIN_TOKEN` (JWT Supabase của admin) rồi thử:

```bash
# 1. Health check — xác nhận provider LLM + key đang sống
curl http://127.0.0.1:8000/health

# 2. Phân loại 1 phản hồi (input -> output có nghĩa, không mock)
curl -X POST http://127.0.0.1:8000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{"content":"Tài xế say xỉn gây tai nạn rồi bỏ chạy","channel":"app","area_code":"HN-Cau-Giay"}'
#   -> {"topic":"Safety","sentiment":"negative","severity":"P5","needs_review":true,...}

# 3. Bật streaming 50 review/giây -> spike -> alert tự sinh
curl -X POST "http://127.0.0.1:8000/api/live-stream/start?batch_size=50&interval_seconds=1&loop=false&auto_ticket=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 4. Phân tích sâu 1 phòng ban bằng LLM thật (multi-agent)
curl "http://127.0.0.1:8000/api/insights/departments/Safety?with_analysis=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 5. AI Chat — hỏi đáp tự nhiên trên dữ liệu phản hồi
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"message":"Khu vực nào đang nóng nhất tuần này?"}'
```

## 5. 🧪 Eval evidence (≥ 5 test case, output thật)

- Bằng chứng đầy đủ: [`docs/eval-evidence.md`](docs/eval-evidence.md) — 6 test case chạy qua **model + rule thật** (Safety override, lỗi app, gian lận thanh toán, phản hồi tích cực, thiếu cung, PII masking).
- Tái lập (không cần server):

  ```bash
  cd pipeline
  pip install -r requirements.txt
  PYTHONIOENCODING=utf-8 python eval/manual_eval.py
  ```

| # | Test case | Output thật | Đạt |
|---|-----------|-------------|:---:|
| TC-01 | Tài xế say xỉn gây tai nạn… | `Safety / negative / P5 / needs_review=true` | ✅ |
| TC-02 | App bị lỗi không đặt được xe | `App Issue / negative / P3 / conf 0.82` | ✅ |
| TC-03 | Tài xế thu tiền gấp đôi… | `Payment / negative / P3 / conf 0.75` | ✅ |
| TC-04 | Tài xế thân thiện, an toàn… | `Driver Behavior / positive / P1 / conf 0.88` | ✅ |
| TC-05 | Gọi xe mãi không có tài xế… | `Other / negative / P3 / conf 0.662` | ✅ |
| TC-06 | SĐT/email/biển số | Ẩn `[SĐT_ĐÃ_ẨN] [EMAIL_ĐÃ_ẨN] [BIỂN_SỐ_ĐÃ_ẨN]` | ✅ |

---

*Mọi đường dẫn file đều tương đối từ gốc repo. Cập nhật link Google Drive ở mục 1 trước khi nộp.*
