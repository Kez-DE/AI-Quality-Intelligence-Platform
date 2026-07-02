---
document_title: Quy trình xử lý Phản hồi Sản phẩm & Lỗi Tính năng App (SOP-PROD-01)
category: product
department: Sản phẩm
severity_scope: [P2, P3, P4]
source: mock
tags: [san-pham, loi-tinh-nang, app, ux, backlog, phan-hoi-tinh-nang]
---

# SOP-PROD-01 — Quy trình xử lý Phản hồi Sản phẩm & Lỗi Tính năng App

## Phạm vi và mức độ

Áp dụng cho phản hồi về trải nghiệm sản phẩm: tính năng khó dùng, luồng đặt xe gây nhầm
lẫn, bản đồ/định vị sai trong app, đề xuất tính năng mới. Không bao gồm lỗi hạ tầng/crash
server (thuộc `IT`) hay lỗi trừ tiền (thuộc `Tài chính & Thanh toán`). Đa số ở mức P3–P4;
lỗi chặn luồng đặt xe cho nhiều người dùng nâng lên P2.

## Bước 1 — Tái hiện và phân loại (0–1 ngày)

1. Ghi lại thiết bị, phiên bản app, hệ điều hành, và các bước tái hiện từ phản hồi khách.
2. Phân biệt ba nhóm: **bug** (hành vi sai so với thiết kế), **vấn đề UX** (hoạt động đúng
   nhưng gây khó), **đề xuất tính năng** (chưa có).
3. Với nghi ngờ bug ảnh hưởng nhiều người, kiểm tra có phản hồi tương tự trong 7 ngày để
   ước lượng phạm vi.

## Bước 2 — Định tuyến nội bộ

1. **Bug chặn luồng chính (đặt xe, thanh toán, đăng nhập):** mở ticket ưu tiên, phối hợp
   `IT` sửa nóng; cập nhật khách khi có bản vá.
2. **Vấn đề UX:** gom vào backlog cải tiến sản phẩm, gắn nhãn khu vực màn hình và mức ảnh
   hưởng; không hứa thời hạn cụ thể với khách.
3. **Đề xuất tính năng:** ghi nhận vào danh sách ý tưởng, cảm ơn khách, không cam kết triển
   khai.

## Bước 3 — Phản hồi khách và theo dõi

1. Phản hồi khách trong 24 giờ với hướng xử lý tương ứng nhóm ở trên.
2. Bug đã có bản vá: đóng ticket kèm phiên bản app chứa bản sửa.
3. Định kỳ rà backlog UX/đề xuất theo mức ảnh hưởng và số lượt phản hồi trùng, không để tồn
   vô thời hạn.
