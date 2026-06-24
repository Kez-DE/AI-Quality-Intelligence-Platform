# Chỉ mục tài liệu

Bản đồ toàn bộ tài liệu của dự án. Bắt đầu từ đây để tìm đúng file.

```
C2-App-116/
  README.md            tổng quan + cài đặt nhanh (đọc đầu tiên)
  docs/
    project/           tài liệu sản phẩm: cơ chế, kiến trúc, setup, vận hành
    harness/           quy trình cộng tác human + agent
  JOURNAL.md           nhật ký cohort
  WORKLOG.md           quyết định kỹ thuật theo ngày
```

## Tài liệu ở thư mục gốc

| File | Mục đích |
| --- | --- |
| `README.md` | Tổng quan dự án, tính năng, cài đặt nhanh, phân quyền |
| `JOURNAL.md` | Nhật ký học tập và hành trình sản phẩm của team |
| `WORKLOG.md` | Nhật ký quyết định kỹ thuật, phân công, bug quan trọng |
| `CLAUDE.md`, `AGENTS.md` | Hướng dẫn cho agent (harness tự nạp) |

## Sản phẩm (`docs/project/`)

### Cơ chế và kiến trúc

| File | Mục đích |
| --- | --- |
| `co_che.md` | Cơ chế tổng thể: luồng review đến ticket/alert/task/report, phân quyền, chia việc, cộng lộ trình cải thiện. Đọc cái này trước khi build lại |
| `giai_thich.md` | Giải thích as-is theo góc người dùng: một review đi từ đầu đến cuối |
| `architecture.md` | Kiến trúc tổng quan: 3 tầng, cấu trúc data, 6 service |
| `architecture-diagram.md` | Sơ đồ Mermaid các module |
| `ai-systems.md` | 4 lớp AI, LLM router, luồng dữ liệu theo worker |
| `agents-guide.md` | 8 agent + orchestrator: thứ tự thực thi, I/O, routing |
| `rbac-departments.md` | Phân quyền role và scope theo phòng ban |
| `guest-account.md` | Cơ chế tài khoản khách và chatbot CSKH |

### Cài đặt và triển khai

| File | Mục đích |
| --- | --- |
| `setup-macos.md` | Cài đặt môi trường macOS |
| `setup-windows.md` | Cài đặt môi trường Windows |
| `setup-supabase.md` | Cấu hình Supabase (auth, schema, migration) |
| `deploy-railway.md` | Deploy 6 service lên Railway |

### Vận hành và đánh giá

| File | Mục đích |
| --- | --- |
| `demo-script.md` | Kịch bản demo 5-7 phút |
| `eval-evidence.md` | Bằng chứng đánh giá model (Gate G2) |

Thư mục con: `product/`.

## Harness (`docs/harness/`)

Tài liệu quy trình cộng tác giữa human và agent.

| File | Mục đích |
| --- | --- |
| `HARNESS.md` | Cách human và agent cộng tác |
| `FEATURE_INTAKE.md` | Cách phân loại prompt thành tiny/normal/high-risk |
| `CONTEXT_RULES.md` | Context rules theo lane/phase |
| `TOOL_REGISTRY.md` | Danh sách tool được trang bị |
| `TRACE_SPEC.md` | Trace fields và quality tiers |
| `GLOSSARY.md` | Từ điển chung |
| `TEST_MATRIX.md` | Proof map |
| `HARNESS_COMPONENTS.md` | Map file đến responsibility |
| `HARNESS_MATURITY.md` | Mức maturity H0 đến H5 |
| `HARNESS_AUDIT.md` | Audit drift và entropy |
| `HARNESS_BACKLOG.md` | Improvement backlog |
| `IMPROVEMENT_PROTOCOL.md` | Review loop cho backlog proposals |

Thư mục con: `decisions/`, `stories/`, `templates/`, `superpowers/`.
