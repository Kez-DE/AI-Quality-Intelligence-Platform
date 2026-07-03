---
document_title: Quy trình Phát hiện & Xử lý Rủi ro Gian lận (SOP-RISK-01)
category: fraud
department: Quản lý Rủi ro & Gian lận
severity_scope: [P3, P4, P5]
source: mock
tags: [gian-lan, rui-ro, tai-khoan-gia, lam-dung-khuyen-mai, chong-lam-dung, khoa-tai-khoan]
---

# SOP-RISK-01 — Quy trình Phát hiện & Xử lý Rủi ro Gian lận

## Phạm vi và mức độ

Áp dụng cho hành vi gian lận có hệ thống: tài khoản giả/đa tài khoản để nhận khuyến mãi,
lạm dụng mã giới thiệu, chuyến "ma" (đặt và hủy khống để cày thưởng), câu kết tài xế–hành
khách rút tiền khuyến mãi. Ca một hành khách tố tài xế thu thêm tiền cho một chuyến cụ thể
được xử lý theo SOP thu-thêm-tiền của đội phản ứng nhanh; SOP này lo phần **mẫu hình gian
lận lặp lại**. `risk_fraud >= 8` chốt P5, `>= 5` chốt P4.

## Bước 1 — Phát hiện mẫu hình (liên tục)

1. Theo dõi tín hiệu bất thường: nhiều tài khoản cùng thiết bị/số điện thoại/phương thức
   thanh toán, tỷ lệ hủy chuyến cao bất thường, cụm giao dịch khuyến mãi trong thời gian
   ngắn.
2. Chấm điểm `risk_fraud` theo Deep Risk Matrix; gom theo tài khoản, thiết bị, và khu vực.
3. Ưu tiên điều tra cụm có giá trị khuyến mãi bị rút lớn hoặc lặp nhiều chu kỳ.

## Bước 2 — Điều tra và xác minh

1. Đối chiếu lịch sử chuyến, thiết bị đăng nhập, và dòng tiền khuyến mãi của các tài khoản
   nghi vấn.
2. Phân biệt **trùng hợp** (cùng hộ gia đình, cùng wifi công cộng) với **gian lận có chủ
   đích** (kịch bản hủy/đặt lặp, tài khoản chỉ hoạt động quanh khuyến mãi).
3. Ghi bằng chứng vào hồ sơ rủi ro; ca nghiêm trọng phối hợp `Tài chính & Thanh toán` để
   khóa dòng tiền liên quan.

## Bước 3 — Chế tài và phòng ngừa

1. **Xác nhận gian lận:** thu hồi khuyến mãi đã rút, khóa tài khoản/thiết bị, chặn phương
   thức thanh toán liên quan.
2. **Nghi vấn chưa đủ bằng chứng:** đưa vào danh sách theo dõi, giới hạn ưu đãi tạm thời,
   không khóa vội.
3. Đề xuất chống lạm dụng cho đội `Sản phẩm`: siết điều kiện mã giới thiệu, giới hạn số tài
   khoản trên một thiết bị, thêm bước xác minh cho tài khoản mới nhận khuyến mãi lớn.
