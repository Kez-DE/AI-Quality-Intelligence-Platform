---
document_title: Quy trình xử lý vi phạm An toàn Giao thông - Lái xe nguy hiểm (SOP-SAFETY-02)
category: safety
department: Vận hành
severity_scope: [P4, P5]
source: mock
tags: [chay-au, vuot-den-do, lang-lach, toc-do, an-toan, say-xin]
---

# SOP-SAFETY-02 — Quy trình xử lý vi phạm An toàn Giao thông (Lái xe nguy hiểm)

## Phạm vi áp dụng và mức độ ưu tiên

Áp dụng cho các phản ánh về hành vi lái xe không an toàn: **chạy ẩu, lạng lách đánh võng, vượt đèn đỏ, đi ngược chiều, chạy quá tốc độ**, hoặc tài xế có dấu hiệu say xỉn/sử dụng chất kích thích.
Mức độ đánh giá:
- **P4 (Nghiêm trọng)**: Chạy ẩu, phanh gấp nhiều lần, chạy quá tốc độ nhưng chưa gây hậu quả. SLA xử lý 8 giờ.
- **P5 (Khẩn cấp)**: Lái xe trong tình trạng say xỉn, vượt đèn đỏ ở giao lộ, đi ngược chiều trên đường lớn/cao tốc. Route lập tức về **Team Safety** với SLA 1-2 giờ.

## Bước 1 — Tiếp nhận và đánh giá khẩn cấp (0–1 giờ)

1. Ghi nhận nguyên văn mô tả của khách hàng (vị trí, thời điểm, hành vi cụ thể).
2. Xác nhận an toàn: Hỏi xem khách hàng đã kết thúc chuyến đi chưa. Nếu khách vẫn đang trên chuyến và cảm thấy bị đe dọa an toàn, tổng đài viên hướng dẫn khách yêu cầu dừng xe ở vị trí đông người/an toàn gần nhất, đồng thời Team Safety sẽ can thiệp định vị.

## Bước 2 — Trích xuất dữ liệu và xác minh (1–4 giờ)

1. **Trích xuất Telematics (GPS & Cảm biến)**: Kiểm tra dữ liệu chuyến đi trên hệ thống để xác nhận tốc độ tối đa, các lần phanh gấp (hard braking), hoặc quỹ đạo di chuyển bất thường (lạng lách).
2. **Liên hệ tài xế**: Gọi điện xác minh. Lưu ý giọng nói của tài xế (có dấu hiệu buồn ngủ hoặc say xỉn không). Đối chiếu giải trình của tài xế với dữ liệu GPS.

## Bước 3 — Áp dụng kỷ luật và xoa dịu hành khách (SLA 8 giờ)

1. **Kỷ luật tài xế**:
   - Vi phạm P4 (chạy ẩu thông thường, lần đầu): Cảnh cáo nặng, trừ điểm uy tín, tạm khóa tài khoản 3-7 ngày và bắt buộc tham gia lại khóa đào tạo An toàn giao thông.
   - Vi phạm P5 (say xỉn, vượt đèn đỏ, đi ngược chiều): Khóa tài khoản vĩnh viễn (Blacklist) ngay lập tức.
2. **Hỗ trợ khách hàng**: Gọi lại xin lỗi khách hàng, thông báo rõ hình thức đã kỷ luật tài xế để khách hàng yên tâm. Áp dụng chính sách bồi thường (thường là hoàn cước chuyến đi và tặng thêm voucher 50.000đ - 100.000đ).
3. Đóng ticket sang trạng thái `resolved` đính kèm biên bản GPS.

## Câu trả lời chuẩn cho tình huống "tài xế chạy ẩu"

"Dạ XanhSM rất xin lỗi về trải nghiệm thiếu an toàn của anh/chị. Hành vi lái xe lạng lách/chạy ẩu là vi phạm nghiêm trọng tiêu chuẩn an toàn của hãng. Bên em đã ghi nhận mã chuyến đi và sẽ lập tức trích xuất dữ liệu GPS để đối soát. Tài xế sẽ bị xử lý kỷ luật nghiêm khắc (có thể khóa tài khoản) nếu hệ thống ghi nhận vi phạm. Em xin phép hoàn cước chuyến này và bộ phận Safety sẽ cập nhật kết quả xử lý đến anh/chị trong vòng 8 giờ tới ạ."
