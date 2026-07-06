# Slides — Tổng quan dự án

`AI-Quality-Intelligence-Platform-Overview.pptx` — bản thuyết trình tổng quan dự án
(20 slide, 16:9, tiếng Việt, có speaker notes), dành cho hội đồng AI20K / demo day.

Mạch trình bày: **Vấn đề → Bài toán → Giải pháp → Kiến trúc → Luồng E2E →
6 năng lực hoạt động → Vòng đời task (5 trạng thái) → Vận hành giao việc
(Manager → Nhân viên) → Phân quyền 4 vai trò (Khách/Nhân viên/Quản lý/Admin) →
Chatbot phân tầng theo tài khoản → Tư duy sản phẩm → Kết quả & Roadmap**.

Ảnh trong slide là **screenshot UI thật** chụp từ app đang chạy (Dashboard, Phản hồi,
Phân loại Ticket, Báo cáo AI, Quản lý công việc, AI Chat) — không phải mockup.

Thiết kế chi tiết: [`docs/superpowers/specs/2026-06-28-project-overview-slides-design.md`](../../superpowers/specs/2026-06-28-project-overview-slides-design.md).

## Pitch 10 phút (demo day)

- `GreenSM-Pitch-10min.pptx` — 12 slide, 16:9: 3' bài toán → 5' sản phẩm
  (mạch kịch bản v4, ẩn dụ phòng cấp cứu) → 2' closing/vision. Không có slide gọi vốn.
- `GreenSM-pitch-script.html` — kịch bản nói từng slide, mốc thời gian khớp speaker notes.
- `assets/pitch/` — screenshot UI thật + ảnh Green SM (nguồn trong `SOURCES.md`).
- Tái sinh deck: `uv run --with python-pptx python scripts/slides/build_greensm_pitch.py`.
