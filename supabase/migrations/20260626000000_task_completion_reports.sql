-- Luồng "Báo cáo hoàn thành" (staff -> manager).
-- KHÁC với task (việc cần xử lý) và department_reports (báo cáo phân tích của analyst_agent).
-- Nhân viên sau khi xử lý task sẽ gửi báo cáo mức độ hoàn thành; quản lý duyệt/phản hồi.
--
-- Backend chạy bằng SERVICE_ROLE_KEY (bypass RLS) nên quyền được gate ở tầng API
-- (pipeline/auth_guard.py + scope theo phòng ban). RLS bên dưới chỉ là lớp phòng thủ.

CREATE TABLE IF NOT EXISTS public.task_completion_reports (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  task_id UUID NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
  staff_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  staff_email TEXT,
  team TEXT NOT NULL,
  -- Mức độ hoàn thành do nhân viên tự đánh giá.
  completion_level TEXT NOT NULL DEFAULT 'completed'
    CHECK (completion_level IN ('completed', 'partial', 'blocked')),
  note TEXT NOT NULL,
  -- Trạng thái duyệt của quản lý.
  status TEXT NOT NULL DEFAULT 'submitted'
    CHECK (status IN ('submitted', 'approved', 'rejected')),
  reviewed_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  reviewed_at TIMESTAMPTZ,
  review_note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tcr_task_id ON public.task_completion_reports(task_id);
CREATE INDEX IF NOT EXISTS idx_tcr_team_status ON public.task_completion_reports(team, status);
CREATE INDEX IF NOT EXISTS idx_tcr_staff_id ON public.task_completion_reports(staff_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.task_completion_reports TO authenticated;
GRANT ALL ON public.task_completion_reports TO service_role;

ALTER TABLE public.task_completion_reports ENABLE ROW LEVEL SECURITY;

-- Đọc: authenticated (gate phòng ban thực hiện ở tầng API).
CREATE POLICY "Completion reports viewable by authenticated"
  ON public.task_completion_reports FOR SELECT TO authenticated USING (true);
-- Ghi: service_role (backend). Cho phép authenticated insert để dự phòng client trực tiếp.
CREATE POLICY "Completion reports insert by authenticated"
  ON public.task_completion_reports FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "Completion reports manageable by service_role"
  ON public.task_completion_reports FOR ALL TO service_role USING (true) WITH CHECK (true);

COMMENT ON TABLE public.task_completion_reports IS
  'Báo cáo hoàn thành của nhân viên cho từng task (staff -> manager). Tách biệt với department_reports (analyst).';

-- Realtime: quản lý nhận thông báo khi có báo cáo hoàn thành mới.
ALTER PUBLICATION supabase_realtime ADD TABLE public.task_completion_reports;
