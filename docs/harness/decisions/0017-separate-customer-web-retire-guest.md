# 0017 Separate Customer web, retire the guest role

Date: 2026-09-27

## Status

Accepted. Supersedes part of decision 0016: the placement of the public intake
routes inside the Staff web (`/f`, `/f/status/$code`), the `topic` and
`severity` fields in the status response, and the status value `resolved`. The
rest of 0016 stands: nullable `user_id` with the identity CHECK, `public_ref` as
the only read credential, the salted IP-hash rate limit, and server-side
classification. 0016's first follow-up, a retention job, is decided here as
redaction rather than deletion.

All points below were confirmed by the owner in a grilling session on 2026-09-27.
Story: `docs/harness/stories/epics/E04-public-intake/US-077-separate-customer-web/`.

## Context

Decision 0016 opened an unauthenticated intake, but placed it inside the one
TanStack Start app that also serves the staff cockpit. Four problems came out of
that, and out of the `guest` role that predates it.

**The customer surface cannot be reached, and it fails silently.** Nothing links
to `/f`. Every landing CTA goes to `/auth`, and the chat widget's canned replies
tell visitors to log in (`app/src/routes/index.tsx:156-653`,
`app/src/components/SupportChatWidget.tsx:60-87`). No `<Toaster/>` is mounted
anywhere, so a Customer who hits the 429 limit or a validation error on `/f`
sees nothing (`app/src/components/ui/sonner.tsx` is never imported;
`app/src/routes/f.tsx:57, 69`). The anonymous pages also ship the Supabase client,
because `publicFetch` lives in `app/src/lib/api.ts`, which imports it at module
top level (`api.ts:5-6`).

**`guest` means three things.** It is the customer account. It is the role every
self sign-up gets (`supabase/migrations/20260616000000_default_role_guest.sql:14-17`),
and so the admin's queue of employees waiting for approval
(`app/src/routes/_authenticated/admin.tsx:132`, `pipeline/users_admin.py:161-186`).
And it is the fail-closed fallback for a missing or unknown role
(`pipeline/auth_guard.py:57-60`). A customer who signs up lands in the approval
queue and can be promoted to staff by mistake.

**Self sign-up keeps doors open that no customer needs.** `/auth` offers
email/password sign-up plus Google and Facebook OAuth (`app/src/routes/auth.tsx:83-90, 304-336`).
Any account it creates can:

- `INSERT` into `feedback` through PostgREST with its own topic and severity,
  because the only check is `auth.uid() = user_id`
  (`supabase/migrations/20260612120000_rbac_roles.sql:85-87`);
- reach the MCP `submit_feedback` tool, which skips the classifier
  (`pipeline/mcp_server.py:78-81`, `pipeline/agent/chat_tools.py:113-123`).

The `profiles.role` column default is still `staff`
(`20260612120000_rbac_roles.sql:15`). A profile inserted outside the trigger would
get ops rights.

**The public status says more than it should, and retention is not enforced.**
The status lookup returns `topic` and `severity`
(`pipeline/public_intake.py:228-229`). It labels a reviewed row `resolved`, which
reads as "the incident was handled", but it only means an operator checked the AI
label (`public_intake.py:105-115`; `pipeline/main.py:1774, 1804`). Nothing reads
`retention_until`. Expired rows keep their text and still answer the lookup with
200.

The backend needs no CORS change for a second origin: CORS is
`allow_origins=["*"]` with `allow_credentials=True` (`pipeline/main.py:263-268`).
It does need the browser to call it directly. The rate limiter keys on the
rightmost `X-Forwarded-For` hop (`public_intake.py:78-92`), so a server-side proxy
would put every Customer into one bucket.

## Decision

Split the two audiences into two deployables, and give the Staff web one
meaning per role.

1. **A separate Customer web.** A new static SPA at `customer-web/` (Vite +
   React, same majors as `app/`). It has two pages: `/` is the Feedback form plus
   a "Tra cứu mã" box, and `/status/:code` is the Feedback status. It is
   Vietnamese only and mobile-first, with the Staff web's brand tokens but not its
   cockpit look. It has no Supabase client, no login and no staff code. The code
   it needs from `app/` is copied, not imported. It is its own Railway service,
   built from its own Dockerfile, and it listens on `$PORT`.
2. **Browser-direct calls to the existing public API.** `VITE_BACKEND_API_URL`
   is baked in at build time. There is no BFF.
3. **A narrower public contract.**
   - `POST /api/public/feedback` takes an optional honeypot field `website`. A
     non-empty value returns 400, stores nothing, and still counts against the
     rate limit.
   - `GET /api/public/feedback/{public_ref}` returns exactly `public_ref`,
     `status` and `created_at`.
   - `resolved` is renamed `reviewed`. The values are `received`,
     `under_review` and `reviewed`.
   - An expired or redacted row returns the same 404 as an unknown one.
4. **Retention by redaction.** `redact_expired_public_feedback` runs daily at
   03:00 Asia/Ho_Chi_Minh in `backend-worker`. For public rows past
   `retention_until` it replaces the text with "[Đã xoá theo hạn lưu trữ]",
   clears `submitter_hash`, and sets the new column `redacted_at`. Labels, area,
   channel, dates and `overall_risk` are kept, so dashboards and trends do not
   change. The job (`pipeline/services/retention.py`) also clears
   `correction_logs.note`, the one copy linked to the row by `feedback_id`.
   Copies that are not linked by id are not redacted; see Tradeoffs.
5. **Retire `guest` for `pending`.** `pending` is an account with no access
   until an admin grants admin, manager or staff.
   - `VALID_ROLES = {admin, manager, staff, pending}`, and every fail-closed
     fallback uses `pending`.
   - One migration rewrites existing `guest` profiles to `pending` without
     deleting any account or row. It also replaces the role CHECK, sets the
     column default to `pending`, and makes the trigger assign `pending` (the
     first profile ever still becomes `admin`).
   - The same migration cuts authenticated `INSERT` on `feedback` to
     `is_ops_staff() AND auth.uid() = user_id`. It drops the
     "Users insert own profile" policy and revokes `INSERT`, `DELETE` and
     `TRUNCATE` on `profiles` from `authenticated`, so profiles come only from
     the trigger and change only through the backend. It replaces the
     `graph_nodes` / `graph_edges` read policies (`USING (true)`) with
     "Graph nodes select ops" / "Graph edges select ops" `USING (is_ops_staff())`,
     so the internal knowledge base is no longer readable by any signed-in
     account.
   - The backend answers a Pending account with 403 everywhere except
     `GET /api/me`, `POST /api/me/password` and `/health`.
   - MCP over HTTP rejects a pending or unknown identity with 401, whether it
     comes as a Supabase JWT or an `mcp_tokens` bearer: no session and no tool
     list (`SupabaseTokenVerifier` in `pipeline/mcp_auth.py`). The stdio server
     gives `MCP_ROLE=pending` (the default) no tools.
6. **Only an admin creates accounts.** `POST /api/admin/users` creates the
   account through the service-role `auth.admin.create_user` with
   `email_confirm=True` and a temporary password. The password must meet the same
   5 criteria the old sign-up form checked. `/auth` becomes login-only.
   The account carries `app_metadata.must_change_password = true`. Only the
   service role can write `app_metadata`, so the user cannot clear the flag with
   `supabase.auth.updateUser`. The flag is enforced on the server:
   - `auth_guard.require_ops_staff`, `require_admin` and `require_manager` return
     403 "Bạn cần đổi mật khẩu tạm trước khi tiếp tục" while it is set.
     `GET /api/me` (which returns `must_change_password`) and
     `POST /api/me/password` are the only routes that need nothing but a valid
     session.
   - `POST /api/me/password` takes `{new_password}`, checks the same 5 criteria,
     and calls `auth.admin.update_user_by_id` with the new password and
     `app_metadata {must_change_password: false}`. Its 400 and 503 responses
     never echo the password.
   - MCP over HTTP rejects a Supabase JWT that carries the flag with 401.
   - `public.password_is_current()` reads `auth.jwt() -> app_metadata`, and
     `is_ops_staff()` and `is_admin()` now require it, so PostgREST and realtime
     are closed to a flagged account too.

   The Staff web reads the flag from `app_metadata` and shows only the
   change-password screen. That screen calls `POST /api/me/password`, then
   `supabase.auth.refreshSession()` so the new JWT no longer carries the flag.
7. **The Staff web drops its customer surface.** `/f`, `/f/status/$code` and
   `GuestDashboard` are deleted. The landing keeps its poster page, points every
   CTA to login, and adds a "Gửi phản hồi" link to the Customer web
   (`VITE_CUSTOMER_WEB_URL`). Public rows get a "Khách hàng" badge.
   `<Toaster/>` is mounted once.
8. **The Supabase Dashboard is a manual step.** Turning off sign-up and the
   Google and Facebook providers happens outside the repo. It is documented for
   the owner in `docs/project/setup-supabase.md`. No code does it or asserts it.

## Alternatives Considered

1. **Keep `/f` in the Staff web** (0016's placement), and fix only the Toaster
   and the links. Rejected. The anonymous pages would still ship the Supabase
   client and the staff route definitions, and would share the Staff web's root
   shell, its meta and its deploy. Every staff change would redeploy the page
   printed on QR codes in vehicles.
2. **Route by Host inside the one Nitro server** (`app/src/server.ts`). Rejected.
   It still ships one bundle and one route tree to both audiences. It ties the
   customer URL to the Staff web's deploy. And it adds routing logic to an SSR
   error wrapper.
3. **A second build from `app/`** with another `srcDirectory` or routes
   directory. Rejected. It keeps one `package.json`, one lockfile and one Lovable
   template for two products. `app/src/lib/api.ts` would still pull the Supabase
   client into the customer build.
4. **A BFF or proxy in front of the public API.** Rejected. The limiter keys on
   the rightmost `X-Forwarded-For` hop, so every Customer would share the
   proxy's bucket of 5 per hour.
5. **Keep `guest` as the customer account next to the Customer web.**
   Rejected. It leaves self sign-up, the approval-queue mix-up, the PostgREST
   `INSERT` path and the MCP path open, all for a login a Customer no longer
   needs.
6. **Delete accounts instead of renaming the role.** Rejected. Every FK to
   `auth.users` is `ON DELETE CASCADE`, so deleting an account deletes its
   feedback, alerts, chat history and MCP tokens.
7. **Hard-delete rows past retention.** Rejected. It changes dashboards,
   trends and alert history retroactively. The personal data is the text and
   the fingerprint, and redaction removes exactly those.

## Consequences

Positive:

- The Customer surface is small, static, and has no Supabase dependency. It can
  be served from any static host and is safe to print on a QR code.
- Each role means one thing. A Pending account cannot be mistaken for a customer,
  and a customer never enters the approval queue.
- The PostgREST `INSERT` bypass and the self-registered MCP path both close.
- Retention stops being a promise on a column and becomes a daily job.
  Redaction keeps analytics stable.
- A Customer never sees internal labels. The "reviewed" wording no longer claims
  the incident was fixed.

Tradeoffs:

- There are two frontends to build, test and deploy. The brand tokens and the
  region list are copied, so they can drift from `app/`.
- A logged-in guest had an LLM assistant. Customers now get none.
- Accounts are created by hand. There is no invitation email, and the admin has
  to hand over a temporary password out of band.
- Until the owner turns the Dashboard toggles off, the Supabase Auth API still
  accepts a direct sign-up. The account lands as `pending` with no access, but it
  still exists.
- Redaction is only as complete as the list of text copies. The job clears
  `correction_logs.note`, the one copy linked to the row by `feedback_id`. These
  copies carry public text but no link to the row, so the job leaves them
  unredacted:
  - `alerts.title` and `alerts.description`. With no LLM key,
    `llm_agent.mock_spike_response` quotes up to 3 samples of 120 characters
    each into the description; with an LLM, the text is the model's summary of
    the samples.
  - P5 alert webhook payloads (`pipeline/webhook_notifier.py`, called from
    `pipeline/spike_detector.py:268`). They go to `WEBHOOK_URL`, or to stdout
    (the container log) when it is unset. A sent webhook cannot be recalled.
  - `tasks.title` and `tasks.summary`. When a ticket moves to `in_progress`,
    `pipeline/main.py` calls `create_ticket_task` with the alert title and
    `alert.description[:300]`.
  - `department_reports.content` (Markdown) and `root_cause_summary`: LLM
    output derived from feedback samples.
  - `chat_messages`, when the assistant quotes alert text into a reply.
  - External LLM providers, which receive the samples in prompts.
  - `model_router`'s `prompt_preview` (the first 160 characters of the first
    user message, after `sanitize_pii_payload`) in `pipeline/logs/agent.log`
    (`pipeline/agent/model_router.py:358, 380`), which lives on the container's
    filesystem when deployed.
  - Supabase backups and point-in-time recovery (PITR), which keep the text as
    it was until they expire.
- `delete_user` still cascades (see Follow-Up). Rejecting a pending account from
  the admin page deletes whatever that former guest had filed.

## Follow-Up

Each item has a row in `harness.db` (`scripts/bin/harness-cli query backlog`):

- `delete_user` cascades into the user's feedback, alerts, chat and MCP tokens.
- Captcha or Turnstile on the Customer web, if the IP limiter plus honeypot
  proves insufficient.
- Deploy `customer-web` once production serves again (backlog #7). Fix the
  Customer web domain before any QR code is printed.
- CI jobs for `customer-web/` and `app/`. CI runs Python checks only today.
