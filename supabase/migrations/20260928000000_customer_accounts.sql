-- US-078 / decision 0018: 'guest' returns as the Customer account.
--
-- A self sign-up on the Customer web (email/password or OAuth) is a Customer
-- account, role 'guest'. It reaches only /api/customer/* on the backend and its
-- own feedback history through the backend. 'pending' stays: no access.
--
-- What this migration does NOT do, on purpose:
-- - No data change. The accounts retired to 'pending' by 20260927000000 stay
--   pending; an admin can hand one back with PATCH /api/users/{id}/role.
-- - No RLS loosening. is_ops_staff() still means admin/manager/staff, so a guest
--   is refused by every ops policy (graph_*, feedback insert). Section 3 even
--   tightens feedback/alerts SELECT: a guest reads its history only through
--   the backend, never raw rows with AI labels. Section 4 limits chat_messages
--   to ops staff, so a guest's only direct PostgREST write left is its own
--   profile row.
-- - The column default stays 'pending': a profile inserted outside the trigger
--   still fails closed.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. profiles.role and mcp_tokens.role accept 'guest'
-- ─────────────────────────────────────────────────────────────────────────────
-- Both constraints were created by name in 20260927000000, so drop by name.
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
ALTER TABLE public.profiles
  ADD CONSTRAINT profiles_role_check
  CHECK (role IN ('admin', 'manager', 'staff', 'pending', 'guest'));

-- Legacy column (role resolves live from profiles since 20260702010000); kept
-- in the same vocabulary so the two never disagree on what a role is.
ALTER TABLE public.mcp_tokens DROP CONSTRAINT IF EXISTS mcp_tokens_role_check;
ALTER TABLE public.mcp_tokens
  ADD CONSTRAINT mcp_tokens_role_check
  CHECK (role IN ('admin', 'manager', 'staff', 'pending', 'guest'));

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Sign-up trigger: first profile admin, every later one guest
-- ─────────────────────────────────────────────────────────────────────────────
-- Admin-created Staff accounts (POST /api/admin/users) also pass through here
-- as 'guest' and the backend then sets their real role in the same request; a
-- failed grant is rolled back by deleting the auth user. Such an account also
-- carries app_metadata.must_change_password, which every backend role guard
-- (require_customer included) refuses until the password is changed.
--
-- Ordering hazard on a FRESH project: sign-up is open (decision 0018), so the
-- first profile ever, whoever creates it, becomes admin. Create the first admin
-- (Dashboard → Authentication → Add user) before the Customer web or the
-- publishable key is reachable by anyone else.
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
    assigned_role := 'guest';
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
-- 3. feedback / alerts: browser SELECT for ops staff only
-- ─────────────────────────────────────────────────────────────────────────────
-- "auth.uid() = user_id OR is_ops_staff()" let a Customer account read its own
-- rows straight from PostgREST with every column, AI labels included, which
-- decision 0017 keeps from Customers. The Customer web reads history through
-- GET /api/customer/feedback (allowlisted fields) instead, so the own-row half
-- goes. Alerts carry no customer ownership at all.
DROP POLICY IF EXISTS "Feedback select" ON public.feedback;
CREATE POLICY "Feedback select" ON public.feedback
  FOR SELECT TO authenticated
  USING (public.is_ops_staff());

DROP POLICY IF EXISTS "Alerts select" ON public.alerts;
CREATE POLICY "Alerts select" ON public.alerts
  FOR SELECT TO authenticated
  USING (public.is_ops_staff());

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. chat_messages: Staff web chat history only
-- ─────────────────────────────────────────────────────────────────────────────
-- "Users manage own chat" let any authenticated account write unbounded rows
-- straight through PostgREST. With open sign-up that is a free, rate-limit-free
-- disk sink for any self-registered account. Only the Staff web chat page uses
-- this table; the Customer web keeps its chat in memory. A Customer account's
-- only write path stays the backend (decision 0018).
DROP POLICY IF EXISTS "Users manage own chat" ON public.chat_messages;
CREATE POLICY "Users manage own chat" ON public.chat_messages
  FOR ALL TO authenticated
  USING (auth.uid() = user_id AND public.is_ops_staff())
  WITH CHECK (auth.uid() = user_id AND public.is_ops_staff());
