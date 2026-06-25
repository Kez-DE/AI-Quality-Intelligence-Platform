-- Vòng đời task khép kín: thêm trạng thái + bảng audit task_events.
-- Backend chạy SERVICE_ROLE_KEY (bypass RLS); quyền gate ở tầng API. RLS là lớp phòng thủ.
-- FK completion_report_id cần task_completion_reports tồn tại. Một số môi trường remote bị
-- drift (20260626000000 ghi trong lịch sử nhưng bảng không tồn tại), nên ta tự đảm bảo bảng
-- tồn tại ở đây (idempotent, đồng bộ với 20260626000000) trước khi tạo FK.

-- 0) Đảm bảo task_completion_reports tồn tại
CREATE TABLE IF NOT EXISTS public.task_completion_reports (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  task_id UUID NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
  staff_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  staff_email TEXT,
  team TEXT NOT NULL,
  completion_level TEXT NOT NULL DEFAULT 'completed'
    CHECK (completion_level IN ('completed', 'partial', 'blocked')),
  note TEXT NOT NULL,
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

DROP POLICY IF EXISTS "Completion reports viewable by authenticated" ON public.task_completion_reports;
CREATE POLICY "Completion reports viewable by authenticated"
  ON public.task_completion_reports FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS "Completion reports insert by authenticated" ON public.task_completion_reports;
CREATE POLICY "Completion reports insert by authenticated"
  ON public.task_completion_reports FOR INSERT TO authenticated WITH CHECK (true);
DROP POLICY IF EXISTS "Completion reports manageable by service_role" ON public.task_completion_reports;
CREATE POLICY "Completion reports manageable by service_role"
  ON public.task_completion_reports FOR ALL TO service_role USING (true) WITH CHECK (true);

DO $$ BEGIN
  ALTER PUBLICATION supabase_realtime ADD TABLE public.task_completion_reports;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- 1) Mở rộng trạng thái task: open -> assigned -> in_progress -> pending_review -> resolved
ALTER TABLE public.tasks DROP CONSTRAINT IF EXISTS tasks_status_check;
ALTER TABLE public.tasks ADD CONSTRAINT tasks_status_check
  CHECK (status IN ('open','assigned','in_progress','pending_review','resolved'));

-- 2) Audit log vòng đời task
CREATE TABLE IF NOT EXISTS public.task_events (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  task_id UUID NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
  actor_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  actor_email TEXT,
  actor_role TEXT,
  team TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN (
    'assigned','accepted','completion_submitted',
    'completion_approved','completion_rejected','reopened','status_changed'
  )),
  from_status TEXT,
  to_status TEXT,
  completion_report_id UUID REFERENCES public.task_completion_reports(id) ON DELETE SET NULL,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_task_events_task_id ON public.task_events(task_id);
CREATE INDEX IF NOT EXISTS idx_task_events_team ON public.task_events(team, created_at DESC);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.task_events TO authenticated;
GRANT ALL ON public.task_events TO service_role;
ALTER TABLE public.task_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Task events viewable by authenticated" ON public.task_events;
CREATE POLICY "Task events viewable by authenticated"
  ON public.task_events FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS "Task events insert by authenticated" ON public.task_events;
CREATE POLICY "Task events insert by authenticated"
  ON public.task_events FOR INSERT TO authenticated WITH CHECK (true);
DROP POLICY IF EXISTS "Task events manageable by service_role" ON public.task_events;
CREATE POLICY "Task events manageable by service_role"
  ON public.task_events FOR ALL TO service_role USING (true) WITH CHECK (true);

COMMENT ON TABLE public.task_events IS
  'Audit log vòng đời task: giao -> nhận -> gửi báo cáo -> duyệt/trả lại. Ghi ở tầng API (có actor).';

DO $$ BEGIN
  ALTER PUBLICATION supabase_realtime ADD TABLE public.task_events;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
