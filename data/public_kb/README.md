# Public KB — Guest Chatbot

Folder này chứa tài liệu công khai cho trợ lý khách hàng (Customer web và tầng public). Nội dung được
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
| `dat_xe_dich_vu.md` | Vận hành | Các dịch vụ (Car, Mini, Premium, Limo, Bike, sân bay, Tour, Liên Tỉnh, Express, Van, Food, Business), đặt xe/đặt hàng, hẹn giờ, đặt hộ, hủy chuyến |
| `cuoc_phi_thanh_toan.md` | CSKH | Phương thức thanh toán, cách tính cước, phụ phí, giờ chờ, hóa đơn VAT, trừ tiền sai |
| `chinh_sach_dich_vu.md` | CSKH | Điều khoản cho khách: hợp đồng chuyến xe, hủy/hoàn tiền, hành lý, trẻ em, đồ bị bỏ quên, dữ liệu cá nhân, chống lừa đảo |
| `khuyen_mai_uu_dai.md` | Sản phẩm | Mã khuyến mãi, VPoint, gói hội viên, giới thiệu bạn bè, Green Business, ưu đãi đối tác có thời hạn |
| `an_toan.md` | Safety | Tai nạn, lái ẩu, quấy rối, cấp cứu, cháy xe, đi đêm, trẻ em/người già, SOS, bảo hiểm chuyến đi, số khẩn cấp 113/114/115 |
| `tai_khoan.md` | CSKH | Đăng ký, đăng nhập, đổi thông tin tài khoản |
| `ho_tro_phan_hoi.md` | CSKH | Hotline 1555, email, kênh chính thức, lỗi app, gửi yêu cầu hỗ trợ, góp ý |
| `ho_tro_khieu_nai.md` | CSKH | Kênh khiếu nại, thông tin cần cung cấp, quyền dữ liệu cá nhân |
| `su_co_chuyen_di.md` | CSKH | Sự cố sau chuyến, bỏ quên đồ, xe không đảm bảo |
| `tu_van_loi_khuyen.md` | CSKH | Lời khuyên cho chuyến đi suôn sẻ: điểm đón, kiểm tra xe, giờ cao điểm, đồ đạc, thanh toán, đánh giá |

## Quy tắc biên tập

- Không đưa footer, menu, cookie banner, link ảnh QR, hoặc nội dung crawl thô vào
  corpus RAG.
- Không thêm chính sách bồi thường, kỷ luật tài xế, SLA nội bộ hoặc thông tin chỉ
  dành cho vận hành.
- Với phí, khuyến mãi, hoàn tiền và điều kiện dịch vụ, luôn nhắc khách kiểm tra
  trong app hoặc liên hệ kênh chính thức vì chính sách có thể thay đổi.
- Giữ `source_url` trong frontmatter để truy vết nguồn công khai; liệt kê mọi trang
  đã dùng trong `sources: [url1, url2]` và cập nhật `source_checked_at`.
- Văn bản thuần: không `**`, `__`, bảng hay emoji (widget hiện nguyên ký tự).
  `pipeline/tests/test_public_kb.py` chặn `**`.
- Ưu đãi có thời hạn phải ghi rõ ngày kết thúc. Chatbot nhận ngày hôm nay và bỏ
  qua ưu đãi đã hết hạn, nhưng hãy xoá mục đã hết hạn khi rà lại KB.
- Chỉ dùng nguồn chính thức greensm.com (xanhsm.com chuyển hướng về đây). Không
  bịa số điện thoại, giá hay điều kiện; điều gì không kiểm được thì bỏ ra.
