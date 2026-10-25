# Exec Plan

## Goal

A Customer submits Feedback and checks its Feedback status on a separate
Customer web, from a phone, with no account. The Staff web becomes staff-only:
no self sign-up, no `guest` role, and only an admin creates accounts. Anonymous
free text is actually redacted once `retention_until` passes, instead of only
being stamped with a date.

Terms follow the repo-root `CONTEXT.md` glossary: Customer, Staff account,
Pending account, Customer web, Staff web, Lookup code, Feedback status.

## Scope

In scope:

- New deployable `customer-web/` (Vite + React static SPA): submit form at `/`
  with a Lookup code box, and `/status/:code`. Browser calls the backend
  directly. No Supabase client, no staff code.
- Public API contract changes in `pipeline/public_intake.py`: a honeypot field
  `website`, a status response cut to `{public_ref, status, created_at}`, the
  status value `resolved` renamed `reviewed`, and 404 for expired or redacted
  rows.
- Daily retention job `redact_expired_public_feedback` in `backend-worker`
  (03:00 Asia/Ho_Chi_Minh), plus redaction of the free-text copies it can reach
  safely.
- Retire the `guest` role for a new `pending` role: one migration (role rewrite,
  CHECK, column default, `handle_new_user`, RLS and functions, ops-only
  authenticated `INSERT` on `feedback`, `feedback.redacted_at`), the backend
  (403 for pending everywhere except `GET /api/me`, `POST /api/me/password` and
  `/health`, MCP, chat),
  and the Staff web (guard, nav, pending screen).
- Admin account creation `POST /api/admin/users` with a temporary password and a
  forced password change on first login.
- Staff web clean-up: delete `/f`, `/f/status/$code`, `GuestDashboard`; login-only
  `/auth`; landing CTAs point to login plus a "Gửi phản hồi" link to the Customer
  web; a "Khách hàng" badge on public rows; mount `<Toaster/>` once.
- Docs and harness records: this story, decision 0017, backlog rows, and the
  product docs that describe the guest role or `/f`.

Out of scope (each has a backlog row):

- `delete_user` cascading into the user's feedback, alerts and chat history.
- Captcha / Turnstile on the Customer web.
- Deploying `customer-web` to Railway. Production does not serve today
  (backlog #7); the service is documented, not created.
- CI jobs for `customer-web/` and `app/`.

Also out of scope:

- Turning the Supabase Dashboard sign-up and OAuth toggles off. No code in this
  repo can do it; it is a documented manual step for the owner
  (`docs/project/setup-supabase.md` §8.1).
- A chatbot, notifications, or any login on the Customer web.
- Applying the migration to any remote database.

## Risk Classification

Risk flags:

- Auth — self sign-up and OAuth removed from the UI; admin-created accounts with a
  temporary password; forced password change on first login.
- Authorization — `guest` becomes `pending` with no access; every fail-closed
  fallback moves to `pending`; authenticated direct `INSERT` on `feedback` is cut
  to ops staff; the MCP guest tool tier is removed.
- Data model — rewrite of `profiles.role` values, a new CHECK, a new column
  default, a replaced trigger, new column `feedback.redacted_at`.
- Audit/security — retention redaction destroys text for good; account creation
  must be audited and must never log or return the password; honeypot on an
  unauthenticated route.
- External systems — Supabase Auth admin API (`auth.admin.create_user`); the
  Supabase Dashboard sign-up and provider toggles.
- Public contracts — status response shape, status value rename, honeypot 400,
  new admin endpoint, `POST /api/feedback/submit` becomes ops-only.
- Cross-platform — a second, mobile-first deployable with its own build-time env.
- Existing behavior — US-076's `/f` routes leave the Staff web; existing guest
  accounts change role.
- Multi-domain — intake, identity, retention and two frontends change at once.

Hard gates: Auth, Authorization, Data migration, Audit/security, External
provider behavior. Lane is high-risk.

## Work Phases

1. Discovery — map every surface that depends on `guest`, every copy of public
   free text, and the current `/f` import tree (done; evidence is in the
   workstream codebase maps and in decision 0017's Context).
2. Design — settle each decision with the owner (done in a grilling session on
   2026-09-27); record decision `0017`.
3. Validation planning — `validation.md` lists the cases before code is written.
4. Implementation — four parallel slices: Customer web, backend + migration,
   Staff web, docs + harness records.
5. Verification — pytest, tsc, vite build, vitest for both webs, a local
   `supabase db reset` run of the migration, and a local E2E pass.
6. Harness update — proof flags and evidence on US-077; reconcile file names the
   docs describe ahead of the code.

## Stop Conditions

Pause for human confirmation if:

- The migration would delete any `profiles`, `auth.users` or `feedback` row.
  Existing guest accounts keep their accounts and their feedback; every FK to
  `auth.users` is `ON DELETE CASCADE`.
- The retention job would touch a row whose `source` is not `public`, or a row
  whose `retention_until` is in the future.
- A free-text copy of a public row cannot be redacted without changing a shared
  contract. Record it as a known limitation; do not force it.
- Any endpoint other than `GET /api/me`, `POST /api/me/password` and `/health`
  answers a Pending account
  with anything but 403.
- A test has to be weakened, or the unauthenticated route guard test has to gain
  a route, to make the change pass.
- The only way forward is a change against the production Supabase project or
  Railway.
