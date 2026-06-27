-- Chuyển từ 4 sang 6 phòng ban.
-- Phòng hợp lệ: IT, CSKH, Vận hành, Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận.
-- Marketing bị bỏ; user và dữ liệu lịch sử reassign về 'Sản phẩm'
-- (phản hồi tích cực/góp ý tính năng nay route về Sản phẩm).
--
-- LƯU Ý: profiles.department, alerts.assigned_team, tasks.assigned_team,
--        department_reports.team đều là TEXT, KHÔNG có CHECK constraint nên
--        không cần đổi schema. Migration này idempotent (chạy lại no-op).

UPDATE public.profiles           SET department    = 'Sản phẩm' WHERE department    = 'Marketing';
UPDATE public.alerts             SET assigned_team = 'Sản phẩm' WHERE assigned_team = 'Marketing';
UPDATE public.tasks              SET assigned_team = 'Sản phẩm' WHERE assigned_team = 'Marketing';
UPDATE public.department_reports SET team          = 'Sản phẩm' WHERE team          = 'Marketing';

COMMENT ON COLUMN public.profiles.department IS
  'Canonical RBAC department: IT, CSKH, Vận hành, Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận';
COMMENT ON COLUMN public.alerts.assigned_team IS
  'Team assignment: IT, CSKH, Vận hành, Tài chính & Thanh toán, Sản phẩm, Quản lý Rủi ro & Gian lận';
