---
document_title: Lịch sử Ticket P5 đã xử lý thành công (CASE-P5-2026)
category: case_study
department: Vận hành
severity_scope: [P4, P5]
source: mock
tags: [case-study, few-shot, ticket-mau, p5, da-giai-quyet]
---

# CASE-P5-2026 — Lịch sử Ticket nghiêm trọng đã xử lý thành công

Tập case mẫu (few-shot) cho AI tham chiếu cách xử lý chuẩn. Mỗi case nêu: bối cảnh, hành
động đã làm, kết quả. Dùng làm ví dụ minh họa, không thay thế SOP gốc.

## Case TK-2026-0142 — Tài xế có dấu hiệu say xỉn

**Bối cảnh:** Khách phản ánh tài xế có mùi rượu, lái loạng choạng, vượt ẩu trên đường vành
đai lúc 22h. Risk Matrix: `risk_safety=9` → P5, route Safety.

**Đã xử lý:**
1. Gọi khách trong 6 phút, xác nhận khách đã xuống xe an toàn tại điểm đông người.
2. Khóa tạm tài khoản tài xế ngay; trích GPS xác nhận lộ trình bất thường (đảo lái, phanh gấp).
3. Mời tài xế làm việc, tài xế thừa nhận uống rượu trước ca → **khóa vĩnh viễn**, đưa blacklist.
4. Hoàn 100% cước cho khách + voucher xin lỗi.

**Kết quả:** Đóng `resolved` trong 52 phút (trong SLA 1 giờ). Không phát sinh khiếu nại tiếp.

## Case TK-2026-0188 — Quấy rối hành khách nữ

**Bối cảnh:** Khách nữ tố tài xế có lời lẽ và hành vi sàm sỡ. Risk Matrix: `risk_safety=9`,
các tiêu chí khác = 0 (xe sạch, đúng giờ). Average sẽ ra "an toàn" — nhưng Waterfall chốt P5.

**Đã xử lý:**
1. Trấn an khách, ghi nhận lời khai nguyên văn, không chất vấn nghi ngờ.
2. Khóa tài khoản tài xế ngay lập tức (biện pháp phòng ngừa bắt buộc).
3. Trích log chuyến + đề nghị khách cung cấp bằng chứng; lập hồ sơ bảo mật.
4. Đủ căn cứ → khóa vĩnh viễn + chuyển hồ sơ công an; hỗ trợ khách tư vấn tâm lý và trình báo.

**Kết quả:** Case minh họa kinh điển cho việc **không lấy trung bình điểm rủi ro**. Xử lý
đúng giúp tránh lọt rủi ro nghiêm trọng.

## Case TK-2026-0210 — Gian lận thu thêm tiền mặt

**Bối cảnh:** Khách báo app hiện 85.000đ nhưng tài xế đòi 150.000đ tiền mặt, dọa không cho
xuống xe. Risk Matrix: `risk_fraud=8`, `risk_safety=6` → P5.

**Đã xử lý:**
1. Đối soát cước chuẩn theo lộ trình = 85.000đ; xác nhận tài xế thu vượt.
2. Hoàn phần chênh 65.000đ cho khách + voucher 50.000đ.
3. Tài xế tái phạm lần 2 (đã có cảnh cáo) → khóa vĩnh viễn.

**Kết quả:** Đóng `resolved` trong SLA; cập nhật blacklist; dùng làm ví dụ đối soát GPS+cước.

## Case TK-2026-0233 — Đuổi khách xuống xe giữa đường

**Bối cảnh:** Tài xế tranh cãi rồi đuổi khách xuống đoạn đường vắng lúc 23h. Risk Matrix:
`risk_attitude=8`, `risk_safety=5` (bỏ khách nơi vắng ban đêm) → nâng P4–P5, phối hợp Safety.

**Đã xử lý:**
1. Xác minh vị trí khách bị bỏ, hỗ trợ đặt chuyến thay thế miễn phí đưa khách về an toàn.
2. Đối chiếu hai phía: khách không có hành vi kích động trước.
3. Cảnh cáo nặng + trừ điểm uy tín + khóa tạm 7 ngày; bồi thường voucher 100.000đ.

**Kết quả:** Đóng `resolved`; ghi nhận làm tiền lệ xử lý hành vi bỏ khách nơi nguy hiểm.
