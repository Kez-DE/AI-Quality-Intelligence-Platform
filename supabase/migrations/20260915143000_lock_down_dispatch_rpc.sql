-- Siết quyền gọi RPC duyệt báo cáo -> tạo task.
--
-- Đo trên production 2026-09-15 (pg_proc):
--   prosecdef = f          → SECURITY INVOKER
--   proconfig = NULL       → search_path không pin
--   proacl    = {=X/postgres, anon=X/postgres, authenticated=X/postgres, ...}
--
-- Nghĩa là PostgREST phơi /rest/v1/rpc/approve_report_and_dispatch cho cả anon.
-- Probe bằng publishable key trả 42501 "permission denied for table
-- department_reports" — hàm ĐÃ chạy, chỉ dừng ở quyền bảng. Toàn bộ RBAC nằm ở
-- FastAPI (require_manager + can_view_team), nên một lệnh GRANT sai trong tương
-- lai là mở lại đường vượt mặt hoàn toàn. Backend chạy bằng service_role nên
-- siết EXECUTE không chạm luồng thật nào.
--
-- Rollback: GRANT EXECUTE ON FUNCTION public.approve_report_and_dispatch(uuid, jsonb, uuid)
--           TO anon, authenticated;  (không khuyến nghị — xem lý do ở trên)

ALTER FUNCTION public.approve_report_and_dispatch(uuid, jsonb, uuid)
  SET search_path = pg_catalog, public;

REVOKE ALL ON FUNCTION public.approve_report_and_dispatch(uuid, jsonb, uuid)
  FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.approve_report_and_dispatch(uuid, jsonb, uuid)
  TO service_role;
