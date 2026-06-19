---
document_title: Hướng dẫn xử lý Lỗi Thanh toán (TECH-IT-01)
category: app
department: IT
severity_scope: [P2, P3]
source: mock
tags: [thanh-toan, the, vi-dien-tu, tru-tien-sai, hoan-tien]
---

# TECH-IT-01 — Hướng dẫn xử lý Lỗi Thanh toán

## Phạm vi

Áp dụng cho lỗi liên quan thanh toán trong app: trừ tiền sai/trùng, thẻ bị từ chối, ví điện
tử không liên kết được, đã thanh toán nhưng app báo nợ cước. Topic **Payment** → route
**CSKH** (SLA 12 giờ); nếu xác định lỗi hệ thống thì phối hợp **Team IT** để fix gốc.

## Lỗi 1 — Trừ tiền hai lần (trùng giao dịch)

**Triệu chứng:** Khách báo bị trừ 2 lần cho cùng một chuyến.

1. Tra mã chuyến + mã giao dịch trong cổng thanh toán, xác nhận có 2 bút toán trùng.
2. Nếu đúng trùng: tạo yêu cầu hoàn 1 giao dịch; thời gian hoàn 24–72 giờ tùy ngân hàng/ví.
3. Thông báo khách thời gian hoàn dự kiến, đính kèm mã yêu cầu hoàn vào ticket.

## Lỗi 2 — Thẻ bị từ chối khi thanh toán

**Triệu chứng:** App báo "thanh toán thất bại" dù thẻ còn hạn mức.

1. Kiểm tra thẻ đã bật thanh toán trực tuyến (OTP/3D-Secure) chưa.
2. Hướng dẫn khách xóa thẻ và liên kết lại; thử lại với ví điện tử nếu thẻ vẫn lỗi.
3. Nếu nhiều khách cùng lỗi với một ngân hàng → nghi sự cố cổng thanh toán, escalate IT.

## Lỗi 3 — Đã trả nhưng app vẫn báo nợ cước

**Triệu chứng:** Khách bị treo nợ cước cũ, không đặt được chuyến mới.

1. Đối chiếu lịch sử thanh toán với bút toán thực tế ở cổng.
2. Nếu khách đã trả: gỡ treo nợ thủ công, mở khóa đặt chuyến ngay.
3. Nếu thực sự chưa trả: hướng dẫn thanh toán lại, giải thích rõ khoản nợ.

## Khi nào escalate sang IT (fix gốc)

- Lỗi xảy ra hàng loạt cùng thời điểm (dấu hiệu sự cố cổng/thanh toán toàn hệ thống).
- Lỗi tái diễn sau cập nhật app mới → gắn nhãn regression, báo Team Product.
- Số tiền treo/sai lớn bất thường → ưu tiên xử lý và rà soát toàn bộ giao dịch liên quan.
