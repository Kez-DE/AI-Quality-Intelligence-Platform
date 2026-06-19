---
document_title: Quy trình xử lý Thái độ Tài xế không chuẩn mực (SOP-OPS-01)
category: attitude
department: Vận hành
severity_scope: [P3, P4]
source: mock
tags: [thai-do, chui-boi, xuc-pham, tranh-cai, duoi-khach]
---

# SOP-OPS-01 — Quy trình xử lý Thái độ Tài xế không chuẩn mực

## Phạm vi và mức độ

Áp dụng cho phản hồi về hành vi cư xử: tài xế chửi bới, xúc phạm, thái độ cộc cằn, tranh
cãi gay gắt, đuổi khách xuống xe giữa đường. Theo Deep Risk Matrix, `risk_attitude >= 8`
chốt **Bậc 4 (Nguy hiểm)**; `risk_attitude >= 6` góp vào **Bậc 3**. Route về **Team Vận
hành** (topic Driver Behavior, SLA 8 giờ). Nếu kèm đe dọa an toàn thì nâng P5 → Safety.

## Bước 1 — Tiếp nhận và phân loại mức độ (0–1 giờ)

1. Ghi nhận nguyên văn lời phản ánh, xác định hành vi cụ thể (lời lẽ, hành động).
2. Phân biệt: (a) thái độ cộc cằn/khó chịu (P3) vs (b) chửi bới xúc phạm nặng/đuổi khách
   giữa đường (P4).
3. Trường hợp **đuổi khách xuống xe giữa đường**: đây là vi phạm nghiêm trọng quy trình
   dịch vụ — xử lý theo P4, ưu tiên xác minh khách có bị bỏ ở nơi nguy hiểm không.

## Bước 2 — Xác minh hai chiều (1–4 giờ)

1. Liên hệ tài xế nghe trình bày; đối chiếu với lời khách và dữ liệu hệ thống (thời điểm,
   vị trí kết thúc chuyến so với điểm trả dự kiến).
2. Nếu có tranh chấp về lý do (khách gây sự trước, tài xế phản ứng): ghi nhận khách quan
   cả hai phía, không thiên vị.

## Bước 3 — Xử lý kỷ luật và xoa dịu khách (trong SLA 8 giờ)

1. Gọi xin lỗi hành khách, ghi nhận sự cố, áp bồi thường theo `sla_boi_thuong_chuan.md`
   (thường là voucher hoặc hoàn một phần cước với P3–P4).
2. Áp kỷ luật tài xế: nhắc nhở (P3) → cảnh cáo + trừ điểm uy tín (P4) → khóa tạm nếu tái
   phạm nhiều lần.
3. Nếu đuổi khách giữa đường gây hậu quả (khách ở nơi vắng, ban đêm): nâng mức kỷ luật,
   xem xét khóa tài khoản.
4. Đóng ticket `resolved` kèm biện pháp đã áp dụng.

## Câu trả lời chuẩn cho tình huống "tài xế đuổi khách xuống xe"

"Bên em rất tiếc về trải nghiệm này. Theo quy trình, hành vi đuổi khách giữa chuyến là vi
phạm và sẽ bị xử lý kỷ luật. Anh/chị vui lòng cho em xin mã chuyến để em xác minh và áp
chính sách hỗ trợ. Trong vòng 8 giờ bên em sẽ phản hồi kết quả xử lý ạ."
