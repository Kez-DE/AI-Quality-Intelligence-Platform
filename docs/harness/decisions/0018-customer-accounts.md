# 0018 Optional Customer accounts on the Customer web

Date: 2026-09-28

## Status

Accepted. Amends decision 0017 in three places:

- 0017 §5 retired the role `guest`. It returns, with one meaning: the
  **Customer account**, used only on the Customer web.
- 0017 §5 made every self sign-up land as `pending`. Self sign-up now lands as
  `guest`.
- 0017 §8 asked the owner to turn off sign-up and the Google and Facebook
  providers in the Supabase Dashboard. They stay on, because the Customer web
  needs them.

The rest of 0017 stands. `pending` keeps its meaning: an account with no access
until an admin grants a Staff role, and the fail-closed value for a missing or
unknown role. Only an admin creates Staff accounts. Anonymous intake through
`/api/public/*` is unchanged, and a Customer can still use the Customer web
without an account.

All points below were confirmed by the owner on 2026-09-28, except two settled
by the orchestrator in review the same day: the `feedback` / `alerts` SELECT
tightening in §4 and the "no retention deadline" rule in §9.
Story: `docs/harness/stories/epics/E04-public-intake/US-078-customer-accounts/`.

## Context

0017 removed the logged-in customer to close four doors: the approval-queue
mix-up, the PostgREST `INSERT` path into `feedback`, the MCP `submit_feedback`
path that skipped the classifier, and the internal knowledge base readable by any
signed-in account. It also accepted a tradeoff: "A logged-in guest had an LLM
assistant. Customers now get none."

The owner wants two things back for Customers who choose to sign up: a history of
their own Feedback without keeping every Lookup code, and the customer assistant.
Both need an identity. Neither needs any of the four doors 0017 closed.

Facts that shape the design:

- The Staff web gate and the backend already fail closed to `pending`. 0017 left
  no route open to a non-Staff role except `GET /api/me`,
  `POST /api/me/password` and `/health`.
- `is_ops_staff()` returns true only for `admin`, `manager` and `staff`
  (`supabase/migrations/20260927000000_retire_guest_role.sql`). A new role gets no
  ops rights in RLS unless a policy names it.
- Before this decision, the own-row `SELECT` policies on `feedback` and `alerts`
  (`auth.uid() = user_id OR is_ops_staff()`) let any account read its own rows
  straight from PostgREST, every column included, AI labels too.
- The old guest chat tier (`git show a69c4ee:pipeline/main.py`) answered from the
  public knowledge base only. Its `submit_feedback` tool set its own labels and a
  fixed severity P3 instead of running the classifier.
- Two production profiles are `pending` today. Both were `guest` before 0017.

## Decision

1. **`guest` is the Customer account.** The role CHECK on `profiles` (and on the
   legacy `mcp_tokens.role`) becomes `admin, manager, staff, pending, guest`. A
   Customer account can log in to the Customer web only. It holds no Staff
   rights anywhere.
2. **Self sign-up lands as `guest`.** `handle_new_user` gives the first profile
   ever `admin` and every other new profile `guest`. The column DEFAULT stays
   `pending`, so a profile inserted outside the trigger still gets no access.
   Admin-created Staff accounts are unchanged: `POST /api/admin/users` sets the
   real role right after the trigger. Migration:
   `supabase/migrations/20260928000000_customer_accounts.sql`.
3. **`pending` stays, and nothing moves.** The two existing `pending` profiles
   stay `pending`. No row is updated or deleted. Sign-up never lands in the
   admin's approval queue again, because the queue lists `pending` only.
4. **No RLS loosening; `feedback` and `alerts` SELECT is tightened.**
   `is_ops_staff()` still excludes `guest`. The `graph_*` policies stay
   ops-only. `feedback` `INSERT` stays ops-only. Migration section 3 recreates
   "Feedback select" and "Alerts select" as `USING (is_ops_staff())`: the
   own-row half is dropped. A Customer account, and also a `pending` account or
   one still on its temporary password, reads no `feedback` or `alerts` row
   through PostgREST, not even its own. A Customer account reads its history
   only through `GET /api/customer/feedback` (allowlisted fields, §5) and
   writes only through the backend.
5. **A separate backend surface: `/api/customer`.** A new router
   (`pipeline/customer_api.py`) behind `require_customer` (role `guest`; every
   other role gets 403):
   - `POST /api/customer/feedback` `{text, channel, area, website}`: the same
     pipeline as public intake (clean and mask, classifier, rules, severity,
     honeypot, length cap), with `user_id` set to the Customer account and
     `source = 'customer'`. The row still gets a `public_ref`. Rate limited per
     user id. Returns `{public_ref, status, created_at}`.
   - `GET /api/customer/feedback`: the account's own rows, newest first, as
     `{public_ref, status, created_at, text}`. `status` is derived as on the
     public route (`received | under_review | reviewed`). Never `topic`,
     `sentiment` or `severity`.
   - `POST /api/customer/chat` `{messages}`: the customer assistant. It is the
     old guest tier (public knowledge base only, the public system prompt), rate
     limited per user. Its `submit_feedback` tool goes through the same
     classifier path as `POST /api/customer/feedback`. The old tool's
     self-assigned labels and fixed P3 are gone.
   - Staff routes keep `require_ops_staff`, `require_admin` and
     `require_manager`, so a Customer account gets 403 there. `GET /api/me`
     answers it. The pending-role route sweep also runs with a `guest` token.
6. **The Customer web gains optional login.** It uses `@supabase/supabase-js`
   with the publishable key (build-time `VITE_SUPABASE_URL`,
   `VITE_SUPABASE_PUBLISHABLE_KEY`). New pages: `/dang-nhap`, `/dang-ky`,
   `/quen-mat-khau`, `/dat-lai-mat-khau`, `/cua-toi` (history), and a chat widget
   for logged-in Customer accounts. When logged in as `guest`, the form posts to
   `/api/customer/feedback`. Logged out, it posts to the public route as before.
   An account whose role is not `guest` (Staff or pending, read via `/api/me`)
   sees "Tài khoản nhân viên dùng Staff web" and makes no customer API call.
7. **The Staff web turns Customer accounts away.** Role `guest` sees one
   screen, "Đây là tài khoản khách hàng", with a link to `VITE_CUSTOMER_WEB_URL`
   and a logout button: no nav, no data fetch. Rows with `source = 'customer'`
   carry the same "Khách hàng" badge as `source = 'public'`. In the admin user
   list a Customer account row is read-only: its role and department cannot be
   changed there (it can still be deleted). The dashboard's employee panel lists
   Staff roles only. A Staff account is created with `POST /api/admin/users`,
   never by promoting a Customer account.
8. **Supabase Auth config.** Sign-up, the Email provider, Google and Facebook
   stay on. The Customer web origins are added to the redirect allow list
   (`http://localhost:5175/**` locally, plus the production Customer web domain
   once it exists). Email confirmation is the owner's choice. The orchestrator
   applies the remote change; no code asserts it.
9. **Customer rows have no retention deadline.** `source = 'customer'` rows are
   stored with `retention_until = NULL`. The 180-day redaction job (`WHERE
   source = 'public'`) and the status-lookup expiry do not apply: the row's
   Lookup code resolves on `GET /api/public/feedback/{public_ref}` with no time
   limit, and the text lives until the account is deleted (cascade).

## Alternatives Considered

1. **Keep 0017 as is: no Customer accounts.** Rejected by the owner. Customers
   lose history and the assistant, and must keep every Lookup code.
2. **Reuse `pending` as the Customer account.** Rejected. It brings back the
   exact ambiguity 0017 removed: a Customer in the approval queue, one click from
   a Staff role.
3. **A new role name (`customer`) instead of `guest`.** Not chosen: the owner
   decided that `guest` returns. The old guest code in `a69c4ee` is the
   reference for the assistant, and the glossary term "Customer account" carries
   the meaning in docs. `source = 'customer'` names the Feedback, not the role.
4. **Let the Customer web write `feedback` directly through PostgREST with the
   user's JWT.** Rejected. It reopens the self-labelled `INSERT` path 0017
   closed and skips the classifier, the honeypot and the rate limit.
5. **Keep the chat tool's own labelling.** Rejected. It was the bug that let
   chat-filed rows carry a fixed P3 whatever the text said.
6. **Rewrite the two pending ex-guests to `guest`.** Rejected. It is a data
   change on production for two rows whose owners may be staff candidates. An
   admin can grant a role by hand.

## Consequences

Positive:

- A Customer can choose: stay anonymous with a Lookup code, or sign up and see
  the history of every Feedback they filed.
- The customer assistant is back, and chat-filed Feedback now goes through the
  classifier like every other intake.
- Every role still means one thing. `guest` is a Customer account, `pending` is
  "waiting for Staff access", and neither has Staff rights.
- No RLS policy is loosened. The Customer account's only write path is the
  backend, and its only read path for Feedback is the backend too.

Tradeoffs:

- Self sign-up is open again, on purpose. Anyone can create a Customer account.
  It gets the Customer web and nothing else, but rate limits per user id are the
  only brake on a script that signs up many accounts.
- The Customer web now ships the Supabase client and a session. 0017 kept it
  Supabase-free; its CSP `connect-src` now includes the Supabase URL.
- An LLM endpoint is reachable by any self-registered account. Provider cost
  and prompt injection are bounded by the per-user rate limit and the public
  knowledge base, not by who the caller is.
- Customer rows carry `user_id`, so `delete_user` (still cascading, backlog)
  deletes a Customer's history along with the account.
- Customer rows have a `public_ref` but are not anonymous. They carry no
  retention deadline (§9), so their text is kept, and their Lookup code keeps
  resolving, for as long as the account exists.
- `feedback` and `alerts` SELECT is ops-only (§4). A `pending` or
  password-flagged account also loses the own-row read it had before. No
  frontend depended on it: the Staff web reads Feedback through the backend.
- `profiles.role` now has two no-Staff values. Every role switch in code must
  handle `guest` explicitly, or it falls to `pending`, which still fails closed.

## Follow-Up

- Retention policy for `source = 'customer'` rows beyond §9: keep while the
  account exists (current), redact after a period, or delete with the account.
- Captcha or Turnstile on `/dang-ky`, if sign-up abuse appears.
- Fix the Customer web production domain and add it to the Supabase redirect
  allow list before the deploy.
- Whether an admin may ever change a `guest` to a Staff role through
  `PATCH /api/users/{id}/role`. Until that is decided, the Staff web does not
  offer it (§7) and a Staff account is created with `POST /api/admin/users`.
  The backend rule for that route lives in `pipeline/users_admin.py`.
