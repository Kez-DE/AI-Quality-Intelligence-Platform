---
document_title: Quy trình xử lý Quấy rối & Hành vi đe dọa an toàn (SOP-SAFETY-02)
category: safety
department: Vận hành
severity_scope: [P5]
source: mock
tags: [quay-roi, sam-so, de-doa, say-xin, khoa-tai-khoan]
---

# SOP-SAFETY-02 — Quy trình xử lý Quấy rối & Hành vi đe dọa an toàn

## Phạm vi áp dụng

Áp dụng cho phản hồi tố cáo tài xế có hành vi: sàm sỡ/quấy rối tình dục, đe dọa hành
hung, lái xe khi say xỉn, có dấu hiệu sử dụng chất kích thích, hoặc bất kỳ hành vi nào
khiến hành khách lo sợ cho an toàn thân thể. Toàn bộ nhóm này gán **Severity P5** và route
**bắt buộc về Team Safety, SLA 1 giờ**.

Lưu ý nghiệp vụ quan trọng: theo thuật toán Deep Risk Matrix (Waterfall), chỉ cần
`risk_safety >= 8` là chốt **Bậc 5 Khẩn cấp**, **không** lấy trung bình với các tiêu chí
khác. Một chuyến "xe sạch, đúng giờ" nhưng có quấy rối vẫn là P5.

## Bước 1 — Ổn định tâm lý hành khách (0–10 phút)

1. Gọi cho hành khách bằng thái độ bình tĩnh, đồng cảm; ưu tiên xác nhận hành khách hiện
   có đang an toàn hay không.
2. Nếu hành khách đang ở trên xe và lo sợ: hướng dẫn yêu cầu dừng tại nơi đông người, gọi
   **113** nếu bị đe dọa trực tiếp.
3. Không chất vấn nạn nhân theo hướng nghi ngờ; ghi nhận lời khai trung thực, nguyên văn.

## Bước 2 — Khóa tài khoản tài xế và thu thập bằng chứng (10–40 phút)

1. **Khóa ngay (suspend) tài khoản tài xế** để ngăn nhận chuyến mới trong khi điều tra —
   đây là biện pháp phòng ngừa bắt buộc với mọi cáo buộc quấy rối.
2. Trích xuất nhật ký chuyến: lộ trình GPS, thời gian, lịch sử liên lạc trong app.
3. Đề nghị hành khách cung cấp bằng chứng nếu có (ảnh, ghi âm, tin nhắn).
4. Lập hồ sơ vụ việc, gắn nhãn bảo mật — chỉ Team Safety và cấp quản lý được truy cập.

## Bước 3 — Xử lý kỷ luật và hỗ trợ nạn nhân (trong 24–48 giờ)

1. Mời tài xế làm việc, đối chiếu lời khai hai bên và bằng chứng GPS/hệ thống.
2. Nếu đủ căn cứ vi phạm: **khóa vĩnh viễn tài khoản**, đưa vào blacklist, và chuyển hồ sơ
   cho cơ quan công an nếu có dấu hiệu hình sự.
3. Hỗ trợ nạn nhân: hoàn 100% cước, đường dây tư vấn tâm lý, và hỗ trợ thủ tục trình báo.
4. Đóng ticket `resolved` kèm kết luận điều tra; lưu case làm tài liệu đào tạo.

## Khi nào leo thang (Escalation)

- Cáo buộc có yếu tố hình sự (cưỡng bức, hành hung gây thương tích) → báo công an + Giám
  đốc Vận hành ngay trong giờ đầu.
- Tài xế tái phạm (đã có cảnh báo trước) → khóa vĩnh viễn ngay, không qua bước cảnh cáo.
