-- US-076 / decision 0016: anonymous public feedback intake.
--
-- Until now every feedback row required a Supabase account: user_id was NOT NULL
-- with an FK to auth.users. A xanhSM rider reporting an incident from the street
-- had to sign up first. This migration makes anonymity a first-class state of a
-- feedback row instead of an impossible one.
--
-- RLS is deliberately NOT touched. The SELECT policy from 20260612120000 is
-- `auth.uid() = user_id OR public.is_ops_staff()`; with user_id IS NULL the left
-- side evaluates to NULL, never true, so anonymous rows are ops-only by
-- construction. `anon` keeps the zero privileges decision 0014 gave it — these
-- rows are written by the backend's service-role key, never from a browser.

ALTER TABLE public.feedback ALTER COLUMN user_id DROP NOT NULL;

-- public_ref: unguessable bearer token, the only credential for reading an
-- anonymous report's status back.
ALTER TABLE public.feedback ADD COLUMN IF NOT EXISTS public_ref TEXT;

-- submitter_hash: salted sha256 of the client IP. Abuse control needs something
-- to count once there is no user.id to key on. Not an identity — one NAT is one
-- fingerprint.
ALTER TABLE public.feedback ADD COLUMN IF NOT EXISTS submitter_hash TEXT;

-- retention_until: unsolicited personal text from the open internet gets a
-- deadline. Nothing purges on it yet (follow-up in decision 0016); the column
-- records the commitment.
ALTER TABLE public.feedback ADD COLUMN IF NOT EXISTS retention_until TIMESTAMPTZ;

-- The identity invariant, in the database rather than in application code:
-- three separate writers (API, workers, dataset ingest) insert into this table
-- and only a constraint covers all of them.
ALTER TABLE public.feedback DROP CONSTRAINT IF EXISTS feedback_identity_chk;
ALTER TABLE public.feedback
  ADD CONSTRAINT feedback_identity_chk
  CHECK (user_id IS NOT NULL OR public_ref IS NOT NULL);

-- Partial indexes: existing authenticated rows carry neither column, so they
-- cost nothing.
CREATE UNIQUE INDEX IF NOT EXISTS feedback_public_ref_idx
  ON public.feedback (public_ref)
  WHERE public_ref IS NOT NULL;

CREATE INDEX IF NOT EXISTS feedback_submitter_hash_idx
  ON public.feedback (submitter_hash, created_at DESC)
  WHERE submitter_hash IS NOT NULL;

COMMENT ON COLUMN public.feedback.public_ref IS
  'Bearer token for anonymous status lookup. Possession is authorization. Never log.';
COMMENT ON COLUMN public.feedback.submitter_hash IS
  'Salted sha256 of client IP for rate limiting and abuse investigation. Not an identity.';
COMMENT ON COLUMN public.feedback.retention_until IS
  'Deadline past which this anonymous row has no reason to exist.';

-- Re-assert the lockdown from 20260827034856 now that a new write surface exists.
REVOKE ALL ON public.feedback FROM anon;
