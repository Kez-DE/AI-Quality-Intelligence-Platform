# Spec: Điều phối Ticket → Giao việc (dispatcher/worker, nối Phân loại Ticket ↔ Quản lý công việc)

**Date:** 2026-07-03
**Lane:** High-risk (Authorization + đổi hành vi 2 luồng + Data)
**Nhánh:** `feat/real-ticket-workflow` (mở rộng PR #24 — thành mô hình điều phối đúng nghiệp vụ)

## Bối cảnh & vấn đề

PR #24 cho ops (staff/manager/admin) bấm đổi status alert tại chỗ — nhưng vai trò lẫn lộn và
KHÔNG nối sang Quản lý công việc. Alert do **agent tự sinh**; cần tách **điều phối** (manager/
admin) khỏi **thực thi** (nhân viên).

## Mô hình đúng (dispatcher → worker)

```
[AGENT tự động]  feedback → alert (open) + AI phân loại + định tuyến phòng
      ▼
[Phân loại Ticket = Admin + Manager]  manager/admin bấm "Tiếp nhận & Giao việc"
      ▼
  Alert → in_progress  +  tạo/gắn TASK (gom theo phòng+khu vực) ──► [Quản lý công việc]
      │                                                   manager giao owner (nhân viên)
      │                                                   nhân viên làm → duyệt → resolved
      ▼
  Alert tự đóng (task resolved → alert resolved)
```

## Thay đổi

### 1. RBAC & nav
- Trang `/alerts` (Phân loại Ticket): **chỉ admin + manager**. Đổi nav `AppShell.tsx` roles
  `AUTHENTICATED_ROLES` → `["admin","manager"]`. Component `alerts.tsx` gate: staff → thông
  báo không đủ quyền.
- Endpoint `PATCH /api/alerts/{id}/status`: đổi `require_ops_staff` → `require_manager`
  (manager + admin). Vẫn scope theo phòng (`can_view_team`); manager chỉ điều phối ticket
  phòng mình, admin toàn hệ thống.

### 2. Tiếp nhận → sinh việc (backend)
- Khi `open → in_progress` và alert **chưa có `task_id`**: **tạo-hoặc-gắn task** cho (phòng,
  khu vực) của alert → set `alert.task_id`.
- Tái dùng logic `task_agent`: **trích helper** `find_or_create_cluster_task(db, team, area,
  priority, title, summary)` (tìm task `open` cùng team+area → gắn; chưa có → insert task
  `status="open"`). Endpoint truyền title đơn giản (từ alert), **KHÔNG gọi LLM** (giữ click
  nhanh); `task_agent` giữ tiêu đề LLM cho nền.
- Task tạo ra ở `status="open"` → hiện ở Quản lý công việc để manager giao owner.

### 3. Đồng bộ task → alert (đóng)
- Khi task chuyển `resolved` (qua `update_task_status` hoặc `support_resolve`): **tự đóng các
  alert liên kết** (`task_id` = task, status != resolved → set `resolved` + `resolved_at` +
  `resolved_by`). Ghi audit.

### 4. Frontend `alerts.tsx`
- Nút `open`: đổi nhãn **"Nhận xử lý" → "Tiếp nhận & Giao việc"**; chỉ hiện cho manager/admin.
  Sau bấm: toast *"Đã tạo việc cho phòng {team} — chuyển Quản lý công việc"* + link "Xem việc"
  (`/tasks`).
- Giữ nút đóng trực tiếp (`in_progress→resolved`) cho manager/admin (ca đóng nhanh không cần
  vòng task đầy đủ) — nhãn "Đóng ticket".
- Badge/luồng real-time giữ nguyên (Supabase realtime đã có).

## Không đổi
- Agent sinh alert (spike detector), workflow task nội bộ, migration timing (#24 đã có),
  chat/RAG, MCP. Không migration mới (dùng `task_id` + cột timing #24).

## Validation
- RBAC: staff gọi `PATCH /api/alerts/{id}/status` → 403; không thấy nav /alerts. Manager phòng
  khác → 403. Manager/admin phòng mình → OK.
- Tiếp nhận: alert open (chưa task) → in_progress + có `task_id`; task xuất hiện ở /api/tasks
  (status open) đúng team+area; alert thứ 2 cùng cụm → gắn CÙNG task (không tạo trùng).
- Đồng bộ: resolve task → các alert `task_id` đó thành resolved + resolved_at.
- E2E thật: manager "Tiếp nhận" alert → task sinh → manager giao owner → resolve task → alert
  đóng.
- Full pytest + tsc + build.
