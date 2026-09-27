# Overview

## Current Behavior

One TanStack Start app (`app/`), built from one Dockerfile into one Railway
service, serves three audiences:

1. Anonymous visitors: the marketing landing `/`, `/auth`, and the US-076 intake
   routes `/f` and `/f/status/$code` (`app/src/routes/f.tsx`,
   `app/src/routes/f_.status.$code.tsx`).
2. Logged-in `guest` accounts, which reach only `/dashboard` and see
   `GuestDashboard` (`app/src/routes/_authenticated/dashboard.tsx:34-35`).
3. Staff accounts (admin, manager, staff), which reach the `_authenticated`
   cockpit.

`/auth` has open self sign-up: email/password plus Google and Facebook OAuth
(`app/src/routes/auth.tsx:73-99, 304-336`). The `handle_new_user` trigger gives
every new account the role `guest`, except that the first profile ever becomes
`admin` (`supabase/migrations/20260616000000_default_role_guest.sql:14-17`).

`guest` does three jobs at once:

- the customer account;
- the queue of employees waiting for approval
  (`app/src/routes/_authenticated/admin.tsx:132`, `pipeline/users_admin.py:161-186`);
- the fail-closed fallback for a missing or unknown role
  (`pipeline/auth_guard.py:57-60`, `app/src/routes/_authenticated/route.tsx:25-36`).

A customer who signs up lands in the admin's approval queue and can be promoted
to staff by mistake.

Nothing links to `/f`. Every landing CTA goes to `/auth`, and the chat widget's
canned replies tell visitors to log in (`app/src/routes/index.tsx:156-653`,
`app/src/components/SupportChatWidget.tsx:60-87`). No `<Toaster/>` is mounted
anywhere, so on `/f` the empty-text validation, the 429 message and every other
error are invisible (`app/src/components/ui/sonner.tsx` is never imported).

The status lookup returns `topic` and `severity` and calls a reviewed label
`resolved`, which reads as "the incident was handled". It only means an operator
reviewed the AI label (`pipeline/public_intake.py:105-115, 228-229`).

`retention_until` is written on every anonymous row, but nothing reads it. Expired
rows keep their text and still answer the status lookup with 200.

Any signed-in account can `INSERT` into `feedback` through PostgREST with its own
topic and severity. The only check is `auth.uid() = user_id`
(`supabase/migrations/20260612120000_rbac_roles.sql:85-87`).

## Target Behavior

A Customer scans a QR code or follows the landing's "Gửi phản hồi" link and lands
on the Customer web. It is a separate static site. It runs no Supabase client,
has no login and ships no staff code. One form (text, channel, area) returns a
Lookup code with a copy button and a link to `/status/<code>`. That page shows
the Feedback status ("Đã tiếp nhận", "Đang xem xét" or "Đã xem xét") and the
submitted date. It shows nothing else, and never an AI label. Every validation,
rate-limit and network error is visible.

The Staff web is for Staff accounts only. `/auth` is login-only. An admin creates
each account with a temporary password, and the account must change it on first
login; the backend, MCP and RLS refuse it until it does. An account with the role
`pending` sees one screen: "Tài khoản đang chờ admin cấp quyền", with a logout
button. The backend answers it with 403 on every route except `GET /api/me`,
`POST /api/me/password` and `/health`. Existing `guest` accounts become
`pending` and keep their feedback. Public rows carry a "Khách hàng" badge in the
feedback list.

Every day at 03:00 Asia/Ho_Chi_Minh, `backend-worker` redacts public rows past
`retention_until`. The text becomes "[Đã xoá theo hạn lưu trữ]" and the submitter
hash is cleared. Labels, area, channel, dates and risk are kept, so dashboards and
trends do not move. Expired or redacted Lookup codes answer 404 like unknown ones.

## Affected Users

- Customer — new term for the person outside the company. Uses the Customer web,
  holds a Lookup code, has no account.
- Pending account — new role. Former guests, and any account created outside the
  admin form (for example from the Supabase Dashboard), until an admin grants a
  Staff role.
- Staff / Manager — lose nothing. They see the "Khách hàng" badge on public rows.
  Their `POST /api/feedback/submit` keeps working.
- Admin — creates accounts; approves pending accounts from the "Chờ cấp quyền"
  list; must switch off Supabase sign-up and OAuth in the Dashboard by hand.
- MCP clients — over HTTP, a JWT or bearer token whose role is `pending` or
  unknown, or a JWT still flagged `must_change_password`, gets 401 and no tool
  list. Over stdio, `MCP_ROLE` unset or `pending` gets no tools.

## Affected Product Docs

- `docs/project/guest-account.md` — rewritten: Customer, Pending account, and how
  accounts are created.
- `docs/project/rbac-departments.md` — the role table, gates, bootstrap, chat
  tiers and frontend guard.
- `docs/project/co_che.md`, `docs/project/giai_thich.md` — roles, screens,
  services, bootstrap.
- `docs/project/data-model.md` — `profiles.role`, the `feedback` columns (US-076
  and `redacted_at`), the RLS summary and the enums.
- `docs/project/architecture.md` — tiers, services, RBAC.
- `docs/project/deploy-railway.md` — the `customer-web` service, and a fix to the
  CORS claim (CORS is `*` today, there is no allowlist).
- `docs/project/setup-supabase.md` — the manual Dashboard step and first-admin
  bootstrap without a sign-up form.
- `README.md` — features, run commands, RBAC table, doc index.

## Non-Goals

- A chatbot on the Customer web. That needs a new unauthenticated LLM endpoint,
  which brings provider cost and a prompt-injection surface.
- Notifying the Customer. The status page is pull-only.
- Deleting rows past `retention_until`. The text is redacted and the row stays.
- Letting a Customer upgrade to an account.
- Deploying either web. The service and the env vars are documented; nothing is
  pushed.
- Changing CORS. It stays `*`.
