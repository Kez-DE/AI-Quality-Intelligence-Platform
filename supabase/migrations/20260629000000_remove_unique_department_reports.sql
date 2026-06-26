-- Cho phép nhiều báo cáo/ngày cho mỗi phòng: bỏ unique (team, report_date).
ALTER TABLE public.department_reports
  DROP CONSTRAINT IF EXISTS department_reports_team_date_unique;
