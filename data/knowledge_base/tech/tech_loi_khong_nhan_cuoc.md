---
document_title: Hướng dẫn xử lý Lỗi App không nhận cuốc / định vị (TECH-IT-02)
category: app
department: IT
severity_scope: [P2, P3]
source: mock
tags: [khong-nhan-cuoc, gps, dinh-vi, app-lag, crash, ban-do]
---

# TECH-IT-02 — Lỗi App không nhận cuốc & Định vị GPS

## Phạm vi

Áp dụng cho lỗi kỹ thuật vận hành app: tài xế không nhận được cuốc, app lag/crash khi nổ
cuốc, định vị GPS sai vị trí, bản đồ không tải. Topic **App Issue** → route **Team IT**
(SLA 12 giờ). Insight phòng IT theo dõi top khu vực lỗi để fix bug khẩn sau mỗi đợt cập nhật.

## Lỗi 1 — Tài xế không nhận được cuốc

**Triệu chứng:** Tài xế online nhưng không có cuốc đổ về, hoặc cuốc nổ rồi biến mất.

1. Kiểm tra trạng thái tài khoản tài xế: online thật chưa, có bị giới hạn vùng không.
2. Kiểm tra kết nối mạng và phiên bản app (yêu cầu cập nhật bản mới nhất).
3. Hướng dẫn đăng xuất/đăng nhập lại, xóa cache app.
4. Nếu nhiều tài xế cùng khu vực cùng lỗi → nghi lỗi phân phối cuốc theo vùng, escalate IT.

## Lỗi 2 — Định vị GPS sai / nhảy vị trí

**Triệu chứng:** Điểm đón/trả lệch vị trí thực, kim chỉ nhảy lung tung, tài xế và khách
"lạc" nhau.

1. Hướng dẫn bật chế độ định vị **độ chính xác cao** trong cài đặt điện thoại.
2. Kiểm tra quyền truy cập vị trí của app (Location permission = Always/When in use).
3. Tránh dùng app giả lập vị trí (fake GPS) — nếu phát hiện ở tài xế, xử lý kỷ luật.
4. Khu vực có nhiều nhà cao tầng/hầm để xe dễ nhiễu GPS — ghi nhận để cải thiện bản đồ.

## Lỗi 3 — App lag / crash khi thao tác

**Triệu chứng:** App đơ, văng ra khi mở bản đồ hoặc lúc nổ cuốc.

1. Thu thập: dòng máy, phiên bản OS, phiên bản app, thời điểm crash.
2. Hướng dẫn cập nhật app, giải phóng RAM, gỡ cài đặt lại nếu cần.
3. Tổng hợp log crash gửi Team Product; nếu crash tăng vọt sau bản cập nhật → đề xuất
   rollback hoặc hotfix khẩn.

## Khi nào escalate sang IT/Product

- Lỗi xuất hiện đồng loạt ngay sau một đợt cập nhật app (regression).
- Một khu vực địa lý có tỷ lệ lỗi định vị/không nhận cuốc cao bất thường.
- Crash chặn hoàn toàn việc nhận cuốc, ảnh hưởng doanh thu tài xế diện rộng.
