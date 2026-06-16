-- ============================================================
-- Tighten RLS policies: tasks, department_reports, agent_run_logs
-- + Add department column to profiles for team assignment
-- ============================================================
-- Previous migrations left overly permissive policies (FOR ALL TO authenticated USING (true)).
-- This migration replaces them with role-based access using helper functions
-- from 20260612120000_rbac_roles.sql: public.is_admin(), public.is_ops_staff().

-- ============================================================
-- 1) TASKS: tighten access
-- ============================================================

-- Drop the overly permissive policy
DROP POLICY IF EXISTS "Tasks manageable by authenticated users" ON public.tasks;

-- SELECT: ops staff (admin/manager/staff) can see all tasks; guest cannot
CREATE POLICY "Tasks select ops only" ON public.tasks
  FOR SELECT TO authenticated
  USING (public.is_ops_staff());

-- INSERT: only service_role (agents create tasks via backend)
-- Revoke direct INSERT from authenticated users
REVOKE INSERT ON public.tasks FROM authenticated;

CREATE POLICY "Tasks insert service_role" ON public.tasks
  FOR INSERT TO service_role
  WITH CHECK (true);

-- UPDATE: ops staff can update (change status, assign, etc.)
CREATE POLICY "Tasks update ops" ON public.tasks
  FOR UPDATE TO authenticated
  USING (public.is_ops_staff())
  WITH CHECK (public.is_ops_staff());

-- DELETE: admin only
CREATE POLICY "Tasks delete admin" ON public.tasks
  FOR DELETE TO authenticated
  USING (public.is_admin());

-- ============================================================
-- 2) DEPARTMENT_REPORTS: tighten access
-- ============================================================

-- Drop the overly permissive SELECT policy
DROP POLICY IF EXISTS "Reports viewable by authenticated users" ON public.department_reports;

-- SELECT: only admin and manager can view reports
CREATE POLICY "Reports select admin_manager" ON public.department_reports
  FOR SELECT TO authenticated
  USING (public.current_user_role() IN ('admin', 'manager'));

-- INSERT: only service_role (agents generate reports)
-- Revoke direct INSERT from authenticated users
REVOKE INSERT ON public.department_reports FROM authenticated;
REVOKE UPDATE ON public.department_reports FROM authenticated;
REVOKE DELETE ON public.department_reports FROM authenticated;

CREATE POLICY "Reports insert service_role" ON public.department_reports
  FOR INSERT TO service_role
  WITH CHECK (true);

-- ============================================================
-- 3) AGENT_RUN_LOGS: tighten access
-- ============================================================

-- Drop the overly permissive SELECT policy
DROP POLICY IF EXISTS "Authenticated users can view agent logs" ON public.agent_run_logs;

-- SELECT: admin and manager only
CREATE POLICY "Agent logs select admin_manager" ON public.agent_run_logs
  FOR SELECT TO authenticated
  USING (public.current_user_role() IN ('admin', 'manager'));

-- INSERT policy for service_role already exists from 20260615100000_agent_run_logs.sql
-- No changes needed for INSERT.

-- ============================================================
-- 4) PROFILES: add department column for team assignment
-- ============================================================

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS department TEXT;

COMMENT ON COLUMN public.profiles.department IS
  'Team assignment: IT, Safety, CSKH, Vận hành, Pricing, Marketing';

-- Allow authenticated users to read their own department (already covered by Profiles select policy).
-- Allow admin to update department via service_role (already bypasses RLS).

-- ============================================================
-- 5) FEEDBACK: verify guest can INSERT own + SELECT own
-- ============================================================
-- The existing policies from 20260612120000_rbac_roles.sql already handle this:
--   "Feedback select"     => auth.uid() = user_id OR is_ops_staff()
--   "Feedback insert own" => auth.uid() = user_id
-- Guest can INSERT their own feedback and SELECT their own feedback.
-- No changes needed — no conflicting policy names introduced here.
