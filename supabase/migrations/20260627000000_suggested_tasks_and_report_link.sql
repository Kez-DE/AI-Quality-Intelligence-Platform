-- HI-Loop Approval: liên kết báo cáo -> task có cấu trúc.
-- Lưu ý: 20260626000000 đã dùng cho task_completion_reports nên file này là 20260627000000.

ALTER TABLE public.department_reports
  ADD COLUMN IF NOT EXISTS suggested_tasks JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS root_cause_summary TEXT;

ALTER TABLE public.tasks
  ADD COLUMN IF NOT EXISTS report_id UUID REFERENCES public.department_reports(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'agent';

ALTER TABLE public.tasks DROP CONSTRAINT IF EXISTS tasks_source_check;
ALTER TABLE public.tasks ADD CONSTRAINT tasks_source_check CHECK (source IN ('agent','report'));

CREATE INDEX IF NOT EXISTS idx_tasks_report_id ON public.tasks(report_id);

-- Duyệt báo cáo + tạo task trong MỘT transaction (atomic).
-- p_tasks: jsonb array, mỗi item có {action, priority, success_metric, due_at(ISO|null)}.
CREATE OR REPLACE FUNCTION public.approve_report_and_dispatch(
  p_report_id uuid,
  p_tasks jsonb,
  p_approver uuid
) RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
  v_team text;
  v_updated int;
  v_created int := 0;
BEGIN
  UPDATE public.department_reports
    SET approved = true,
        approved_by = p_approver,
        approved_at = now(),
        suggested_tasks = p_tasks
    WHERE id = p_report_id AND approved = false
    RETURNING team INTO v_team;

  GET DIAGNOSTICS v_updated = ROW_COUNT;
  IF v_updated = 0 THEN
    RAISE EXCEPTION 'report_not_found_or_already_approved';
  END IF;

  INSERT INTO public.tasks
    (title, summary, assigned_team, priority, status, source, report_id, due_at)
  SELECT
    COALESCE(NULLIF(t->>'action', ''), 'Hành động chưa đặt tên'),
    t->>'success_metric',
    v_team,
    COALESCE(NULLIF(t->>'priority', ''), 'P3'),
    'open',
    'report',
    p_report_id,
    CASE WHEN COALESCE(t->>'due_at','') <> '' THEN (t->>'due_at')::timestamptz ELSE NULL END
  FROM jsonb_array_elements(p_tasks) AS t;

  GET DIAGNOSTICS v_created = ROW_COUNT;
  RETURN v_created;
END;
$$;
