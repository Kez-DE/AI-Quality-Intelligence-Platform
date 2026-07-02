---
document_title: Biện pháp Bảo mật & Bảo vệ Dữ liệu Khách hàng (SOP-RISK-02)
category: security
department: Quản lý Rủi ro & Gian lận
severity_scope: [P2, P3, P4, P5]
source: https://www.greensm.com/vn-vi/terms-policies/consumer-protection-policy
tags: [bao-mat, bao-ve-du-lieu, mfa, sso, pentest, ma-hoa, quyen-nguoi-tieu-dung]
---

# SOP-RISK-02 — Bảo mật & Bảo vệ Dữ liệu Khách hàng

> Neo trên Chính sách Bảo vệ Người tiêu dùng công khai của Green SM (xanhSM). Dùng làm chuẩn
> đối chiếu khi điều tra sự cố rò rỉ/lạm dụng dữ liệu và khi phối hợp IT.

## Liên hệ phụ trách dữ liệu

- **DPO (Bảo vệ dữ liệu): DPOoffice@greensm.com**
- Hỗ trợ khách hàng: **Hotline 1555**, support.vn@greensm.com.

## Nguyên tắc dùng dữ liệu (theo chính sách)

- Công ty **không bán** thông tin khách hàng cho bất kỳ bên nào.
- Chia sẻ dữ liệu chỉ trong các trường hợp: khách đã đồng ý; khách ủy quyền hợp pháp; theo
  thỏa thuận cụ thể; hoặc theo quy định pháp luật/cơ quan nhà nước có thẩm quyền.

## Biện pháp kỹ thuật đang áp dụng (chuẩn đối chiếu điều tra)

- Kiểm soát phân quyền theo vai trò/trách nhiệm, nguyên tắc **"ít đặc quyền nhất"**.
- Xác thực người dùng **MFA**, kết hợp **SSO qua MS AD**.
- **Ghi log truy cập**: thời gian, địa chỉ IP, hành động, thông tin người dùng.
- **Mã hóa dữ liệu trên đường truyền**.
- Sao lưu định kỳ + kế hoạch phục hồi dữ liệu.
- **Pentest** với hệ thống phát sinh mới hoặc nâng cấp.
- Rà quét dữ liệu lưu trữ sai quy định hàng ngày; chỉ định bộ phận/nhân sự phụ trách bảo vệ
  dữ liệu khách hàng.

## Quyền của khách về dữ liệu (đối chiếu khi xử lý yêu cầu)

Biết về hoạt động xử lý; đồng ý/không đồng ý; truy cập – xem – chỉnh sửa; rút lại đồng ý;
xóa thông tin; hạn chế xử lý; yêu cầu cung cấp thông tin của mình; phản đối xử lý; khiếu
nại/tố cáo/khởi kiện; tự bảo vệ theo quy định pháp luật.

## Áp dụng nội bộ

Khi điều tra ca gian lận/rò rỉ (SOP-RISK-01), đối chiếu log truy cập + phân quyền + MFA ở
trên để xác định điểm yếu; ca liên quan lộ dữ liệu cá nhân → phối hợp DPO
(DPOoffice@greensm.com) và IT.
