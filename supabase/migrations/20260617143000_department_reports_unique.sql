-- Fix duplicate department reports: mỗi phòng ban chỉ có 1 báo cáo / ngày.
-- 1. Xoá các bản trùng, giữ lại bản mới nhất (created_at lớn nhất) cho mỗi (team, report_date).
-- 2. Thêm UNIQUE constraint để upsert hoạt động và chặn trùng về sau.

DELETE FROM public.department_reports a
USING public.department_reports b
WHERE a.team = b.team
  AND a.report_date = b.report_date
  AND a.created_at < b.created_at;

-- Trường hợp created_at bằng nhau (hiếm) — giữ id nhỏ hơn về mặt thứ tự
DELETE FROM public.department_reports a
USING public.department_reports b
WHERE a.team = b.team
  AND a.report_date = b.report_date
  AND a.created_at = b.created_at
  AND a.id < b.id;

ALTER TABLE public.department_reports
  ADD CONSTRAINT department_reports_team_date_unique UNIQUE (team, report_date);
