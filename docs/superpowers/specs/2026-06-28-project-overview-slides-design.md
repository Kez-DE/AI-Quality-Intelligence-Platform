# Thiết kế: Slide tổng quan dự án (PPTX) — AI Quality Intelligence Platform

> Ngày: 2026-06-28 · Nhánh: `docs/project-overview-slides` · Đối tượng: Hội đồng AI20K / demo day

## Mục tiêu

Tạo một bản thuyết trình `.pptx` (16:9) tổng quan dự án xanhSM AI Quality Intelligence
Platform, theo mạch: **Vấn đề → Bài toán → Vận hành → Cách hoạt động → Tư duy sản phẩm**,
dùng **ảnh chụp UI thật** từ app đang chạy, đủ để trình bày 10–15 phút trước hội đồng.

## Phạm vi (in scope)

- 1 file `.pptx` 15 slide, tiếng Việt, theme thương hiệu xanhSM (xanh lá / trắng).
- Speaker notes cho mỗi slide.
- Ảnh UI thật chụp từ app local (frontend `:5174` + backend `:8000` + Supabase cloud).
- 4 sơ đồ tự dựng (vector trong PPTX): bài toán, kiến trúc, luồng E2E, nguyên tắc sản phẩm.
- File xuất ra: `docs/project/slides/AI-Quality-Intelligence-Platform-Overview.pptx`.

## Ngoài phạm vi (out of scope)

- Không thay đổi code sản phẩm, schema, hay tài liệu kỹ thuật hiện có.
- Không tạo bản tiếng Anh.
- Không dựng video/animation.
- Không deploy gì lên Railway/Supabase.

## Cách dựng

- Dùng skill `pptx-official` (python-pptx) để sinh `.pptx` gốc, mở/sửa được trong PowerPoint.
- Chụp screenshot bằng cách chạy app local rồi điều khiển browser (đăng nhập admin).
- Sơ đồ dựng bằng shape/vector của python-pptx (không nhúng ảnh raster cho diagram).

## Theme

- Tỉ lệ 16:9.
- Màu chủ đạo: xanh lá xanhSM (xanh đậm tiêu đề + xanh tươi nhấn), nền trắng/xám rất nhạt.
- Mỗi content slide: 1 tiêu đề ý chính + bullet ngắn + 1 ảnh/sơ đồ.
- Footer: "xanhSM · AI20K Cohort 2 — Team 116" + số trang.

## Dàn 15 slide

| # | Slide | Nội dung | Hình |
|---|-------|----------|------|
| 1 | Bìa | Tên nền tảng · xanhSM · Team 116 · AI20K Cohort 2 | Landing page hoặc hero |
| 2 | Bối cảnh & Vấn đề | Nghìn review/ngày; vận hành quá tải; sự cố an toàn bị chôn vùi; phản hồi rời rạc đa kênh | Đồ họa stat |
| 3 | Bài toán | Tiếp nhận tự động → phân loại → phát hiện sớm → định tuyến đúng phòng → hành động khép kín | Sơ đồ bài toán (vector) |
| 4 | Giải pháp tổng quan | Câu định vị + 11 tính năng gom 4 nhóm: Tiếp nhận · Phân tích · Cảnh báo · Hành động | Dashboard |
| 5 | Kiến trúc tổng thể | 3 tầng app/pipeline/supabase; 6 Railway service; Supabase là trục realtime | Sơ đồ kiến trúc (vector) |
| 6 | Luồng vận hành E2E | Review thô → che PII → ML phân loại → spike → alert/ticket → HI-loop → báo cáo → task | Sơ đồ luồng (vector) |
| 7 | Hoạt động ①: Thu nhận + Phân loại + Che PII | ML TF-IDF/LinearSVC + luật safety tiếng Việt; mask SĐT/email/biển số; AI tự gán topic/sentiment/severity | Trang Phản hồi |
| 8 | Hoạt động ②: Spike → Alert → Ticket định tuyến | Spike detector → LLM root cause → alert giao đúng 1 trong 6 phòng; ticket tự đổi trạng thái | Trang Alerts |
| 9 | Hoạt động ③: Human-in-the-Loop | Review Queue (P5/safety/confidence thấp); sửa nhãn → correction log (audit + retrain) | Review Queue |
| 10 | Hoạt động ④: Multi-agent + Báo cáo AI | 8 agent + orchestrator; báo cáo 3 khối Vấn đề→Phân tích→Đề xuất; lịch 09:00 & 14:00 | Trang Báo cáo AI |
| 11 | Hoạt động ⑤: Khép kín Báo cáo → Task | HI-Loop Approval: biên tập đề xuất → duyệt 1 nút → tạo task, liên kết ngược báo cáo gốc | Trang Task Board |
| 12 | Hoạt động ⑥: AI Chat + RAG Hybrid tiered | Cohere embed-multilingual-v3 + BM25-lite + RRF (k=60); phân quyền Guest (FAQ) / Staff (nội bộ) | Trang AI Chat |
| 13 | Tư duy sản phẩm | 5 nguyên tắc: An toàn không nhường xác suất · Human-in-the-loop · Phân quyền tự động · Khép kín phản hồi→hành động · Realtime-first | Đồ họa nguyên tắc (vector) |
| 14 | Kết quả & Roadmap | Trạng thái hoàn thiện (task loop, HI-loop, hybrid RAG, 6 phòng); bằng chứng eval; hướng tiếp | Dashboard (metrics) |
| 15 | Cảm ơn / Q&A | Liên hệ + kêu gọi | Logo/closing |

## Danh sách screenshot cần chụp

Đăng nhập admin (`manhnguyn1912@gmail.com`), chụp ở viewport ~1440×900:

1. `/` — landing (slide 1)
2. `/dashboard` — tổng quan (slide 4, tái dùng cho 14)
3. `/feedback` — danh sách phản hồi + AI auto-label (slide 7)
4. `/feedback` — section Review Queue "Cần duyệt" (slide 9)
5. `/alerts` — danh sách alert + chi tiết (slide 8)
6. `/reports` — Báo cáo AI 3 khối (slide 10)
7. `/tasks` — Task Board, badge "Từ báo cáo" (slide 11)
8. `/chat` — AI Chat (slide 12)

Nếu một trang trống dữ liệu, chạy seed/live-stream theo `demo-script.md` trước khi chụp.

## Tiêu chí hoàn thành

- File `.pptx` mở được, 15 slide, đúng thứ tự, tiếng Việt, có speaker notes.
- ≥ 6 slide chứa ảnh UI thật (không phải poster/mockup).
- 4 sơ đồ vector hiển thị rõ.
- Nội dung khớp tài liệu hiện tại (6 phòng ban, RAG hybrid, 8 agent, task loop).
- File nằm ở `docs/project/slides/` và được commit.

## Rủi ro & cách xử lý

- **App không chạy / Supabase rỗng**: dùng live-stream/seed của demo-script; nếu vẫn fail, fallback dùng poster cho slide UI và ghi rõ trong commit.
- **Trang yêu cầu role cao**: dùng tài khoản admin để thấy tối đa tính năng.
- **Ảnh chứa PII**: app đã mask PII; vẫn rà nhanh trước khi nhúng.
