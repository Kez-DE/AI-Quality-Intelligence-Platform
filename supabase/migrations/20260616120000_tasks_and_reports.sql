-- Create tasks table to group alerts
CREATE TABLE public.tasks (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  owner_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  summary TEXT,
  assigned_team TEXT NOT NULL,
  topic TEXT,
  area TEXT,
  priority TEXT NOT NULL DEFAULT 'P2',
  status TEXT NOT NULL DEFAULT 'open',
  due_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.tasks TO authenticated;
GRANT ALL ON public.tasks TO service_role;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Tasks manageable by authenticated users" ON public.tasks FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- Add task_id to alerts
ALTER TABLE public.alerts ADD COLUMN task_id UUID REFERENCES public.tasks(id) ON DELETE SET NULL;
CREATE INDEX idx_alerts_task_id ON public.alerts(task_id);

-- Create department reports table
CREATE TABLE public.department_reports (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  team TEXT NOT NULL,
  report_date DATE NOT NULL DEFAULT CURRENT_DATE,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.department_reports TO authenticated;
GRANT ALL ON public.department_reports TO service_role;
ALTER TABLE public.department_reports ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Reports viewable by authenticated users" ON public.department_reports FOR SELECT TO authenticated USING (true);
CREATE POLICY "Reports manageable by service_role" ON public.department_reports FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Realtime publication
ALTER PUBLICATION supabase_realtime ADD TABLE public.tasks;
ALTER PUBLICATION supabase_realtime ADD TABLE public.department_reports;
