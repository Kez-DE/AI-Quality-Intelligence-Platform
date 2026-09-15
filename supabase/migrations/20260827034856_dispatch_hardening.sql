-- Siết đường phân phối việc: RPC báo cáo->task, index cho truy vấn nóng, và khoá
-- quyền ghi trực tiếp từ trình duyệt.
--
-- Bối cảnh (đo trên dữ liệu thật 2026-08-27):
--   * 19/19 task do agent sinh có topic='General', due_at NULL, owner NULL.
--   * approve_report_and_dispatch bỏ trống topic/area và đặt summary = success_metric,
--     nên task từ báo cáo mất ngữ cảnh (phụ trách, hạn đề xuất) ngay khi tạo.
--   * tasks không có index nào cho (assigned_team, area, topic, status) — đúng truy vấn
--     mà task_agent chạy mỗi cụm, mỗi chu kỳ.
--   * authenticated có quyền UPDATE/DELETE thẳng trên tasks/feedback/task_events/
--     task_completion_reports với policy USING(true) hoặc is_ops_staff(), tức là mọi
--     cổng RBAC ở tầng API đều có thể bị vượt qua từ DevTools.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. RPC duyệt báo cáo -> tạo task: giữ nguyên chữ ký, bổ sung ngữ cảnh
-- ─────────────────────────────────────────────────────────────────────────────
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
    (title, summary, assigned_team, topic, area, priority, status, source, report_id, due_at)
  SELECT
    COALESCE(NULLIF(t->>'action', ''), 'Hành động chưa đặt tên'),
    -- Trước đây summary = success_metric, làm mất phụ trách và hạn đề xuất mà manager
    -- đã biên tập; người nhận việc chỉ thấy tiêu chí đo, không thấy ai chịu trách nhiệm.
    NULLIF(
      concat_ws(
        E'\n',
        NULLIF(t->>'success_metric', ''),
        CASE WHEN NULLIF(t->>'owner', '') IS NOT NULL
             THEN 'Phụ trách đề xuất: ' || (t->>'owner') END,
        CASE WHEN NULLIF(t->>'deadline', '') IS NOT NULL
             THEN 'Hạn đề xuất: ' || (t->>'deadline') END
      ), ''
    ),
    v_team,
    -- topic/area chỉ ghi khi payload thật sự có. Báo cáo là cấp phòng ban nên thường
    -- không gắn khu vực — để NULL là trung thực, không bịa giá trị cho vừa bộ lọc.
    NULLIF(t->>'topic', ''),
    NULLIF(t->>'area', ''),
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

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Index cho truy vấn nóng
-- ─────────────────────────────────────────────────────────────────────────────

-- task_agent tìm task còn hút được alert theo đúng bộ khoá này, mỗi cụm mỗi chu kỳ.
CREATE INDEX IF NOT EXISTS idx_tasks_cluster
  ON public.tasks (assigned_team, area, topic, status);

-- Bảng công việc lọc theo trạng thái + mới nhất.
CREATE INDEX IF NOT EXISTS idx_tasks_status_created
  ON public.tasks (status, created_at DESC);

-- Vòng gom cụm quét đúng tập alert chưa có task; index từng phần nên rất nhỏ.
CREATE INDEX IF NOT EXISTS idx_alerts_unassigned
  ON public.alerts (status, created_at DESC)
  WHERE task_id IS NULL;

-- ml-worker quét feedback chưa chấm rủi ro mỗi 30 giây.
CREATE INDEX IF NOT EXISTS idx_feedback_unscored
  ON public.feedback (created_at DESC)
  WHERE overall_risk IS NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Khoá đường ghi trực tiếp từ trình duyệt
--    Backend chạy bằng service_role nên không bị ảnh hưởng. Frontend chỉ ghi thẳng
--    Supabase ở bảng chat_messages (giữ nguyên) và cần SELECT để realtime hoạt động.
-- ─────────────────────────────────────────────────────────────────────────────

-- tasks: đọc được (realtime + fallback), ghi phải đi qua API để chịu _assert_transition,
-- can_view_team và _log_task_event.
REVOKE INSERT, UPDATE, DELETE ON public.tasks FROM authenticated;
REVOKE ALL ON public.tasks FROM anon;
DROP POLICY IF EXISTS "Tasks update ops" ON public.tasks;
DROP POLICY IF EXISTS "Tasks delete admin" ON public.tasks;

-- feedback: giữ quyền gửi phản hồi của chính mình; bỏ quyền sửa/xoá vì sửa thẳng sẽ
-- dọn sạch hàng đợi duyệt mà không để lại dòng correction_logs nào.
REVOKE UPDATE, DELETE ON public.feedback FROM authenticated;
REVOKE ALL ON public.feedback FROM anon;
DROP POLICY IF EXISTS "Feedback update own or ops" ON public.feedback;
DROP POLICY IF EXISTS "Feedback delete own or admin" ON public.feedback;

-- alerts: cùng lý do; ticket chỉ được đổi trạng thái qua endpoint có kiểm tra phòng ban.
REVOKE INSERT, UPDATE, DELETE ON public.alerts FROM authenticated;
REVOKE ALL ON public.alerts FROM anon;
DROP POLICY IF EXISTS "Alerts insert own" ON public.alerts;
DROP POLICY IF EXISTS "Alerts update own or ops" ON public.alerts;
DROP POLICY IF EXISTS "Alerts delete own or admin" ON public.alerts;

-- task_events là audit trail: chèn/sửa/xoá được từ client thì nó không còn là bằng chứng.
REVOKE INSERT, UPDATE, DELETE ON public.task_events FROM authenticated;
REVOKE ALL ON public.task_events FROM anon;
DROP POLICY IF EXISTS "Task events insert by authenticated" ON public.task_events;
DROP POLICY IF EXISTS "Task events viewable by authenticated" ON public.task_events;
-- Postgres không có CREATE POLICY IF NOT EXISTS; thiếu dòng này thì lần chạy thứ
-- hai (db reset, dựng môi trường mới) abort 42710 và mọi lệnh phía dưới không chạy.
DROP POLICY IF EXISTS "Task events viewable by ops" ON public.task_events;
CREATE POLICY "Task events viewable by ops" ON public.task_events
  FOR SELECT TO authenticated
  USING (public.is_ops_staff());

-- task_completion_reports: nội dung do nhân viên gửi qua API (có kiểm tra owner).
REVOKE INSERT, UPDATE, DELETE ON public.task_completion_reports FROM authenticated;
REVOKE ALL ON public.task_completion_reports FROM anon;
DROP POLICY IF EXISTS "Completion reports insert by authenticated" ON public.task_completion_reports;
DROP POLICY IF EXISTS "Completion reports viewable by authenticated" ON public.task_completion_reports;
DROP POLICY IF EXISTS "Completion reports viewable by ops" ON public.task_completion_reports;
CREATE POLICY "Completion reports viewable by ops" ON public.task_completion_reports
  FOR SELECT TO authenticated
  USING (public.is_ops_staff());

REVOKE ALL ON public.department_reports FROM anon;

-- Supabase cấp sẵn TRUNCATE cho authenticated. PostgREST không phơi truncate ra HTTP,
-- nhưng một RPC bất kỳ chạy dưới quyền người gọi thì có; không có lý do gì để giữ.
REVOKE TRUNCATE ON public.tasks, public.alerts, public.feedback, public.task_events,
                   public.task_completion_reports, public.department_reports
  FROM authenticated;
