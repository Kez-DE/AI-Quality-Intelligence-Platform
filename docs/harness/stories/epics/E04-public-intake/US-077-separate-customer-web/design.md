# Design

## Domain Model

Vocabulary is fixed in the repo-root `CONTEXT.md`. This story changes what three
of its words point at in code:

- **Customer** — a person outside the company. Has no account. Writes only
  through `POST /api/public/feedback` and reads only through a Lookup code. In the
  code a Customer's row is `source='public'`, `user_id IS NULL`. The old
  logged-in `guest` "customer account" no longer exists.
- **Pending account** — `profiles.role = 'pending'`. It exists in Supabase Auth
  and can log in, but it holds no access until an admin grants `admin`,
  `manager` or `staff`. It is also the fail-closed value wherever a role is
  missing or unknown.
- **Staff account** — `admin`, `manager` or `staff`. Only an admin creates one.

Invariants this story adds:

> A Pending account can reach nothing but its own identity (`GET /api/me`), its
> own password (`POST /api/me/password`) and `/health`.

> An account still on its temporary password (`app_metadata.must_change_password`)
> can reach nothing behind a role guard, over PostgREST, realtime or MCP until it
> changes the password through `POST /api/me/password`.

> A Customer never sees an AI label. The Feedback status is one of `received`,
> `under_review`, `reviewed`. `reviewed` means an operator checked the AI
> classification, not that the problem is fixed.

> After `retention_until`, a public row keeps its labels and loses its words.
> The text becomes "[Đã xoá theo hạn lưu trữ]", `submitter_hash` becomes NULL,
> `redacted_at` is set. `topic`, `sentiment`, `severity`, `area`, `channel`,
> `created_at` and `overall_risk` are untouched.

`VALID_ROLES = {admin, manager, staff, pending}`. `OPS_ROLES` is unchanged:
`{admin, manager, staff}`.

## Application Flow

Submit (Customer web → `POST /api/public/feedback`):

```
browser (Customer web, no token)
  -> pydantic validation                 text 1..4000, channel <=40, area <=80;
                                         422 before the handler runs, so it does
                                         not count against the limit
  -> rate limit check (fingerprint)      unchanged from US-076; 429 + Retry-After
  -> honeypot: website.strip() != ""     400 "Invalid submission", nothing stored;
                                         the request already counted against the
                                         limit
  -> clean_text() -> predict_feedback()  unchanged
  -> insert feedback                     unchanged (source 'public', public_ref,
                                         submitter_hash, retention_until)
  -> 200 { public_ref, status, created_at }
```

The honeypot check sits after the rate limit on purpose. A bot that fills
`website` still spends its bucket, so ignoring the 400 and retrying does not help
it. `website` has no length cap for the same reason: a length error would be a
422 raised before the limiter, a free probe.

Status (`GET /api/public/feedback/{public_ref}`):

```
  -> rate limit check (fingerprint)
  -> select by public_ref, limit 1
  -> 404 when absent, OR retention_until < now, OR redacted_at IS NOT NULL
     (one response for all three, so the endpoint stays a non-oracle)
  -> 200 { public_ref, status, created_at }
```

Retention (`backend-worker`, daily at 03:00 Asia/Ho_Chi_Minh):

```
APScheduler cron job in pipeline/worker_ticket.py
  -> services/retention.redact_expired_public_feedback(now)
       UPDATE feedback
          SET text = '[Đã xoá theo hạn lưu trữ]',
              submitter_hash = NULL,
              redacted_at = now
        WHERE source = 'public'
          AND retention_until < now
          AND redacted_at IS NULL
  -> redact the reachable copies of that text (see Data Model)
  -> log the count only
```

The job is idempotent: a second run on the same data returns 0. It uses the same
`add_job(..., "cron", timezone="Asia/Ho_Chi_Minh")` style as
`pipeline/worker_agent.py`.

Account creation (Staff web admin page → `POST /api/admin/users`):

```
require_admin
  -> validate body in the handler (not by FastAPI, whose 422 echoes the input);
     errors are 400 and name fields only
  -> password meets the 5 criteria (>= 8 chars, upper, lower, digit, special),
     the same set the old sign-up form checked; else 400 naming the criteria
  -> auth.admin.create_user(email, password, email_confirm=True,
       user_metadata={full_name},
       app_metadata={must_change_password: true})
       duplicate email -> 409
  -> handle_new_user trigger inserts the profile as 'pending'
  -> update profiles.role / department; on failure delete the new auth user
     and return 503
  -> audit_logs row
  -> 201 { status: 'success', data: { id, email, role, department } }
     never the password
```

The flag lives in `app_metadata` because only the service role can write it. A
flag in `user_metadata` could be cleared by the user with `auth.updateUser`.

First login (Staff web `_authenticated` layout):

```
session.user.app_metadata.must_change_password === true
  -> change-password screen only (new password twice, same 5 criteria)
  -> POST /api/me/password { new_password }
       backend: auth.admin.update_user_by_id(uid, { password,
                  app_metadata: { must_change_password: false } })
  -> supabase.auth.refreshSession()   new JWT without the flag, so
                                      is_ops_staff() lets the account in
  -> router.invalidate(); continue to the role's normal landing
```

Until then the server refuses the account on its own: the role guards return
403, `SupabaseTokenVerifier` returns 401 for the JWT, and `is_ops_staff()` /
`is_admin()` are false because `password_is_current()` is false.

Pending login:

```
role === 'pending'
  -> "Tài khoản đang chờ admin cấp quyền" + logout; no nav, no data fetches
```

## Interface Contract

`POST /api/public/feedback` — no `Authorization` header, none read.

| | |
| --- | --- |
| Body | `{ "text": string (1..4000), "channel"?: string (<=40), "area"?: string (<=80), "website"?: string }` |
| 200 | `{ "status": "success", "data": { "public_ref", "status", "created_at" } }` |
| 400 | `website` non-empty after strip, or text empty after cleaning. The honeypot raises `HTTPException(400, detail="Invalid submission")`; on the wire the app's handler sends `{ "error": { "code": "HTTP_ERROR", "message": "Invalid submission" } }`. |
| 422 | Body fails pydantic validation. Raised before the handler, so it does not count against the rate limit. |
| 429 | Rate limit exceeded; `Retry-After` in seconds. |
| 503 | Database unreachable. |

Order: pydantic validation → rate limit → honeypot → clean, classify, insert.

`GET /api/public/feedback/{public_ref}` — no `Authorization` header.

| | |
| --- | --- |
| 200 | `{ "status": "success", "data": { "public_ref", "status", "created_at" } }`. The allowlist is exactly `{public_ref, status, created_at}`. |
| 404 | Unknown, expired, or redacted reference. One body for all three. |
| 429 | Rate limit exceeded. |

`status` is one of `received | under_review | reviewed`. It is derived, never
stored: `reviewed` when `reviewed`, `under_review` when `needs_review`, otherwise
`received`. The value `resolved` is gone.

`POST /api/admin/users` — `require_admin`.

| | |
| --- | --- |
| Body | `{ "email", "full_name", "role": "admin" \| "manager" \| "staff", "department"?, "temp_password" }` |
| 201 | `{ "status": "success", "data": { "id", "email", "role", "department" } }` |
| 400 | Validation error (invalid email, empty name, role outside the three, unknown department, password over 72 chars): the message names the fields only, never a value. A password that fails the 5 criteria: the message names the failed criteria. The handler validates the body itself; only a body that is not a JSON object still reaches FastAPI's 422. |
| 403 | Caller is not admin, or is an admin still on a temporary password. |
| 409 | Email already exists. |
| 503 | Supabase Auth refused (message carries the error code only), or the role grant failed and the new account was rolled back. |

`POST /api/me/password` — `get_current_user` only, so open to a Pending account
and to an account still on its temporary password.

| | |
| --- | --- |
| Body | `{ "new_password": string }` |
| Effect | `auth.admin.update_user_by_id(user.id, { password, app_metadata: { must_change_password: false } })` |
| 200 | `{ "status": "success", "data": { "must_change_password": false } }` |
| 400 | `new_password` missing, not a string, over 72 chars, or failing the 5 criteria. The message names the field or the criteria, never the password. |
| 401 | No or invalid session. |
| 503 | Supabase Auth refused; the message carries the error code only, never the password. |

`GET /api/me` now also returns `must_change_password`.

Other contract changes:

- `POST /api/feedback/submit` requires ops staff (was: any logged-in account).
- Every route except `GET /api/me`, `POST /api/me/password` and `/health`
  returns 403 for `pending`. `/api/public/*` never reads a token, so it is
  unaffected.
- `require_ops_staff`, `require_admin` and `require_manager` return 403
  "Bạn cần đổi mật khẩu tạm trước khi tiếp tục" while
  `app_metadata.must_change_password` is true. `GET /api/me` and
  `POST /api/me/password` are the only identity-only routes.
- `POST /api/agent/chat`: the `role == 'guest'` tier is removed. `public_only`
  still drops an ops caller to the public FAQ tier (the landing widget). A
  Pending account gets 403.
- MCP (`mcp_auth.py`, `mcp_server.py`, `chat_tools.py`): a role of `pending`, any
  role outside the three Staff roles, or an ops profile with no department maps
  to `pending`. Over HTTP, `SupabaseTokenVerifier` rejects that identity with 401
  for both a JWT and an `mcp_tokens` bearer, and rejects a JWT carrying
  `app_metadata.must_change_password` with 401: no session, no tool list. On
  stdio, `MCP_ROLE` defaults to `pending`, which gets no tools. The guest tool
  tier is removed.
- `/api/feedback/recent` loses its guest-only filter. The cockpit loses
  `restricted = role == 'guest'`.

The unauthenticated route set stays `/`, `/health` and the two public routes.
The pinned-route guard test in `pipeline/tests/test_public_intake.py` must pass
unchanged.

## Data Model

One forward-only migration,
`supabase/migrations/20260927000000_retire_guest_role.sql`:

The file has eight sections, in this order:

| § | Section (as titled in the file) | Change | Reason |
| --- | --- | --- | --- |
| 1 | `profiles.role: guest -> pending` | Drop every CHECK on `profiles` whose definition names `guest`; `UPDATE profiles SET role = 'pending' WHERE role = 'guest'`; new `profiles_role_check` on `admin, manager, staff, pending`; column DEFAULT → `pending`. | Retire the value without deleting an account: FKs to `auth.users` are `ON DELETE CASCADE`, so a delete would take the user's feedback, alerts and chat with it. The default was `staff` (`20260612120000_rbac_roles.sql:15`), so a profile inserted outside the trigger got ops rights. |
| 2 | Sign-up trigger: new accounts are pending | `handle_new_user` assigns `pending`; `EXECUTE` revoked from `PUBLIC`, `anon`, `authenticated`. | Keeps the "first profile ever becomes admin" bootstrap. |
| 3 | `feedback`: direct INSERT only for ops staff, as themselves | "Feedback insert own" → "Feedback insert ops" `WITH CHECK (is_ops_staff() AND auth.uid() = user_id)`. | Closes the PostgREST path that let any account write self-labelled rows past the classifier and rate limit. |
| 4 | `mcp_tokens.role`: legacy column, same vocabulary | Same CHECK swap and `guest` → `pending` rewrite as § 1. | Not the source of truth since `20260702010000` (role resolves live from `profiles`), but its CHECK still named `guest`. |
| 5 | `profiles`: no self-insert or self-delete from the browser | Drop "Users insert own profile"; `REVOKE INSERT, DELETE, TRUNCATE ON profiles FROM authenticated`. | The policy let an account without a profile row insert one with any role, admin included. Profiles now come only from the trigger and change only through the backend. |
| 6 | RLS helpers refuse an account still on its temporary password | New `password_is_current()` reads `auth.jwt() -> 'app_metadata' ->> 'must_change_password'`; `is_ops_staff()` and `is_admin()` now also require it. | Closes PostgREST and realtime to a flagged account, as the backend guards already do. |
| 7 | `graph_nodes` / `graph_edges`: internal knowledge base, ops staff only | Replace the `USING (true)` read policies with "Graph nodes select ops" / "Graph edges select ops" `USING (is_ops_staff())`. | Any signed-in account, now including every self-signup as `pending`, could read the internal SOP/SLA knowledge base. The backend reads it with the service role and is unaffected. |
| 8 | `feedback.redacted_at`: set by the daily retention job | `+ feedback.redacted_at TIMESTAMPTZ`, plus column comments on `redacted_at` and `retention_until`. | Marks a row the retention job has redacted, and makes the job idempotent. |

`is_ops_staff()` excludes every role outside admin, manager and staff, so
`pending` has ops rights nowhere in RLS by construction. The backend treats any
non-ops token role as `pending`.

Where public free text is copied. The job clears `correction_logs.note`, the one
copy linked by `feedback_id`. These copies have no id link, so the job leaves
them unredacted; `validation.md` lists them as known gaps, not silently skipped:

- `alerts.title` / `alerts.description`. In no-LLM mode,
  `llm_agent.mock_spike_response` quotes up to 3 samples of 120 characters each.
- P5 alert webhook payloads (`webhook_notifier.send_alert_webhook`, from
  `spike_detector.py:268`), sent to `WEBHOOK_URL` or printed to stdout when it
  is unset.
- `tasks.title` / `tasks.summary`: `pipeline/main.py` passes the alert title and
  `alert.description[:300]` to `create_ticket_task`.
- `department_reports.content` (Markdown) and `root_cause_summary`: LLM output
  derived from feedback samples.
- `chat_messages`, via alert text the assistant quotes.
- External LLM providers, which receive the samples in prompts.
- `model_router`'s `prompt_preview` (first 160 characters of the first user
  message, after `sanitize_pii_payload`) in `pipeline/logs/agent.log`
  (`pipeline/agent/model_router.py:358, 380`), on the container filesystem when
  deployed.
- Supabase backups and PITR.

## UI / Platform Impact

Customer web (`customer-web/`, new):

- Vite + React static SPA. React and Vite majors match `app/`. Pages: `/` and
  `/status/:code`. Vietnamese only.
- Mobile-first. Same brand tokens as the Staff web (`app/src/styles.css`: colors,
  radius, shadow; "aurora cards, rounded + shadow" from US-UI-01), without the
  internal cockpit look.
- No Supabase client and no Supabase env vars. One build-time env var,
  `VITE_BACKEND_API_URL` (same name as the Staff web), passed as a Docker build
  `ARG`.
- The browser calls the backend directly. No BFF: the limiter keys on the
  rightmost `X-Forwarded-For` hop, and a proxy would put every Customer in one
  bucket.
- The error-envelope parsing, `regions.ts` and the few UI primitives are copied
  from `app/`, not imported. There are no workspaces.
- A mounted toast or inline-message system carries validation, 429 and network
  errors.
- Honeypot input `website`: visually hidden, `tabIndex={-1}`,
  `autocomplete="off"`, sent in the POST body.
- Privacy copy: "Không cần tài khoản. Số điện thoại, email, biển số được che tự
  động. Nội dung tự xoá sau 180 ngày."
- `Dockerfile` (multi-stage; static serving with SPA fallback; listens on
  `$PORT`), `README.md`, vitest tests. Dev server port 5175.
- nginx (`nginx.conf.template`) sends `Content-Security-Policy`, whose
  `connect-src` is `'self'` plus `$BACKEND_ORIGIN` (the Dockerfile sets that env
  from the `VITE_BACKEND_API_URL` build arg), `Strict-Transport-Security`,
  `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff` and
  `X-Frame-Options: DENY`, with `server_tokens off`.

Staff web (`app/`):

- Deleted: `/f`, `/f/status/$code`, `GuestDashboard` and its dashboard branch,
  and `publicFetch` with its test, if nothing else uses them.
  `routeTree.gen.ts` is regenerated by the build.
- `/auth` is login-only: no sign-up form, no Google or Facebook buttons.
- First-login password change, and the pending screen (see Application Flow).
- Admin page: a "Tạo tài khoản" form; pending accounts listed as "Chờ cấp quyền";
  bulk approve works on pending.
- Landing: every CTA says "Đăng nhập" and goes to `/auth`. A new "Gửi phản hồi"
  CTA goes to `VITE_CUSTOMER_WEB_URL` (build-time; fallback
  `http://localhost:5175`). The chat widget's canned replies point to the
  Customer web. The widget's anonymous `/api/me` call gets an `enabled` guard.
- Feedback list: a "Khách hàng" badge on rows with `source === 'public'`.
- `<Toaster/>` mounted once in `__root.tsx`.

Deploy: a new Railway service `customer-web` is documented in
`docs/project/deploy-railway.md` and not created. Production does not serve
today (backlog #7).

Outside the repo: the Supabase Dashboard sign-up toggle and the Google and
Facebook providers stay on until the owner turns them off
(`docs/project/setup-supabase.md` §8.1). Until then, the Supabase Auth API still
accepts a direct sign-up. It lands as `pending`, with no access.

## Observability

- Account creation writes an `audit_logs` row, like every other admin action. The
  password is never logged, never stored outside Supabase Auth, and never
  returned. The same holds for `POST /api/me/password`, which logs only the
  user id and the error code on failure.
- A honeypot rejection logs no body. It is countable only through the access log
  (400 on the route).
- The retention job logs how many rows it redacted, never the text. A redacted
  row is countable as `redacted_at IS NOT NULL`.
- Public intake volume stays a plain `source='public'` query.

## Alternatives Considered

Recorded in full in
`docs/harness/decisions/0017-separate-customer-web-retire-guest.md`:

- Keep `/f` inside the Staff web, as decision 0016 placed it.
- Route by Host inside the one Nitro server.
- A second build from `app/` with another `srcDirectory`.
- A BFF or proxy in front of the public API.
- Keep `guest` as the customer account.
- Hard-delete rows past retention.
