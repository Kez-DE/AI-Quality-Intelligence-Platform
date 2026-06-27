# Tổng quan Sản phẩm

> **Cập nhật 2026-06-27:** phản ánh trạng thái hoàn thành (task loop, HI-loop, hybrid RAG, 6 phòng).

**xanhSM AI Quality Intelligence Platform** (C2-App-116) phân tích phản hồi khách hàng cho dịch vụ di chuyển thông minh xanhSM. Hệ thống tự động tiếp nhận phản hồi, làm sạch PII, phân loại bằng ML, phát hiện spike, tạo báo cáo AI theo phòng ban, hỗ trợ vòng duyệt nhân viên (Human-in-the-Loop), và cung cấp giao diện hỏi đáp RAG cho nhiều nhóm người dùng.

Stack: FastAPI + scikit-learn + LLM multi-agent (backend), React 19 + TanStack Start + Vite 7 (frontend), Supabase PostgreSQL + Auth + Realtime (database). Deploy: 6 service Docker trên Railway.

## Tính năng đã hoàn thành (11 tính năng)

| # | Tính năng | Mô tả |
|---|-----------|-------|
| 1 | Phân loại tự động | TF-IDF + LinearSVC + rule engine tiếng Việt |
| 2 | Che giấu PII | Mask SĐT, email, biển số xe |
| 3 | Ma trận Rủi ro Sâu | Chấm 5 chiều (safety, fraud, attitude, vehicle, compliance) qua LLM Scoring Agent |
| 4 | Phát hiện Spike | Nhận diện điểm nóng, tự tạo alert ticket |
| 5 | Multi-Agent | 8 agent nghiệp vụ + Orchestrator + report_builder (helper) |
| 6 | Phân tích phòng ban | 6 phòng ban, nhiều báo cáo/ngày (09:00 và 14:00), cấu trúc 3 khối: Vấn đề, Phân tích, Đề xuất |
| 7 | Human-in-the-Loop | Hàng đợi duyệt nhãn, nhân viên sửa nhãn AI, ghi correction log |
| 8 | AI Chat + RAG Hybrid | Hybrid Search (Cohere embed-multilingual-v3.0 + BM25-lite + RRF k=60), tiered RBAC (Guest: Public FAQ, Staff: Internal KB) |
| 9 | Streaming Realtime | Ingest phản hồi theo luồng thời gian thực |
| 10 | RBAC 4 vai trò | admin, manager, staff, guest |
| 11 | Khép kín Báo cáo → Task | HI-Loop Approval: manager biên tập đề xuất AI trong báo cáo, duyệt một nút tạo task chính thức, có liên kết ngược về báo cáo gốc |

## Phòng ban (6 phòng)

| # | Phòng ban |
|---|-----------|
| 1 | Công nghệ Thông tin (IT) |
| 2 | Chăm sóc Khách hàng (CSKH) |
| 3 | Vận hành |
| 4 | Tài chính & Thanh toán |
| 5 | Sản phẩm |
| 6 | Quản lý Rủi ro & Gian lận |

## Phân quyền (RBAC 4 vai trò)

| Vai trò | Phạm vi |
|---------|---------|
| admin | Toàn quyền, quản lý user, xem mọi phòng |
| manager | Giám sát phòng mình: alerts, feedback, insights, reports, chat |
| staff | Công việc hàng ngày phòng mình: feedback, tasks, chat |
| guest | Dashboard, feedback, chat CSKH (Public FAQ) |

Scope dữ liệu theo phòng ban: manager và staff chỉ xem dữ liệu phòng mình.

## Tài liệu liên quan

- `docs/project/architecture.md`: kiến trúc 3 tầng, 6 service Railway
- `docs/project/agents-guide.md`: 8 agent + orchestrator, I/O, routing
- `docs/project/rbac-departments.md`: RBAC 4 vai trò + scope theo phòng ban
- `docs/project/demo-script.md`: kịch bản demo
- `docs/project/roadmap.md`: lộ trình mở rộng
