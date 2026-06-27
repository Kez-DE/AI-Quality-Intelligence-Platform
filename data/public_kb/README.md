# Public KB — Guest Chatbot

Folder này chứa tài liệu công khai cho chatbot khách (`guest`). Nội dung được
làm sạch/tóm lược từ trang hỗ trợ và trang chính sách công khai của Green SM,
không chứa SOP/SLA nội bộ.

## Cách runtime đọc KB

`pipeline/agent/public_kb.py` load mọi file `.md` trong folder này, trừ
`README.md`, và chỉ nhận file có frontmatter:

```yaml
audience: public
```

Nội dung được chunk theo heading `##` và tìm kiếm bằng keyword/BM25-lite. Nếu
không tìm thấy mục phù hợp, chatbot phải hướng khách về kênh hỗ trợ chính thức.

## Manifest tài liệu

| File | Topic group | Nội dung |
| :--- | :--- | :--- |
| `an_toan.md` | Safety | Tai nạn, chuyến xe không an toàn, thông tin xe/tài xế không khớp |
| `dat_xe_dich_vu.md` | Vận hành | Đặt xe, chọn dịch vụ, hủy/chỉnh chuyến |
| `cuoc_phi_thanh_toan.md` | CSKH | Phương thức thanh toán, cước phí, hóa đơn, trừ tiền |
| `khuyen_mai_uu_dai.md` | Sản phẩm | Mã khuyến mãi, ưu đãi, điểm/hạng thành viên |
| `tai_khoan.md` | CSKH | Đăng ký, đăng nhập, đổi thông tin tài khoản |
| `ho_tro_phan_hoi.md` | CSKH | Lỗi app, gửi yêu cầu hỗ trợ, góp ý |
| `ho_tro_khieu_nai.md` | CSKH | Kênh khiếu nại, hỗ trợ khách hàng, quyền dữ liệu cá nhân |
| `su_co_chuyen_di.md` | CSKH | Sự cố sau chuyến, bỏ quên đồ, xe không đảm bảo |

## Quy tắc biên tập

- Không đưa footer, menu, cookie banner, link ảnh QR, hoặc nội dung crawl thô vào
  corpus RAG.
- Không thêm chính sách bồi thường, kỷ luật tài xế, SLA nội bộ hoặc thông tin chỉ
  dành cho vận hành.
- Với phí, khuyến mãi, hoàn tiền và điều kiện dịch vụ, luôn nhắc khách kiểm tra
  trong app hoặc liên hệ kênh chính thức vì chính sách có thể thay đổi.
- Giữ `source_url` trong frontmatter để truy vết nguồn công khai.
