-- US-077 / decision 0017: retire the 'guest' role; add the retention redaction marker.
--
-- 'guest' did two jobs: the customer account, and the state every self-signup
-- landed in until an admin approved it. Customers now report through the
-- Customer web with no account, so only the second job is left, and it gets an
-- honest name: 'pending' — an account with no access until an admin grants
-- admin, manager or staff.
--
-- No row is deleted. Existing guest accounts become pending and keep their
-- feedback: every FK to auth.users is ON DELETE CASCADE, so deleting an account
-- would delete its feedback, alerts and chat history with it.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. profiles.role: guest -> pending
-- ─────────────────────────────────────────────────────────────────────────────
-- The old CHECK rejects 'pending', so it must go before the UPDATE. Dropped by
-- definition rather than by name: it was declared inline (auto-named
-- profiles_role_check here), and a hand-built environment may name it differently.
DO $$
DECLARE c record;
BEGIN
  FOR c IN
    SELECT conname FROM pg_constraint
    WHERE conrelid = 'public.profiles'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) LIKE '%guest%'
  LOOP
    EXECUTE format('ALTER TABLE public.profiles DROP CONSTRAINT %I', c.conname);
  END LOOP;
END $$;

UPDATE public.profiles SET role = 'pending' WHERE role = 'guest';

ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
ALTER TABLE public.profiles
  ADD CONSTRAINT profiles_role_check
  CHECK (role IN ('admin', 'manager', 'staff', 'pending'));

-- The column default was still 'staff' from 20260612120000, so any profile
-- inserted outside the trigger got ops access by default. Fail closed instead.
ALTER TABLE public.profiles ALTER COLUMN role SET DEFAULT 'pending';

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Sign-up trigger: new accounts are pending
-- ─────────────────────────────────────────────────────────────────────────────
-- Keeps the bootstrap: the first profile ever becomes admin, so a fresh
-- environment still has someone who can create accounts.
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  assigned_role TEXT;
BEGIN
  IF (SELECT COUNT(*) FROM public.profiles) = 0 THEN
    assigned_role := 'admin';
  ELSE
    assigned_role := 'pending';
  END IF;

  INSERT INTO public.profiles (id, email, full_name, role)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
    assigned_role
  );
  RETURN NEW;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM PUBLIC, anon, authenticated;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. feedback: direct INSERT only for ops staff, as themselves
-- ─────────────────────────────────────────────────────────────────────────────
-- "Feedback insert own" let any signed-in account write rows through PostgREST
-- with self-chosen topic, severity and overall_risk, skipping the classifier and
-- the rate limit. Staff web submissions go through the backend (service role),
-- so this only narrows the browser path.
DROP POLICY IF EXISTS "Feedback insert own" ON public.feedback;
DROP POLICY IF EXISTS "Feedback insert ops" ON public.feedback;
CREATE POLICY "Feedback insert ops" ON public.feedback
  FOR INSERT TO authenticated
  WITH CHECK (public.is_ops_staff() AND auth.uid() = user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. mcp_tokens.role: legacy column, same vocabulary
-- ─────────────────────────────────────────────────────────────────────────────
-- Not the source of truth since 20260702010000 (role resolves live from
-- profiles), but its CHECK still names 'guest'.
DO $$
DECLARE c record;
BEGIN
  FOR c IN
    SELECT conname FROM pg_constraint
    WHERE conrelid = 'public.mcp_tokens'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) LIKE '%guest%'
  LOOP
    EXECUTE format('ALTER TABLE public.mcp_tokens DROP CONSTRAINT %I', c.conname);
  END LOOP;
END $$;

UPDATE public.mcp_tokens SET role = 'pending' WHERE role = 'guest';

ALTER TABLE public.mcp_tokens DROP CONSTRAINT IF EXISTS mcp_tokens_role_check;
ALTER TABLE public.mcp_tokens
  ADD CONSTRAINT mcp_tokens_role_check
  CHECK (role IN ('admin', 'manager', 'staff', 'pending'));

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. profiles: no self-insert or self-delete from the browser
-- ─────────────────────────────────────────────────────────────────────────────
-- "Users insert own profile" (20260606100321) let an account without a profile
-- row insert one with any role, admin included. The trigger always creates the
-- row, so the hole was dormant, but every self-signup is now an untrusted
-- pending account. Profiles are created only by the SECURITY DEFINER trigger
-- and changed only by the backend (service role).
DROP POLICY IF EXISTS "Users insert own profile" ON public.profiles;
REVOKE INSERT, DELETE, TRUNCATE ON public.profiles FROM authenticated;

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. RLS helpers refuse an account still on its temporary password
-- ─────────────────────────────────────────────────────────────────────────────
-- An admin-created account carries app_metadata.must_change_password = true
-- (only the service role can write app_metadata). The backend returns 403 to it;
-- this closes the same door for direct PostgREST and realtime access. The claim
-- comes from the JWT, which the client refreshes after the password change.
CREATE OR REPLACE FUNCTION public.password_is_current()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SET search_path = public
AS $$
  SELECT COALESCE((auth.jwt() -> 'app_metadata' ->> 'must_change_password')::boolean, false) = false;
$$;

CREATE OR REPLACE FUNCTION public.is_ops_staff()
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
  SELECT public.current_user_role() IN ('admin', 'manager', 'staff')
     AND public.password_is_current();
$$;

CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
  SELECT public.current_user_role() = 'admin'
     AND public.password_is_current();
$$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. graph_nodes / graph_edges: internal knowledge base, ops staff only
-- ─────────────────────────────────────────────────────────────────────────────
-- USING (true) let any signed-in account — now any self-signup, as a pending
-- account — read the internal SOP/SLA knowledge base. The backend reads it with
-- the service role, so narrowing the browser path changes nothing for it.
DROP POLICY IF EXISTS "Allow read access for authenticated users on graph_nodes" ON public.graph_nodes;
DROP POLICY IF EXISTS "Allow read access for authenticated users on graph_edges" ON public.graph_edges;
DROP POLICY IF EXISTS "Graph nodes select ops" ON public.graph_nodes;
DROP POLICY IF EXISTS "Graph edges select ops" ON public.graph_edges;
CREATE POLICY "Graph nodes select ops" ON public.graph_nodes
  FOR SELECT TO authenticated USING (public.is_ops_staff());
CREATE POLICY "Graph edges select ops" ON public.graph_edges
  FOR SELECT TO authenticated USING (public.is_ops_staff());

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. feedback.redacted_at: set by the daily retention job
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE public.feedback ADD COLUMN IF NOT EXISTS redacted_at TIMESTAMPTZ;

COMMENT ON COLUMN public.feedback.redacted_at IS
  'When the retention job replaced this public row''s text (retention_until passed). Labels are kept.';
COMMENT ON COLUMN public.feedback.retention_until IS
  'Deadline for this anonymous row''s text. After it, the backend-worker redacts the text and sets redacted_at.';
