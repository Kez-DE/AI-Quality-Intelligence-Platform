---
document_title: Quy trình xử lý Gian lận Cước & Vòi vĩnh (SOP-SAFETY-03)
category: fraud
department: Safety
severity_scope: [P4, P5]
source: mock
tags: [gian-lan, voi-vinh, thu-them-tien, doi-soat, khoa-tai-khoan]
---

# SOP-SAFETY-03 — Quy trình xử lý Gian lận Cước & Vòi vĩnh

## Phạm vi và mức độ

Áp dụng khi hành khách tố tài xế: thu thêm tiền ngoài app, đòi chuyển khoản riêng, cố tình
đi lòng vòng để tăng cước, gian lận quãng đường, hoặc ép hủy chuyến để "kèo ngoài". Theo
Deep Risk Matrix, `risk_fraud >= 8` chốt **Bậc 5**, `risk_fraud >= 5` chốt **Bậc 4**.
Route về **Team Safety** (P5) hoặc **Vận hành/CSKH** phối hợp đối soát (P4).

## Bước 1 — Thu thập bằng chứng đối soát (0–1 giờ)

1. Yêu cầu hành khách cung cấp: số tiền app hiển thị vs số tiền thực trả, ảnh chụp màn hình
   chuyển khoản (nếu có), nội dung tin nhắn đòi tiền.
2. Trích xuất từ hệ thống: cước chuẩn theo lộ trình, lộ trình GPS thực tế vs lộ trình tối ưu,
   lịch sử hủy chuyến của tài xế.
3. So sánh quãng đường thực tế với quãng đường ước tính — phát hiện đi vòng bất thường.

## Bước 2 — Xác minh và phân loại hành vi (1–4 giờ)

1. **Thu thêm tiền mặt ngoài app / đòi chuyển khoản:** vi phạm nghiêm trọng → cảnh cáo lần
   1, tái phạm khóa tài khoản. Hoàn lại phần chênh lệch cho khách.
2. **Đi lòng vòng tăng cước:** đối chiếu GPS; nếu cố ý → điều chỉnh lại cước đúng, hoàn
   chênh lệch, trừ điểm uy tín tài xế.
3. **Ép khách hủy để đi "kèo ngoài":** kiểm tra tỷ lệ hủy bất thường → cảnh cáo/khóa theo
   mức độ.

## Bước 3 — Xử lý và hoàn tiền (trong 24 giờ)

1. Hoàn phần tiền chênh lệch cho hành khách qua ví hoặc phương thức gốc theo
   `sla_boi_thuong_chuan.md`.
2. Áp kỷ luật tài xế theo thang: cảnh cáo → khóa tạm 7 ngày → khóa vĩnh viễn (tái phạm).
3. Đóng ticket `resolved` kèm kết luận và bằng chứng đối soát.

## Khi nào leo thang

- Đường dây gian lận có tổ chức (nhiều tài xế cùng thủ đoạn) → mở chuyên án, báo cáo Giám
  đốc Vận hành.
- Số tiền chiếm đoạt lớn, hành khách muốn trình báo → hỗ trợ thủ tục pháp lý.
