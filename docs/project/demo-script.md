# Kịch bản demo — 5–7 phút

> **Cập nhật 2026-06-27:** phản ánh trạng thái hoàn thành (task loop, HI-loop, hybrid RAG, 6 phòng).

Mục tiêu: cho hội đồng thấy luồng từ review thô qua phân loại, spike, alert định tuyến 6 phòng ban, vòng duyệt nhãn (Human-in-the-Loop), vòng khép kín báo cáo → task (HI-Loop Approval), và AI Chat tiered RBAC.

## Chuẩn bị trước (không tính giờ)

1. Điền `.env` ở root từ `.env.example`: Supabase URL + service role key + ít nhất 1 LLM key (OpenRouter). `LLM_PROVIDER=auto`.
2. Áp migration lên Supabase: `supabase db push` (hoặc đã áp sẵn).
3. Có sẵn tài khoản admin (`manhnguyn1912@gmail.com` / `Admin@12345`).
4. Chạy 2 terminal theo `docs/project/setup-macos.md` hoặc `docs/project/setup-windows.md`: backend (8000) + frontend (5174).
5. (Tuỳ chọn) `POST /api/feedback/reclassify` để data cũ mang nhãn mới.

## Trên sân khấu

**Phút 0–1 — Bối cảnh.** Mở dashboard. Bài toán: hàng nghìn review/ngày, đội vận hành không kịp đọc, sự cố an toàn dễ bị chôn vùi → cần phát hiện sớm + định tuyến tự động.

**Phút 1–2 — Thu thập + tự gán nhãn.** Mở trang Phản hồi. Gõ một review (chỉ nhập nội dung + kênh + chọn khu vực từ dropdown — KHÔNG chọn cảm xúc/severity). Nhấn gửi → AI tự gán topic/sentiment/severity + confidence. Nhấn mạnh: người gửi không khai nhãn, máy phân tích.

**Phút 2–3 — Streaming.** Bật live-stream 50 review/giây:

```bash
curl -X POST "http://localhost:8000/api/live-stream/start?batch_size=50&interval_seconds=1&loop=false&auto_ticket=true" -H "Authorization: Bearer <admin_token>"
```

Dashboard và danh sách phản hồi đổ dữ liệu liên tục theo thời gian thực (realtime, không reload).

**Phút 3-4 (Spike → Alert → Ticket).** Khi vùng nào dồn P4/P5 vượt ngưỡng → spike detector bắt → LLM thật phân tích → sinh alert. Mở tab Alerts, click một alert đỏ: đọc root cause + action + phòng ban được giao (Vận hành/IT/CSKH tùy topic). Ticket tự chuyển trạng thái open→in_progress→resolved.

**Phút 4–5 — Review Queue + Safety.** Trên trang Phản hồi, chỉ vào 2 section: **Cần duyệt** (P5/safety/confidence thấp) và **Luồng phản hồi**. Review "tai nạn/say xỉn" tự vào Review Queue với badge lý do. Nhấn mạnh: rule Safety ép P5 dù model nghĩ khác — an toàn không nhường xác suất.

**Phút 5–6 — Human-in-the-Loop.** Trong Review Queue, lấy một ca AI gán sai/không chắc. Bấm **Sửa nhãn** → chọn nhãn đúng → Lưu. Giải thích: nhãn sửa ghi vào `correction_logs` (audit + dữ liệu retrain), ca rời khỏi Queue. Hoặc bấm **Duyệt** nếu nhãn AI đã đúng.

**Phút 6–7 — Multi-agent (tuỳ chọn).** Mở insight theo phòng ban:

```bash
curl "http://localhost:8000/api/insights/departments/IT?with_analysis=true" -H "Authorization: Bearer <admin_token>"
```

Mỗi phòng ban có một "trợ lý AI" tổng hợp vấn đề cốt lõi + đề xuất hành động.

**Phút 7-8 (tùy chọn): Báo cáo AI → Task (HI-Loop Approval).** Vào trang Báo cáo AI. Chọn một báo cáo có đề xuất hành động. Nhấn "Sửa Draft Task" để biên tập nội dung task (phạm vi, ưu tiên). Nhấn "Duyệt và triển khai task". Chuyển sang Task Board: task mới xuất hiện với badge "Từ báo cáo" và liên kết ngược về báo cáo gốc. Nhấn mạnh: luồng khép kín từ phản hồi → phân tích → hành động được phê duyệt.

**Phút 8-9 (tùy chọn): AI Chat tiered RBAC.** Mở trang AI Chat dưới tài khoản admin/manager. Hỏi "khu vực nào đang nóng?" hoặc "tuần này Vận hành có vấn đề gì?". Chat truy vấn Knowledge Base nội bộ qua Hybrid Search (Cohere embed-multilingual-v3.0 + BM25-lite + RRF k=60). Sau đó thử đăng nhập tài khoản guest và hỏi cùng câu hỏi: guest chỉ nhận FAQ công khai, không thấy dữ liệu nội bộ. Nhấn mạnh: cùng giao diện chat, phân quyền tự động theo role.

## Câu hỏi hay gặp

- *Data thật không?* Review tiếng Việt thật từ App Store/Google Play. Metadata vận hành (area, driver_id, trip_id, spike flag) là synthetic cho demo. Xem `data/README.md`.
- *Real-time chứ?* Có — streaming 50 review/giây qua scheduler. Cũng có batch thủ công cho demo an toàn.
- *Model gì?* TF-IDF + LinearSVC (distill từ nhãn LLM) + rule engine bù câu ngắn/từ khóa. Topic 77%, sentiment 94% trên test set.
- *AI gán sai thì sao?* Confidence thấp → vào Review Queue → người duyệt/sửa → ghi correction_logs. Vòng học khép kín.
- *Phụ thuộc 1 API key?* Không — failover tự nhảy provider có key sống (OpenRouter→OpenAI→Gemini→Groq→mock).
- *Phân quyền?* RBAC 4 role (admin/manager/staff/guest), login Supabase Auth, nút vận hành gate theo role.
