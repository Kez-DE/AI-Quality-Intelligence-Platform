---
document_title: Xử lý Sự cố Ứng dụng — Đặt xe, Định vị, Điểm thưởng (SOP-IT-01)
category: tech
department: IT
severity_scope: [P3, P4]
source: https://www.greensm.com/vn-vi/helps
tags: [ung-dung, gps, dinh-vi, diem-xanh, thanh-toan, su-co-ky-thuat]
---

# SOP-IT-01 — Xử lý Sự cố Ứng dụng (Đặt xe/Định vị/Điểm thưởng)

> Neo phần hướng dẫn thao tác công khai của Green SM (xanhSM). Dùng khi phản hồi liên quan
> lỗi kỹ thuật app. Phần cấu hình hệ thống nội bộ (backend cổng thanh toán) là nội bộ, chưa
> có nguồn công khai — đánh dấu rõ.

## Điểm tựa từ hướng dẫn chính thức

- **Định vị GPS:** app dùng GPS xác định vị trí hiện tại ở bước chọn điểm đón → lỗi định vị
  sai thường do quyền GPS/thiết bị; hướng dẫn khách bật quyền vị trí, nhập điểm đón tay.
- **Phương thức thanh toán:** thêm/cập nhật tại **Tài khoản → Thanh toán** → lỗi thêm thẻ
  thường ở bước điền thông tin/xác thực; đối chiếu với cổng thanh toán.
- **Không nhận điểm Xanh cho chuyến** (mục 4.5 FAQ) → kiểm tra điều kiện tích điểm + trạng
  thái chuyến; ca lỗi hệ thống tích điểm → mở ticket IT.

## Phân loại nhanh (nội bộ)

- **Lỗi chặn luồng chính** (không đặt được, không đăng nhập, crash) → ưu tiên, phối hợp
  Sản phẩm; cập nhật khách khi có bản vá.
- **Lỗi thanh toán cổng** → xem SOP-FIN-01 + đối soát; phối hợp Tài chính.
- **Lỗi hiển thị/nhỏ** → gom backlog kỹ thuật.

> Nội bộ, chưa có nguồn công khai: cấu hình cổng thanh toán, log hệ thống, quy trình rollback
> — theo tài liệu vận hành IT nội bộ.

## Liên hệ

Khách báo lỗi kỹ thuật: **Hotline 1555**, mục Hỗ trợ trong app.
