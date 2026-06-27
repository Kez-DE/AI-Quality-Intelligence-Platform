# Lộ trình mở rộng

> Lộ trình mở rộng. Mục **"Mở rộng danh sách phòng ban (4 lên 6)"** đã **triển khai (2026-06-27)**:
> hệ thống hiện chạy **6 phòng ban** — IT, CSKH, Vận hành, Tài chính & Thanh toán, Sản phẩm,
> Quản lý Rủi ro & Gian lận. Các mục còn lại (Global Report chéo phòng và Các hướng khác) vẫn là
> định hướng tương lai, **chưa triển khai**. Nội dung được tách ra từ kế hoạch HI-Loop gốc của team.

## Mở rộng danh sách phòng ban (4 lên 6) — ✅ đã triển khai (2026-06-27)

Hệ thống đã mở rộng định tuyến và xử lý lên sáu phòng ban (chi tiết:
`docs/superpowers/specs/2026-06-27-six-departments-design.md`):

| # | Phòng ban | Vai trò |
| --- | --- | --- |
| 1 | Công nghệ Thông tin (IT / Engineering) | Lỗi hệ thống, ứng dụng, server, API, GPS, thanh toán kỹ thuật |
| 2 | Vận hành (Operations) | Hoạt động tài xế, chuyến xe, quy trình vận hành |
| 3 | Chăm sóc Khách hàng (Customer Support) | Tiếp nhận và xử lý khiếu nại, hỗ trợ người dùng |
| 4 | Tài chính và Thanh toán (Finance & Payment) | Hoàn tiền, đối soát giao dịch, lỗi thanh toán |
| 5 | Sản phẩm (Product Management) | Cải thiện tính năng, UX/UI, đề xuất nâng cấp |
| 6 | Quản lý Rủi ro và Gian lận (Risk & Fraud) | Phát hiện gian lận, lạm dụng khuyến mãi, tài khoản bất thường |

## Cơ chế chia việc khi lên 6 phòng

> Router Agent (mục 1) và Analyst Agent (mục 2) đã triển khai cùng đợt 4→6 (2026-06-27).
> Global Report chéo phòng (mục 3) vẫn **chưa triển khai**.

### 1. Nâng cấp Router Agent

Trang bị taxonomy mới (cập nhật `data/taxonomy/routing_table.json`) để phân biệt rõ ranh giới
nghiệp vụ giữa các phòng. Ví dụ:

- Khách không thanh toán được do app sập: giao IT.
- Khách bị trừ tiền hai lần, yêu cầu hoàn: giao Tài chính và Thanh toán.
- Phát hiện hàng loạt cuốc xe ảo lạm dụng khuyến mãi: giao Quản lý Rủi ro và Gian lận.
- Giao diện đặt xe khó dùng khiến khách nhầm điểm đón: giao Sản phẩm.

### 2. Nâng cấp Analyst Agent

Thêm persona chuyên biệt cho từng phòng mới trong `analyst_agent.py`. Ví dụ đề xuất hành động:

- Sản phẩm: thiết kế lại luồng chọn điểm đón để giảm sai sót.
- Quản lý Rủi ro: rà soát và tạm khoá nhóm tài khoản dùng chung thiết bị để đầu cơ khuyến mãi.
- Tài chính: thực hiện lệnh hoàn tiền hàng loạt cho nhóm khách bị trừ tiền kép.

### 3. Sự cố chéo phòng ban (Global Report)

Một sự cố diện rộng (ví dụ lỗi hệ thống thanh toán) thường ảnh hưởng nhiều phòng. Hệ thống phát
hiện spike rồi sinh một Báo cáo Tổng hợp, đề xuất các task song song cho từng phòng liên quan:

- IT: sửa lỗi API thanh toán ngay (ưu tiên P1).
- Tài chính: đối soát giao dịch, xác định số tiền treo (P2).
- CSKH: chuẩn bị kịch bản phản hồi, xin lỗi và tặng mã giảm giá cho khách bị ảnh hưởng (P2).

Trưởng phòng mỗi phòng độc lập duyệt các task thuộc phạm vi của mình trên giao diện duyệt báo
cáo đã có, để triển khai đồng bộ.

## Các hướng khác

- Hút review real-time trực tiếp từ store và app thay cho streaming dataset đóng gói.
- Đẩy thông báo tới Slack, email, hoặc app tài xế thay vì chỉ hiển thị trên dashboard.
- Container hoá đầy đủ, CI/CD, monitoring cho môi trường production thật.
- Thay router heuristic bằng LLM khi cần độ chính xác định tuyến cao hơn.
</content>
