# Exec Plan

## Goal

A Customer can, if they want, sign up on the Customer web. With a Customer
account they see the history of every Feedback they filed and can talk to the
customer assistant. Without one, nothing changes: the anonymous form and the
Lookup code work as in US-077. A Customer account never gets Staff rights, and
the Staff web turns it away.

Terms follow the repo-root `CONTEXT.md` glossary: Customer, Customer account,
Staff account, Pending account, Customer web, Staff web, Lookup code, Feedback
status.

## Scope

In scope:

- Migration `supabase/migrations/20260928000000_customer_accounts.sql`: role
  CHECK on `profiles` and `mcp_tokens` gains `guest`; `handle_new_user` gives the
  first profile `admin` and every other new profile `guest`; the column DEFAULT
  stays `pending`; section 3 tightens `feedback` / `alerts` SELECT to
  `is_ops_staff()` only (the own-row half goes). No other RLS change.
- Backend router `pipeline/customer_api.py` (`/api/customer`, dependency
  `require_customer`): submit, own history, customer chat. The chat
  `submit_feedback` tool goes through the classifier path.
- Customer web (`customer-web/`): Supabase client, login, sign-up, forgot and
  reset password, `/cua-toi` history, chat widget for logged-in accounts, header
  states, the authenticated submit path, and the "Tài khoản nhân viên dùng
  Staff web" message for non-guest accounts.
- Staff web (`app/`): a Customer account screen in the account gate; the
  "Khách hàng" badge also for `source = 'customer'`; `guest` rows read-only in
  the admin user list; the dashboard employee panel lists Staff roles only.
- Docs and harness records: this story, decision 0018, `CONTEXT.md`, and the
  product docs that describe roles, sign-up and Feedback sources.

Out of scope:

- A retention policy for `source = 'customer'` rows. They carry no
  `retention_until` (decision 0018 §9); the 0017 job keeps
  `WHERE source = 'public'`. Anything beyond that is a 0018 Follow-Up.
- Moving the two existing `pending` ex-guests to `guest`. They stay `pending`.
- Captcha or Turnstile on sign-up.
- Deploying either web, and fixing the production Customer web domain.
- Applying the migration or the Auth config to any remote project. The
  orchestrator does that, after the owner approves.

## Risk Classification

Risk flags:

- Auth — self sign-up (email/password, Google, Facebook) is open again; password
  reset on the Customer web; Supabase sessions in a second frontend.
- Authorization — a new role value `guest` next to `pending`; every guard must
  keep it out of Staff routes and RLS ops rights.
- Data model — role CHECK on `profiles` and `mcp_tokens`, a replaced trigger, a
  new `feedback.source` value `customer`.
- Audit/security — a self-registered account reaches an LLM endpoint; per-user
  rate limits; the honeypot and masking must apply to the authenticated path.
- External systems — Supabase Auth sign-up, OAuth providers and redirect URLs;
  the LLM provider behind the customer assistant.
- Public contracts — three new endpoints under `/api/customer`; `/api/me` for a
  `guest`; the Customer web's CSP gains the Supabase URL.
- Cross-platform — OAuth redirects between the Customer web and Supabase.
- Existing behavior — US-077's "self sign-up lands as pending" and the Staff
  web's fail-closed `guest → pending` mapping change.
- Multi-domain — identity, intake, chat and both frontends change at once.

Hard gates: Auth, Authorization, Audit/security, External provider behavior.
Lane is high-risk.

## Work Phases

1. Discovery — the old guest code at `a69c4ee` (`GuestDashboard`, the guest chat
   tier, `chat_tools.py`, the GUEST prompt) and the US-077 guards that now meet a
   second non-Staff role.
2. Design — decisions confirmed by the owner on 2026-09-28; decision `0018`.
3. Validation planning — `validation.md` lists the cases.
4. Implementation — parallel slices: migration and backend, Customer web, Staff
   web, docs and harness records.
5. Verification — pytest (neutralised env), tsc, vitest and build for both webs,
   a local `supabase db reset`, a local E2E pass.
6. Harness update — proof flags and evidence on US-078.

## Stop Conditions

Pause for human confirmation if:

- The migration would update or delete any existing `profiles`, `auth.users` or
  `feedback` row. The two `pending` ex-guests must stay `pending`.
- Any RLS policy has to name `guest` to make a case pass, or `is_ops_staff()`
  would return true for it.
- Any Staff route answers a `guest` token with anything but 403.
- The customer chat can only file Feedback by setting its own labels.
- A Customer response would carry `topic`, `sentiment` or `severity`.
- A test has to be weakened, or the unauthenticated route guard test has to gain
  a route.
- The only way forward is a change against the production Supabase project or
  Railway.
