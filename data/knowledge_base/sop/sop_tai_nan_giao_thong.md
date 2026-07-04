---
document_title: Quy trình xử lý Tai nạn Giao thông (SOP-SAFETY-01)
category: safety
department: Vận hành
severity_scope: [P5]
source: mock
tags: [tai-nan, khan-cap, cong-an, cap-cuu, bao-hiem]
---

# SOP-SAFETY-01 — Quy trình xử lý Tai nạn Giao thông

## Phạm vi áp dụng và mức độ ưu tiên

Quy trình này áp dụng cho mọi phản hồi hoặc báo cáo liên quan đến tai nạn giao thông
trong chuyến đi: va chạm, tông xe, lật xe, hành khách hoặc tài xế bị thương. Mọi case
thuộc nhóm này được gán **Severity P5 (Khẩn cấp)** và định tuyến **bắt buộc về Team
Safety** với **SLA 1 giờ**, bất kể số lượng phản hồi. Đây là mức nghiêm trọng nhất, kích
hoạt cảnh báo 🔴 CRITICAL ngay lập tức và không bị gộp dedup như các alert thông thường.

Nguyên tắc vàng: **An toàn tính mạng đặt trên mọi chỉ số vận hành.** Nhân viên trực phải
ưu tiên xử lý case P5 trước tất cả ticket khác trong hàng đợi.

## Bước 1 — Tiếp nhận và xác minh khẩn cấp (0–10 phút)

1. Gọi lại ngay cho hành khách qua số điện thoại trong hệ thống để xác minh tình trạng.
2. Hỏi 3 thông tin tối thiểu: (a) có người bị thương không, (b) vị trí hiện tại, (c) xe
   còn di chuyển được không.
3. Nếu có người bị thương: hướng dẫn gọi **115 (cấp cứu)** ngay, đồng thời Team Safety
   chủ động gọi hỗ trợ y tế đến vị trí.
4. Ghi nhận thời điểm tiếp nhận vào ticket; trạng thái ticket chuyển sang `in_progress`.

## Bước 2 — Phối hợp hiện trường và cơ quan chức năng (10–30 phút)

1. Nếu tai nạn có thiệt hại người/tài sản lớn: yêu cầu giữ nguyên hiện trường, hướng dẫn
   các bên gọi **113 (công an)** để lập biên bản.
2. Liên hệ tài xế qua kênh nội bộ, yêu cầu cung cấp ảnh hiện trường và biên bản (nếu có).
3. Kích hoạt **bảo hiểm chuyến đi**: gửi mã chuyến và thông tin tai nạn cho bộ phận
   Bảo hiểm để mở hồ sơ bồi thường.
4. Khóa tạm tài khoản tài xế nếu có dấu hiệu lỗi nghiêm trọng (vượt đèn đỏ, sử dụng rượu
   bia) cho đến khi điều tra xong.

## Bước 3 — Chăm sóc hành khách và đóng ticket (30–60 phút)

1. Sắp xếp chuyến xe thay thế miễn phí nếu hành khách cần tiếp tục di chuyển và đủ sức khỏe.
2. Áp chính sách bồi thường theo `sla_boi_thuong_chuan.md` mục Tai nạn (hoàn 100% cước +
   hỗ trợ chi phí y tế ban đầu theo hóa đơn).
3. Cập nhật toàn bộ diễn biến vào ticket; đính kèm hồ sơ bảo hiểm.
4. Chỉ chuyển ticket sang `resolved` khi: hành khách đã an toàn, hồ sơ bảo hiểm đã mở, và
   tài xế đã được xử lý (tạm khóa hoặc xác nhận không lỗi).

## Khi nào leo thang (Escalation)

- Có người tử vong hoặc nguy kịch → báo cáo trực tiếp Giám đốc Vận hành trong 15 phút.
- Báo chí/mạng xã hội đã đưa tin → kích hoạt thêm Team Truyền thông xử lý khủng hoảng.
- Quá SLA 1 giờ mà chưa liên hệ được hành khách → tự động escalate lên cấp quản lý Safety.
