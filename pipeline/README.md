# Pipeline — Python ML + Agent (batch mode)

Xử lý phản hồi khách hàng theo lô: làm sạch PII → phân loại (TF-IDF + LinearSVC) → safety rule → ghi Supabase → phát hiện spike → agent LLM sinh alert/ticket.

Tầng này chạy độc lập với frontend. Frontend đọc kết quả từ Supabase; pipeline ghi vào Supabase. Không có server trung gian.

## Yêu cầu

- Python 3.10+ (đã test trên 3.14)
- `scikit-learn==1.6.1` — phải khớp version đã train model `.joblib`, nếu lệch sẽ có `InconsistentVersionWarning` và kết quả có thể sai.

## Cài đặt

```bash
cd pipeline
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Cấu hình `.env` ở **gốc repo** (không tạo `.env` riêng trong `pipeline/`). Copy từ `.env.example` rồi điền key. Tối thiểu cần `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` để ghi dữ liệu.

## Chạy

Khởi động API (chế độ batch, live-stream mặc định tắt):

```bash
cd pipeline
python main.py        # http://localhost:8000  — Swagger: /docs
```

Luồng demo end-to-end (bấm một nút):

```bash
# Nạp lô đánh giá vào feedback, rồi detect spike + agent
curl -X POST "http://localhost:8000/api/run-real-pipeline?limit=150&batch_size=150"

# Hoặc ép quét spike ngay
curl -X POST "http://localhost:8000/api/trigger-spike-detect"
```

## Thành phần

| File | Vai trò |
| :--- | :--- |
| `clean.py` | Làm sạch text, mask SĐT/email (PII) |
| `classifier.py` | Load model `.joblib`, predict topic+sentiment, suy severity, safety override |
| `ingest.py` | Phễu lọc 3 tầng: Đọc dataset → Lọc ML → Chạy Batch LLM Scoring → Ghi DB |
| `agents/scoring_agent.py`| **Scoring Agent**: Chấm điểm rủi ro 5 chiều (Deep Risk Matrix) + Waterfall. |
| `agents/router_agent.py` | **Router Agent**: Định tuyến ticket về đúng team dựa trên `routing_table.json`. |
| `agents/alert_agent.py`  | **Alert Agent**: Phát hiện spike, phân cấp cảnh báo WATCH/WARNING/CRITICAL. |
| `agents/insight_agent.py`| **Insight Agent**: Zero-LLM, dùng SQL gom cụm metric cho từng team. |
| `agents/analyst_agent.py`| **Analyst Agent**: Phân tích nguyên nhân gốc rễ và đưa ra Action Plan. |
| `agents/task_agent.py`   | **Task Agent**: Gom cụm Alert (Heuristic) → Task lớn & Sinh Báo cáo Markdown. |
| `agents/orchestrator.py` | **Orchestrator**: Vòng lặp khép kín điều phối các agent định kỳ. |
| `main.py` | FastAPI: endpoints batch, đọc feedback/alerts/tasks/reports. |

## Lưu ý quan trọng

- **Severity P5 = nghiêm trọng nhất**, P1 = nhẹ nhất. Safety keyword (tai nạn, cướp, sàm sỡ...) luôn ép `Safety`/P5 và hạ confidence → buộc Human-in-the-Loop review.
- `feedback.user_id` NOT NULL ref `auth.users`, nên ingest cần ít nhất một tài khoản đã đăng ký trên frontend, và cần `SUPABASE_SERVICE_ROLE_KEY` (admin) để ghi.
- Không có key LLM nào → agent chạy chế độ **mock** (vẫn sinh alert mẫu, không gọi mạng). Đặt `LLM_PROVIDER` hoặc một API key trong `.env` để bật agent thật.
- **Đây là batch thủ công cho demo**, không phải real-time. Phần production (micro-batch/scheduler) nằm ngoài phạm vi đồ án — xem `docs/architecture.md`.

## Test nhanh tính năng (Demo / Admin)

### a) Lấy token admin (dùng cho các lệnh curl bên dưới)
```bash
cd pipeline
TOKEN=$(.venv/bin/python - <<'PY'
import os; from dotenv import load_dotenv; load_dotenv("../.env")
from supabase import create_client
c=create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_PUBLISHABLE_KEY"])
r=c.auth.sign_in_with_password({"email":"demo.20260606180215@example.com","password":"Admin@12345"})
print(r.session.access_token)
PY
)
echo "${TOKEN:0:20}..."
```

### b) Streaming 50 review/giây (luồng chính)
```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
 "http://127.0.0.1:8000/api/live-stream/start?batch_size=50&interval_seconds=1&loop=false&reset=true&auto_ticket=true&ticket_every_batches=10"

# theo dõi tiến độ (chạy lại nhiều lần để thấy số tăng):
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/live-stream/status

# dừng giữa chừng nếu cần:
curl -s -X POST -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/live-stream/stop
```

### c) Nút "bắn 1 lô" demo an toàn (không cần streaming)
```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
 "http://127.0.0.1:8000/api/ingest-real-dataset?limit=150&batch_size=150"
```

### d) Trigger ticket thủ công (gọi LLM thật, ~10–25s)
```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
 "http://127.0.0.1:8000/api/trigger-spike-detect?max_feedback=1000&max_spikes=3"
```

### e) Multi-agent — insight theo phòng ban
```bash
# 1 phòng ban (kèm phân tích root cause của LLM):
curl -s -H "Authorization: Bearer $TOKEN" \
 "http://127.0.0.1:8000/api/insights/departments/Safety?with_analysis=true"

# toàn bộ 6 phòng ban (chạy ~2 phút vì gọi LLM nhiều lần):
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
 "http://127.0.0.1:8000/api/agent/run?hours=24"
```

### f) Chat AI (test trực tiếp backend)
```bash
curl -s -X POST -H "Content-Type: application/json" \
 -d '{"messages":[{"role":"user","content":"Khu vực nào tiêu cực nhất?"}]}' \
 http://127.0.0.1:8000/api/agent/chat
```
