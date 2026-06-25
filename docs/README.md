# Chỉ mục tài liệu

Bản đồ toàn bộ tài liệu của dự án. Bắt đầu từ đây để tìm đúng file.

```
C2-App-116/
  README.md            tổng quan + cài đặt nhanh (đọc đầu tiên)
  docs/
    project/           tài liệu sản phẩm: cơ chế, kiến trúc, dữ liệu, vận hành, setup
      architecture/    luồng E2E và taxonomy định tuyến
    harness/           quy trình cộng tác human + agent
    superpowers/       spec và plan của từng đợt phát triển
  pipeline/README.md   backend Python (ML + agent)
  supabase/README.md   schema, migrations, cách đồng bộ DB
  data/README.md       dữ liệu huấn luyện và tri thức
  scripts/README.md    công cụ vận hành (harness CLI)
```

## Đọc theo nhu cầu

- Muốn hiểu hệ thống làm gì, từ đầu đến cuối: đọc `project/co_che.md`, rồi `project/architecture.md`.
- Muốn hiểu dữ liệu và các bảng/trường trong Supabase: đọc `project/data-model.md`.
- Muốn chạy dự án trên máy: đọc `README.md` gốc, rồi `project/setup-*.md` và `supabase/README.md`.
- Muốn deploy: đọc `project/deploy-railway.md`.
- Muốn sửa code backend/AI: đọc `pipeline/README.md`, `project/ai-systems.md`, `project/agents-guide.md`.
- Muốn hiểu phân quyền: đọc `project/rbac-departments.md`.

## Tài liệu ở thư mục gốc

| File | Mục đích |
| --- | --- |
| `README.md` | Tổng quan dự án, tính năng, cài đặt nhanh, phân quyền |
| `JOURNAL.md` | Nhật ký học tập và hành trình sản phẩm của team |
| `WORKLOG.md` | Nhật ký quyết định kỹ thuật, phân công, bug quan trọng |
| `CLAUDE.md`, `AGENTS.md` | Hướng dẫn cho agent (harness tự nạp) |

## README của từng phần

| File | Mục đích |
| --- | --- |
| `pipeline/README.md` | Backend Python: ML phân loại, nhóm agent, chạy pipeline batch |
| `supabase/README.md` | Schema, danh sách migration, cách áp lên remote, lưu ý drift |
| `data/README.md` | Bộ dữ liệu huấn luyện, tri thức (knowledge base), manifest |
| `scripts/README.md` | Công cụ dòng lệnh, chủ yếu là harness CLI |

## Sản phẩm (`docs/project/`)

### Cơ chế và kiến trúc

| File | Mục đích |
| --- | --- |
| `co_che.md` | Cơ chế tổng thể: luồng review đến ticket/alert/task/report, phân quyền, chia việc, lộ trình cải thiện. Đọc trước khi dựng lại hệ thống |
| `giai_thich.md` | Giải thích theo góc người dùng: một review đi từ đầu đến cuối |
| `architecture.md` | Kiến trúc tổng quan: 3 tầng, cấu trúc dữ liệu, các service |
| `architecture-diagram.md` | Sơ đồ Mermaid các module |
| `architecture/e2e-flow.md` | Luồng xử lý phản hồi đầu cuối, kèm file mã tương ứng từng chặng |
| `architecture/routing-taxonomy.md` | Bảng topic đến phòng ban và quy tắc định tuyến |
| `ai-systems.md` | Các lớp AI, LLM router, luồng dữ liệu theo worker |
| `agents-guide.md` | Nhóm agent và orchestrator: thứ tự chạy, đầu vào/ra, định tuyến |

### Dữ liệu

| File | Mục đích |
| --- | --- |
| `data-model.md` | Data dictionary Supabase: mọi bảng, mọi trường, enum, RLS, hàm, sơ đồ quan hệ |

### Phân quyền và tài khoản

| File | Mục đích |
| --- | --- |
| `rbac-departments.md` | Phân quyền theo role và scope theo phòng ban |
| `guest-account.md` | Cơ chế tài khoản khách và chatbot CSKH |

### Cài đặt và triển khai

| File | Mục đích |
| --- | --- |
| `setup-macos.md` | Cài đặt môi trường macOS |
| `setup-windows.md` | Cài đặt môi trường Windows |
| `setup-supabase.md` | Cấu hình Supabase (auth, schema, migration) |
| `deploy-railway.md` | Deploy các service lên Railway |

### Vận hành và đánh giá

| File | Mục đích |
| --- | --- |
| `demo-script.md` | Kịch bản demo 5-7 phút |
| `eval-evidence.md` | Bằng chứng đánh giá model (Gate G2) |
| `roadmap.md` | Lộ trình mở rộng (6 phòng ban, Global Report) — định hướng tương lai, chưa triển khai |
| `product/README.md` | Ghi chú sản phẩm |

Lưu ý: nhóm "Cơ chế và kiến trúc" hiện có vài file chồng nội dung (`co_che.md`, `giai_thich.md`,
`architecture*.md`, `ai-systems.md`, `agents-guide.md`). Nếu cần gọn hơn, hướng hợp nhất đề
xuất là giữ `co_che.md` làm tài liệu cơ chế chính, `architecture.md` làm kiến trúc kỹ thuật,
và gộp phần AI vào `ai-systems.md`; các file còn lại trỏ về ba file này.

## Định tuyến và đánh giá routing

| File | Mục đích |
| --- | --- |
| `architecture/routing-taxonomy.md` | 4 phòng ban và bảng topic đến phòng |
| `architecture/e2e-flow.md` | Luồng đầu cuối, dùng để đối chiếu code |

## Spec và plan (`docs/superpowers/`)

Mỗi đợt phát triển có một cặp spec (thiết kế) và plan (kế hoạch triển khai).

| File | Mục đích |
| --- | --- |
| `specs/2026-06-25-task-completion-loop-design.md` | Thiết kế vòng khép kín giao việc và duyệt hoàn thành task |
| `plans/2026-06-25-task-completion-loop.md` | Kế hoạch triển khai vòng khép kín đó |
| `specs/2026-06-25-router-accuracy-design.md` | Thiết kế cải thiện độ chính xác định tuyến |
| `plans/2026-06-25-router-accuracy.md` | Kế hoạch cải thiện định tuyến |
| `specs/2026-06-25-hiloop-approval-design.md` | Thiết kế HI-Loop Approval (manager duyệt báo cáo thành task) |
| `plans/2026-06-25-hiloop-approval.md` | Kế hoạch HI-Loop Approval |

## Harness (`docs/harness/`)

Tài liệu quy trình cộng tác giữa human và agent.

| File | Mục đích |
| --- | --- |
| `HARNESS.md` | Cách human và agent cộng tác |
| `FEATURE_INTAKE.md` | Cách phân loại prompt thành tiny/normal/high-risk |
| `CONTEXT_RULES.md` | Context rules theo lane và phase |
| `TOOL_REGISTRY.md` | Danh sách tool được trang bị |
| `TRACE_SPEC.md` | Trace fields và quality tiers |
| `GLOSSARY.md` | Từ điển chung |
| `TEST_MATRIX.md` | Proof map |
| `HARNESS_COMPONENTS.md` | Map file đến trách nhiệm |
| `HARNESS_MATURITY.md` | Mức maturity H0 đến H5 |
| `HARNESS_AUDIT.md` | Audit drift và entropy |
| `HARNESS_BACKLOG.md` | Backlog cải thiện |
| `IMPROVEMENT_PROTOCOL.md` | Review loop cho đề xuất cải thiện |

Thư mục con: `decisions/`, `stories/`, `templates/`, `superpowers/`.
</content>
