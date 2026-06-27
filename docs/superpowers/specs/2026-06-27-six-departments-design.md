# Thiết kế: Chuyển 4 → 6 phòng ban (trích từ `docs`, áp lên `main`)

- Ngày: 2026-06-27
- Lane: **High-risk** (authorization scope + data migration + routing contract + multi-domain)
- Trạng thái: Đã chốt thiết kế, chờ lập plan thực thi.

## 1. Bối cảnh

Hai branch đã rẽ nhánh trên **cùng một vùng tính năng**. Branch `docs` có đúng một commit
riêng (`d2d38f7 "sửa báo cáo AI"`) gói **hai việc không liên quan**:

1. Migration 4 → 6 phòng ban (phần muốn lấy).
2. Một bản revamp Báo cáo AI **của riêng docs** + file rác `scratch/fix*.py` + `IMPLEMENTATION_PLAN.md`
   bị thêm lại (đã từng bị xoá ở `d72e5cd`).

Trong khi đó `main` đã ship **một bản revamp Báo cáo AI khác, đã verified** (nhiều báo cáo/ngày,
body 3 khối, lịch 09:00/14:00, tên task trong báo cáo hoàn thành).

`git merge origin/docs` chỉ xung đột ở vùng báo cáo (`report_builder.py`, `schemas.py`,
`task_agent.py`, `test_report_approval.py`) — chính là bản revamp trùng của docs đụng bản của main.

### Trạng thái hiện tại của `docs` (nửa vời, mâu thuẫn nội tại)

| Hạng mục | `docs` đã làm | Vấn đề |
| --- | --- | --- |
| `departments.py`, `analyst_agent.py` personas, `routing_table.json` | Đã là **6 phòng** | OK, lấy về |
| `co_che.md`, `roadmap.md`, `rbac-departments.md` | Vẫn ghi **"4 phòng + Marketing"** | Mâu thuẫn chính code của nó |
| `spike_detector.py:146` | Vẫn `team == "Marketing"` | **Bug cơ chế ticket**: ticket "opportunity" thành dead vì positive nay route về Sản phẩm |
| `router_agent.py`, `alerts.tsx`, `build_public_kb.py` | Vẫn tham chiếu Marketing | Rác cần dọn |

## 2. Quyết định đã chốt

1. **Chiến lược merge**: KHÔNG full-merge `origin/docs`. Trích **chỉ** delta 4 → 6 phòng ban áp
   lên `main`. Bỏ bản revamp báo cáo của docs, `scratch/fix*.py`, `IMPLEMENTATION_PLAN.md` thêm lại.
   Giữ nguyên bản revamp báo cáo đã verified của `main`.
2. **Xử lý dữ liệu Marketing**: reassign user + alerts/tasks lịch sử `Marketing` → **Sản phẩm**
   (vì phản hồi tích cực/góp ý tính năng nay route về Sản phẩm). Làm bằng data migration.
3. **Phạm vi cơ chế ticket**: bounded — bảng routing 6 phòng + fix bug opportunity + dọn tham chiếu
   Marketing + đồng bộ toàn bộ docs prose. **Không** làm Global Report chéo phòng, **không** retune SLA.

## 3. Sáu phòng ban đích

`IT`, `CSKH`, `Vận hành`, `Tài chính & Thanh toán`, `Sản phẩm`, `Quản lý Rủi ro & Gian lận`
(bỏ **Marketing**).

| Phòng | Việc chính | Topic/route về |
| --- | --- | --- |
| IT | Lỗi app, server, API, GPS, thanh toán kỹ thuật | App Issue |
| CSKH | Tiếp nhận khiếu nại, hỗ trợ khách, catch-all | Other, default_team |
| Vận hành | Tài xế, chuyến xe, an toàn, điều phối | Safety, Driver Behavior, Delay, override P5 |
| Tài chính & Thanh toán | Hoàn tiền, đối soát giao dịch | Payment |
| Sản phẩm | UX/UI, nâng cấp tính năng, khai thác phản hồi tích cực | positive sentiment override (Other, App Issue) |
| Quản lý Rủi ro & Gian lận | Gian lận, lạm dụng khuyến mãi, giá cước bất thường | Pricing |

## 4. Thay đổi theo thành phần (file cụ thể)

### 4.1 Backend — định nghĩa phòng & chia việc
- `pipeline/departments.py`: `DEPARTMENTS` 4 → 6; bỏ alias `marketing`, thêm alias
  finance/payment, product/sản phẩm, risk/fraud/rủi ro/gian lận; sửa docstring "four" → "six".
- `pipeline/agents/analyst_agent.py`: `DEPARTMENT_PERSONAS` bỏ Marketing, thêm 3 persona
  (Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận) — lấy từ `docs`.
- `pipeline/agents/orchestrator.py`: vòng lặp insight/analyst chạy `list(DEPARTMENTS)` thay vì
  list 4 phòng hardcode.
- `pipeline/users_admin.py`: bảo đảm `valid_departments` suy ra từ `DEPARTMENTS` (dynamic).

### 4.2 Backend — cơ chế ticket
- `data/taxonomy/routing_table.json`: Payment → **Tài chính & Thanh toán**; Pricing →
  **Quản lý Rủi ro & Gian lận**; sentiment override positive → **Sản phẩm** (topics
  `["Other","App Issue"]`).
- `pipeline/spike_detector.py:146`: **fix bug** `team == "Marketing"` → `team == "Sản phẩm"`
  để ticket "opportunity" vẫn phát sau khi đổi route.
- `pipeline/agents/router_agent.py`: fallback `normalize_department(..., "Marketing")` →
  `"Sản phẩm"`; cập nhật comment và ví dụ `__main__`.
- `pipeline/scripts/build_public_kb.py:18`: tag KB "Marketing" → "Sản phẩm".

### 4.3 Frontend
- `app/src/lib/api.ts`: type `Department` + `ALL_TEAMS` 4 → 6; comment "4 phòng ban" → "6".
- `app/src/routes/_authenticated/alerts.tsx`: map nhãn/màu phòng bỏ Marketing + thêm 3;
  "Cơ hội Marketing" → "Cơ hội Sản phẩm".
- `app/src/components/DepartmentBadge.tsx`: map màu bỏ Marketing + thêm 3 phòng mới.
- `app/src/routes/_authenticated/admin.tsx`: thừa hưởng `ALL_TEAMS` tự động (verify).

### 4.4 Database — data migration (không đổi schema; `department` là TEXT, không CHECK)
- Migration mới `supabase/migrations/<ts>_six_departments.sql`:
  - `UPDATE profiles SET department='Sản phẩm' WHERE department='Marketing';`
  - `UPDATE alerts SET assigned_team='Sản phẩm' WHERE assigned_team='Marketing';`
  - `UPDATE tasks SET assigned_team='Sản phẩm' WHERE assigned_team='Marketing';`
  - Cập nhật COMMENT liệt kê 6 phòng. Idempotent (chạy lại no-op).

### 4.5 Docs sync (prose đang mâu thuẫn với code)
- `co_che.md` §4 (routing), §6 (Phòng ban), §7 (RBAC diagram + valid_departments), §10
  (orchestrator Step 6-7, sentiment override).
- `docs/project/rbac-departments.md`: mục "4 phòng ban" → 6, valid_departments, diagram.
- `docs/project/roadmap.md`: đánh dấu mục "4 → 6" là **đã triển khai**; giữ Global Report +
  hướng khác là tương lai.
- Sweep `MASTER_BLUEPRINT.md`, `docs/project/architecture.md`, `agents-guide.md`,
  `giai_thich.md` tìm "4 phòng ban"/Marketing.

### 4.6 Tests
- Cập nhật `pipeline/tests/test_departments.py`, `test_department_rbac.py` về bộ 6 phòng.
- Thêm test snapshot routing (Payment→Tài chính, Pricing→Rủi ro&Gian lận, positive→Sản phẩm)
  và test spike opportunity → Sản phẩm (đóng gap G8/P1-5 trong co_che.md).

## 5. Error handling & an toàn
- `normalize_department` trả `default` cho giá trị lạ → chuỗi "Marketing" tự do cũ resolve an toàn
  sau khi bỏ alias; row đã lưu được migration xử lý.
- Migration idempotent.
- Gate API (`auth_guard`) là nguồn chân lý cho scope; phòng mới chỉ thấy dữ liệu sau khi admin gán.

## 6. Ngoài phạm vi (hoãn)
Global Report chéo phòng, retune SLA/priority, bản revamp báo cáo của docs, việc P0 RLS.

## 7. Tiêu chí hoàn thành
- `DEPARTMENTS` = đúng 6 phòng; không còn tham chiếu "Marketing" trong code/docs (trừ migration
  lịch sử và ghi chú di trú).
- Routing: Payment→Tài chính, Pricing→Rủi ro&Gian lận, positive→Sản phẩm; opportunity ticket phát
  cho Sản phẩm.
- Migration reassign Marketing→Sản phẩm chạy sạch trên Supabase.
- Frontend hiện đủ 6 phòng (badge, admin assign, alerts).
- Bản revamp báo cáo AI của `main` không bị hồi quy.
- Test xanh, gồm snapshot routing + departments mới.
