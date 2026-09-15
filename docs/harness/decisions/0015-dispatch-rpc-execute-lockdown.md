# 0015 approve_report_and_dispatch chỉ service_role được EXECUTE

Date: 2026-09-15

## Status

Accepted

## Context

`20260827034856_dispatch_hardening.sql` tạo `public.approve_report_and_dispatch`
mà không khai báo mode, không pin `search_path`, và không thu hồi `EXECUTE`.
Postgres mặc định cấp `EXECUTE` cho `PUBLIC`, nên PostgREST phơi hàm ở
`/rest/v1/rpc/approve_report_and_dispatch` cho cả `anon`.

Đo trên production `gvtoqbowulwmpzfogjwp` ngày 2026-09-15:

```text
prosecdef = f
proconfig = NULL
proacl    = {=X/postgres, postgres=X/postgres, anon=X/postgres,
             authenticated=X/postgres, service_role=X/postgres}
```

Probe bằng publishable key với `p_report_id` không tồn tại trả
`42501 permission denied for table department_reports` — tức hàm đã chạy và chỉ
dừng lại ở quyền bảng. Hàm cũng tin tưởng `p_approver` làm đối số, không kiểm tra
role hay phòng ban của người gọi: toàn bộ RBAC nằm ở FastAPI (`require_manager`
+ `can_view_team`), nên đường gọi RPC trực tiếp đi vòng qua hết.

Bảo vệ hiện tại đến từ table grant, không đến từ thiết kế hàm. Một lệnh `GRANT`
sai trong tương lai là mở lại đường vượt mặt hoàn toàn.

## Decision

Thu hồi `EXECUTE` khỏi `PUBLIC`, `anon`, `authenticated`; chỉ `service_role` giữ
quyền gọi. Pin `search_path = pg_catalog, public`. Ghi ở
`supabase/migrations/20260915143000_lock_down_dispatch_rpc.sql`.

Backend chạy bằng `service_role` nên không luồng thật nào mất quyền. Frontend
không có lệnh `.rpc(` nào tới hàm này.

## Alternatives Considered

1. Chuyển hàm sang `SECURITY DEFINER` và validate role/phòng ban bên trong SQL.
   Bỏ: `DEFINER` mà authorization rỗng thì tệ hơn hiện trạng, và sẽ nhân đôi
   luật RBAC đang sống ở tầng API.
2. Giữ nguyên, dựa vào table grant. Bỏ: đó là phòng thủ tình cờ, không phải
   thiết kế; không có test nào khoá lại.

## Consequences

Positive:

- Đường RPC không còn là cửa vòng qua RBAC tầng API, kể cả khi table grant đổi.
- `search_path` pin chặn tấn công tráo schema.

Tradeoffs:

- Bất kỳ client tương lai muốn gọi hàm bằng JWT người dùng sẽ phải đi qua API.

## Follow-Up

- Thêm integration test khẳng định JWT `authenticated` nhận `42501` khi gọi RPC
  và khi `update` thẳng `tasks`.
- Cân nhắc partial unique index `(assigned_team, area, topic)` cho task đang mở
  để chặn race tạo trùng cụm (xem review `task_agent.py:133`).
