# Kịch bản demo — 5 phút

Mục tiêu: cho hội đồng thấy luồng khép kín từ review thô tới alert định tuyến phòng ban, có cả vòng người sửa nhãn.

## Chuẩn bị trước (không tính giờ)

1. Điền `.env` ở root từ `.env.example`: Supabase URL + service role key, và một LLM key (hoặc để trống chạy mock).
2. Áp schema lên Supabase: chạy các file trong `supabase/migrations/`.
3. Tạo 1 tài khoản trên frontend (ingest cần `user_id` thật vì `feedback.user_id` ref `auth.users`).
4. Cài pipeline:
   ```bash
   cd pipeline
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

## Trên sân khấu

**Phút 0–1 — Bối cảnh.** Mở dashboard đang trống/bình thường. Nói về bài toán: hàng nghìn review, đội vận hành không kịp đọc, sự cố an toàn dễ bị chôn vùi.

**Phút 1–2 — Bấm nút bắn review.** Chạy:
```bash
curl -X POST "http://localhost:8000/api/run-real-pipeline?limit=150&batch_size=150"
```
Giải thích: 150 review đi qua clean → classify → ghi Supabase. Dashboard bắt đầu có số.

**Phút 2–3 — Spike + alert.** Trong 150 review demo có ~30 record cắm spike ở Cầu Giấy. Spike detector bắt vùng P4/P5 vượt ngưỡng → LLM phân tích → sinh alert. Mở tab Alerts, click vào một alert đỏ: đọc root cause + phòng ban được giao (Safety / Vận hành / IT).

**Phút 3–4 — Safety override.** Lọc feedback topic = Safety. Chỉ ra các review "tai nạn", "tài xế say" đều bị ép P5 dù model có thể nghĩ khác. Đây là rule cứng — an toàn không nhường cho xác suất.

**Phút 4–5 — Human-in-the-Loop.** Mở một feedback bị phân loại sai (confidence thấp), bấm sửa nhãn. Giải thích nhãn sửa được lưu lại làm dữ liệu retrain — vòng học khép kín.

## Câu hỏi hay gặp

- *Data thật không?* Review là tiếng Việt thật từ App Store/Google Play. Metadata vận hành (area, driver_id, trip_id, spike flag) là synthetic cho demo. Xem `data/README.md`.
- *Real-time chứ?* Demo chạy batch thủ công. Code có sẵn live-stream nhưng tắt mặc định. Production sẽ là micro-batch.
- *Model gì?* TF-IDF + LinearSVC, distill từ nhãn LLM. Topic 77%, sentiment 94% trên test set.
