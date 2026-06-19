---
document_title: SLA & Chính sách Bồi thường Chuẩn 2026 (POLICY-SLA-01)
category: sla
department: CSKH
severity_scope: [P1, P2, P3, P4, P5]
source: mock
tags: [sla, boi-thuong, voucher, hoan-tien, deadline]
---

# POLICY-SLA-01 — SLA & Chính sách Bồi thường Chuẩn 2026

## Bảng SLA theo mức Severity

Thời gian tối đa kể từ khi ticket được tạo đến khi phải đóng (`resolved`). Quá hạn sẽ tự
động escalate lên cấp quản lý của phòng phụ trách.

| Severity | Mức độ | Phòng phụ trách mặc định | SLA đóng ticket |
| :--- | :--- | :--- | :--- |
| **P5** | Khẩn cấp (an toàn/gian lận nặng) | Safety | **1 giờ** |
| **P4** | Nguy hiểm | Vận hành / Safety | 8 giờ |
| **P3** | Trung bình | CSKH / Vận hành | 12 giờ |
| **P2** | Thấp | CSKH | 24 giờ |
| **P1** | Ghi nhận / bình thường | CSKH | 48 giờ |

Quy tắc bất biến: mọi case gán **P5 luôn route về Safety** với SLA 1 giờ, kể cả khi topic
gốc khác (severity override thắng routing theo topic).

## Bảng mức Bồi thường chuẩn cho khách

Áp dụng tham chiếu; nhân viên có thể điều chỉnh trong khung cho phép tùy mức độ thực tế.

| Tình huống | Mức bồi thường chuẩn |
| :--- | :--- |
| Tai nạn có thiệt hại sức khỏe | Hoàn 100% cước + hỗ trợ chi phí y tế ban đầu theo hóa đơn + bảo hiểm chuyến đi |
| Quấy rối / đe dọa an toàn | Hoàn 100% cước + tư vấn tâm lý + hỗ trợ thủ tục trình báo |
| Gian lận cước / thu thêm tiền | Hoàn 100% phần chênh lệch + voucher 50.000đ xin lỗi |
| Thái độ tài xế nặng / đuổi khách | Voucher 50.000–100.000đ hoặc hoàn 50% cước chuyến |
| Trễ giờ đón quá 15 phút do tài xế | Voucher 30.000đ |
| Mất đồ — hỗ trợ giao trả | Hỗ trợ tối đa 50% cước giao trả |
| Lỗi App gây trừ tiền sai | Hoàn 100% số tiền trừ sai trong 24–72 giờ |

## Quy tắc phê duyệt bồi thường

- Voucher ≤ 100.000đ: nhân viên CSKH tự duyệt.
- Hoàn tiền > 500.000đ hoặc hỗ trợ y tế: cần quản lý ca phê duyệt.
- Mọi khoản bồi thường phải ghi rõ lý do và đính kèm vào ticket trước khi đóng.

## Cam kết phản hồi khách (Response SLA)

- Phản hồi lần đầu cho khách: trong 30 phút với P4–P5, trong 2 giờ với P2–P3.
- Cập nhật tiến độ: tối thiểu 1 lần/ngày cho ticket chưa đóng.
- Khi đóng ticket: luôn gửi thông báo kết quả xử lý cho khách.
