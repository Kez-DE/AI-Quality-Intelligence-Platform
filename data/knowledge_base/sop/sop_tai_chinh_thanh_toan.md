---
document_title: Quy trình xử lý Khiếu nại Thanh toán & Hoàn tiền (SOP-FIN-01)
category: payment
department: Tài chính & Thanh toán
severity_scope: [P2, P3, P4]
source: mock
tags: [thanh-toan, hoan-tien, tru-tien-sai, doi-soat, vi-dien-tu, hoa-don]
---

# SOP-FIN-01 — Quy trình xử lý Khiếu nại Thanh toán & Hoàn tiền

## Phạm vi và mức độ

Áp dụng khi hành khách khiếu nại về tiền: bị trừ tiền sai, trừ hai lần cho một chuyến,
cước hiển thị khác cước bị trừ, voucher/khuyến mãi không áp, hoặc ví điện tử báo giao dịch
lỗi. Không bao gồm cáo buộc tài xế thu thêm tiền mặt hoặc vòi vĩnh — ca đó thuộc
`Quản lý Rủi ro & Gian lận`. Phần lớn khiếu nại thanh toán ở mức P3; trừ hai lần hoặc số
tiền lớn nâng lên P2.

## Bước 1 — Xác minh giao dịch (0–2 giờ)

1. Lấy mã chuyến và mã giao dịch từ hành khách; đối chiếu với cổng thanh toán (thẻ, ví,
   tiền mặt) và log hệ thống.
2. So sánh cước chuẩn theo lộ trình với số tiền thực bị trừ. Ghi rõ chênh lệch.
3. Kiểm tra trạng thái voucher/khuyến mãi tại thời điểm đặt chuyến: điều kiện áp dụng, hạn
   dùng, đã dùng cho chuyến khác chưa.

## Bước 2 — Phân loại và xử lý

1. **Trừ hai lần / trừ khi chuyến đã hủy:** hoàn 100% phần thừa trong 24 giờ, gửi xác nhận
   cho khách. Nếu lỗi cổng thanh toán, phối hợp `IT` mở ticket kỹ thuật.
2. **Voucher không áp do lỗi hệ thống:** hoàn phần chênh lệch tương ứng giá trị voucher.
3. **Voucher không áp do khách không đủ điều kiện:** giải thích điều kiện, không hoàn; ghi
   log để tránh khiếu nại lặp.
4. **Ví điện tử báo lỗi nhưng tiền chưa về:** hướng dẫn khách chờ chu kỳ đối soát của nhà
   cung cấp ví (thường 3–5 ngày làm việc), mở ticket theo dõi.

## Bước 3 — Đối soát và chốt

1. Cập nhật kết quả vào ticket, đính kèm bằng chứng đối soát.
2. Giao dịch hoàn tiền phải khớp sổ đối soát cuối ngày. Chênh lệch chưa khớp giữ trạng thái
   `in_progress`, không đóng ticket.
3. SLA phản hồi lần đầu: 4 giờ. SLA hoàn tất hoàn tiền: 24 giờ (trừ ca phụ thuộc nhà cung
   cấp ví).
