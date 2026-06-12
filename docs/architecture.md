# Kiến trúc — AI Quality Intelligence Platform

Dự án AI20K-223. Phân tích phản hồi khách hàng smart mobility (xanhSM) và định tuyến sự cố tới đúng phòng ban.

## Một repo, ba tầng

```
C2-App-116/
├── app/        Frontend TanStack Start + React 19 (Quality Cockpit, auth, chat)
├── pipeline/   Python: clean → classify → ingest → spike detect → LLM agent
├── supabase/   Schema PostgreSQL (profiles, feedback, alerts, chat_messages)
└── data/       Dataset public review + metadata synthetic + train splits
```

Supabase là trục nối: pipeline Python **ghi** kết quả, frontend **đọc** để hiển thị. Không có backend server trung gian cho phần đọc — frontend gọi thẳng Supabase qua RLS.

## Luồng xử lý

```
Review (demo 150 / dataset 4837)
   │
   ▼
[1] clean.py        mask PII (SĐT, email), chuẩn hóa text
   │
   ▼
[2] classifier.py   TF-IDF + LinearSVC → topic (7 lớp) + sentiment
   │                 → severity suy từ sentiment (P1..P5, P5 nặng nhất)
   │                 → Safety rule override: keyword nguy hiểm ép P5 + hạ confidence
   ▼
[3] ingest.py       ghi vào Supabase feedback (dùng nhãn sẵn nếu data đã label)
   │
   ▼
[4] spike_detector  group by area, đếm P4/P5 trong cửa sổ thời gian
   │                 ≥ ngưỡng → spike
   ▼
[5] llm_agent.py    gửi review của vùng spike cho LLM → JSON
   │                 {title, root cause, action, assigned_team}
   ▼
[6] alerts          ghi alert vào Supabase → frontend hiển thị
```

## Hai chế độ chạy

Hệ thống chạy thật end-to-end với **hai chế độ song song**, dùng chung pipeline xử lý:

**1. Streaming (luồng chính) — gần real-time**
- `POST /api/live-stream/start` bật APScheduler tự bơm từng batch review theo `interval_seconds`.
- Sau mỗi `ticket_every_batches` lô, hệ thống tự chạy spike detect → LLM phân tích → ghi alert.
- Ticket workflow tự chuyển trạng thái `open → in_progress → resolved` theo thời gian.
- Frontend subscribe Supabase realtime (`postgres_changes`) → dashboard tự cập nhật, không cần reload.
- Bật/tắt bằng `LIVE_STREAM_ENABLED` hoặc API runtime.

**2. Batch thủ công — nút bấm demo an toàn**
- `POST /api/run-real-pipeline` / `POST /api/trigger-spike-detect`: bắn một lô 100–150 review và sinh alert ngay.
- Dùng trên sân khấu khi không muốn phụ thuộc nhịp scheduler / mạng / LLM lúc demo trực tiếp.

Cả hai đã verify chạy thật: streaming bơm 1.860 review tự động qua scheduler; LLM thật (OpenRouter) sinh alert root-cause đa tầng và định tuyến phòng ban.

## Demo vs Production

| Khía cạnh | Cái đang build (chạy thật) | Production đầy đủ (nếu mở rộng) |
| :--- | :--- | :--- |
| Ingest | Streaming scheduler + batch thủ công, nguồn là dataset đóng gói | Hút review real-time trực tiếp từ store/app |
| Data | Public store review + metadata synthetic | Dữ liệu vận hành thật của hãng |
| Thông báo | Realtime trên dashboard | Push tới Slack/email/app tài xế |
| Hạ tầng | Supabase cloud + chạy local | Container hóa, CI/CD, monitoring, auth/roles đầy đủ |

## ML — distillation, không train lại từ đầu

Model `.joblib` (TF-IDF + LinearSVC) train trên nhãn do LLM sinh trước đó (distillation). Đây là quyết định cố ý: rẻ, nhanh, đủ chính xác cho demo.

Độ chính xác đo trên `data/train/test_split.json` (932 mẫu có nhãn):
- Topic: 77.1%
- Sentiment: 94.3%

Safety là rule cứng đặt **trên** model: bất kỳ review chứa keyword nguy hiểm (tai nạn, cướp, sàm sỡ...) đều bị ép `Safety / P5 / confidence 0.3`, buộc Human-in-the-Loop review lại. Rule luôn thắng model để không bỏ sót ca an toàn.

## LLM provider

`pipeline/agent/model_router.py` hỗ trợ nhiều provider (OpenRouter, OpenAI, Gemini, Groq) + mock. Chọn theo `LLM_PROVIDER` trong `.env`; mặc định `auto` lấy key đầu tiên có sẵn. Không có key → chạy mock (vẫn sinh alert giả lập để demo luồng).
