# Chỉ mục tài liệu dự án

> **Cập nhật 2026-06-27:** chỉ mục điều hướng sau đối soát toàn bộ docs/project.

Thư mục `docs/project` chứa tài liệu mô tả kiến trúc, cơ chế, dữ liệu, và quy trình vận hành của hệ thống AI Quality Intelligence Platform (xanhSM). Mỗi mục dưới đây là một tệp hoàn chỉnh với mô tả ngắn về nội dung chính.

---

## Kiến trúc & Luồng

| Tệp | Mô tả |
| --- | --- |
| [architecture.md](architecture.md) | Kiến trúc tổng thể: các tầng hệ thống, tech stack, sơ đồ thành phần chính |
| [architecture-diagram.md](architecture-diagram.md) | Sơ đồ ASCII/Mermaid chi tiết các tầng: frontend, backend, AI, DB |
| [architecture/e2e-flow.md](architecture/e2e-flow.md) | 12 luồng xử lý đầu cuối: nguồn quyền uy cho pipeline, agent, RBAC, workers |
| [architecture/routing-taxonomy.md](architecture/routing-taxonomy.md) | Taxonomy định tuyến: ánh xạ topic sang phòng ban, dữ liệu thực |

## Cơ chế & AI

| Tệp | Mô tả |
| --- | --- |
| [co_che.md](co_che.md) | Cơ chế hoạt động: pipeline xử lý, scoring, worker topology, HI-loop |
| [giai_thich.md](giai_thich.md) | Giải thích từng bước: từ một review đến lúc phòng ban nhận task |
| [agents-guide.md](agents-guide.md) | Roster đầy đủ: 8 agent nghiệp vụ, Orchestrator, report_builder (helper) |
| [ai-systems.md](ai-systems.md) | AI Systems: RAG hybrid (Cohere embed + BM25 + RRF), model routing, chat endpoint |

## Dữ liệu & RBAC

| Tệp | Mô tả |
| --- | --- |
| [data-model.md](data-model.md) | Data dictionary: 10+ bảng Supabase, enums, indexes, triggers, ghi chú lịch sử |
| [rbac-departments.md](rbac-departments.md) | RBAC 5 roles (admin/manager/staff/pending/guest), phân quyền theo 6 phòng ban |
| [guest-account.md](guest-account.md) | Khách hàng (Customer web), tài khoản khách hàng (tuỳ chọn), tài khoản chờ cấp quyền, cách tạo tài khoản |

## Setup & Deploy

| Tệp | Mô tả |
| --- | --- |
| [setup-macos.md](setup-macos.md) | Hướng dẫn cài đặt môi trường trên macOS (backend + frontend) |
| [setup-windows.md](setup-windows.md) | Hướng dẫn cài đặt môi trường trên Windows (backend + frontend) |
| [setup-supabase.md](setup-supabase.md) | Thiết lập Supabase Cloud: project, migration, env vars |
| [deploy-railway.md](deploy-railway.md) | Deploy lên Railway: 4 workers, biến môi trường, push-to-deploy qua GitHub |

## Product & Eval

| Tệp | Mô tả |
| --- | --- |
| [product/README.md](product/README.md) | Tổng quan sản phẩm: vai trò người dùng, luồng UX chính, trạng thái tính năng |
| [demo-script.md](demo-script.md) | Kịch bản demo 5-7 phút: các bước, điểm nhấn, fallback khi lỗi |
| [roadmap.md](roadmap.md) | Lộ trình: 6 phòng ban (hoàn thành), Global Report chéo phòng (chưa), các hướng khác |
| [eval-evidence.md](eval-evidence.md) | Bằng chứng eval G2: kết quả pytest, router, model, pipeline smoke, build frontend |

---

Với mọi thay đổi kiến trúc hoặc cơ chế, cập nhật tệp liên quan và đồng bộ `architecture/e2e-flow.md` là nguồn quyền uy.
