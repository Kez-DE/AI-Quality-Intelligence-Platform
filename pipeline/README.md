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
| `ingest.py` | Đọc dataset → build payload → ghi bảng `feedback` |
| `spike_detector.py` | Gom feedback P4/P5 theo khu vực, vượt ngưỡng → spike |
| `llm_agent.py` | Gửi feedback vùng spike cho LLM → JSON alert (root cause, action, team) |
| `agent/model_router.py` | Chọn provider LLM (openrouter/openai/gemini/groq/mock) + log |
| `main.py` | FastAPI: endpoints batch, đọc feedback/alerts, chat agent |

## Lưu ý quan trọng

- **Severity P5 = nghiêm trọng nhất**, P1 = nhẹ nhất. Safety keyword (tai nạn, cướp, sàm sỡ...) luôn ép `Safety`/P5 và hạ confidence → buộc Human-in-the-Loop review.
- `feedback.user_id` NOT NULL ref `auth.users`, nên ingest cần ít nhất một tài khoản đã đăng ký trên frontend, và cần `SUPABASE_SERVICE_ROLE_KEY` (admin) để ghi.
- Không có key LLM nào → agent chạy chế độ **mock** (vẫn sinh alert mẫu, không gọi mạng). Đặt `LLM_PROVIDER` hoặc một API key trong `.env` để bật agent thật.
- Đây là **batch thủ công cho demo**, không phải real-time. Phần production (micro-batch/scheduler) nằm ngoài phạm vi đồ án — xem `docs/architecture.md`.
