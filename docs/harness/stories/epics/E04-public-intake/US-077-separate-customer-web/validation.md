# Validation

Proof status: **implemented** (2026-09-27). Unit, integration and E2E proof
recorded below; platform (deployed Customer web) is still open, see backlog #10.

## Proof Strategy

Four claims carry this story. Each one must fail loudly if it breaks:

1. **A Customer needs nothing but the Customer web.** A submit with no token
   returns a Lookup code. The status page shows the Feedback status and the date,
   and no AI label. Every error is visible in the browser.
2. **A Pending account gets nothing.** Every backend route except `GET /api/me`,
   `POST /api/me/password` and `/health` answers 403. The Staff web shows it one
   screen and fetches no data. An account still on its temporary password is
   refused on the server too (role guards, MCP, RLS), not only by the Staff web.
3. **Retiring `guest` loses no data and opens no door.** No profile or feedback
   row is deleted. No `guest` value survives the migration. No fallback grants
   more than `pending`. An authenticated account without an ops role can no
   longer `INSERT` into `feedback`.
4. **Retention takes the words and keeps the numbers.** Expired public rows lose
   their text and submitter hash. Nothing else on them changes, and no other row
   is touched.

Claims 2 and 3 matter most. The failure mode of this story is a role rename that
quietly fails open. Tests assert 403 across the whole route table, not on a few
hand-picked endpoints.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | `derive_status` maps `reviewed` → `reviewed`, `needs_review` → `under_review`, else `received`, and never returns `resolved`. Honeypot: missing, `""` and whitespace-only `website` pass; any other value is rejected. `redact_expired_public_feedback`: redacts only rows with `source='public'`, `retention_until < now` and `redacted_at IS NULL`; sets the placeholder text, `submitter_hash = NULL` and `redacted_at = now`; leaves `topic`, `sentiment`, `severity`, `area`, `channel`, `created_at` and `overall_risk` unchanged; leaves non-public rows and future-retention rows unchanged; returns the count; a second run returns 0. `auth_guard`: a missing profile, a NULL role and an unknown role (including a leftover `guest`) resolve to `pending`; `VALID_ROLES` is exactly `{admin, manager, staff, pending}`. Password check: each of the 5 criteria rejects on its own; a password that meets all 5 passes (backend and Staff web). Customer web: the status-label map gives the three Vietnamese labels; the error-envelope parser reads `error.message`; the honeypot input is hidden, has `tabIndex=-1` and `autocomplete="off"`. |
| Integration | Public submit with non-empty `website` → 400 with body `{error:{code:'HTTP_ERROR',message:'Invalid submission'}}`, no row stored, and the request counts toward the limit (5 honeypot posts, then a clean post → 429). A body that fails pydantic validation → 422 and does not count toward the limit. The status response has exactly the keys `public_ref`, `status`, `created_at`. An expired row → 404. A redacted row → 404. Both bodies equal the unknown-reference 404 body. Pending: a scan of every mounted route with a pending token returns 403 except `GET /api/me` (200, role `pending`), `POST /api/me/password`, `/health` and the public routes. `POST /api/feedback/submit`: pending → 403, staff → 200. `POST /api/agent/chat`: pending → 403; ops with `public_only` → public tier. MCP over HTTP: `SupabaseTokenVerifier` returns no access token (401, no tool list) for a pending or unknown role, an ops profile with no department, a JWT with no profile, a pending bearer token, and a JWT whose `app_metadata.must_change_password` is true. MCP over stdio: `MCP_ROLE` unset or `pending` → an empty tool list. `POST /api/admin/users`: non-admin → 403; a weak password → 400; an invalid field → 400 naming the field only; a duplicate email → 409; success calls `auth.admin.create_user` with `email_confirm=True` and `app_metadata={must_change_password: true}`, sets role and department, writes one `audit_logs` row, and returns 201 `{status:'success', data:{id, email, role, department}}` with no password key. Temporary password: `get_current_user` reads the flag from `app_metadata` and ignores it in `user_metadata`; `require_ops_staff`, `require_admin` and `require_manager` return 403 for a flagged account while `GET /api/me` still answers 200 with `must_change_password: true`; `POST /api/me/password` calls `auth.admin.update_user_by_id` with the new password and `app_metadata {must_change_password: false}`, rejects bad input with 400 and a provider failure with 503, never echoes or logs the password, and needs a session (401 without one). Bulk approve moves `pending` → staff/manager and leaves other roles alone. The retention job is registered in `worker_ticket.py` as a cron at 03:00 `Asia/Ho_Chi_Minh`. The pinned unauthenticated-route guard test passes unchanged. |
| Migration (local DB) | Against a local stack only (`supabase start`, then `supabase db reset` to apply every migration). Before/after counts of `profiles`, `feedback`, `alerts` and `chat_messages` are equal. Zero rows have `role = 'guest'` afterwards. The role CHECK rejects `guest` and accepts `pending`. The column default is `pending`. The trigger makes the first profile `admin` and the second `pending`. As a pending user, a PostgREST `INSERT` into `feedback` is denied. As a staff user, an `INSERT` with its own `user_id` is allowed. As any authenticated user, a PostgREST `INSERT` or `DELETE` on `profiles` is denied. As a pending user, a `SELECT` on `graph_nodes` / `graph_edges` returns no rows; as a staff user it returns rows. As a staff user whose JWT carries `app_metadata.must_change_password = true`, `is_ops_staff()` is false, so ops reads return only the user's own rows; after the password change and a session refresh they return everything again. `feedback.redacted_at` exists. `mcp_tokens` has no `guest` rows afterwards, and its role CHECK accepts `pending` and rejects `guest`. |
| E2E | Local stack, both webs in a browser. Customer web at a phone viewport: submit → Lookup code with copy and a status link; the status page shows one of the three labels and a date, no topic and no severity; an unknown code → a friendly not-found; a 429 and a network failure are visible; the privacy copy is present. Staff web: `/auth` has no sign-up form and no OAuth button; `/f` and `/f/status/x` are not routes. The admin creates an account → the new user logs in → the change-password screen only → after the change, the normal landing. A migrated pending user logs in → the waiting screen only; the network log shows no data request besides `/api/me`. The landing "Gửi phản hồi" link goes to `VITE_CUSTOMER_WEB_URL`. The feedback list shows "Khách hàng" on public rows. A toast renders. With sign-up disabled in the local Auth config, the admin create endpoint still creates a user (see Known Gaps). |
| Platform | `customer-web`: `tsc --noEmit`, `vite build`, `vitest run`. A `docker build` with `--build-arg VITE_BACKEND_API_URL=...`, then a run with `PORT` set: `/` serves, `/status/abc` falls back to `index.html`, and responses carry `Content-Security-Policy` (with the build-arg backend in `connect-src`) and `Strict-Transport-Security`, and no nginx version in `Server`. Staff web: `tsc --noEmit`, `vite build` (the regenerated `routeTree.gen.ts` has no `/f` route), `vitest run`. |
| Performance | None expected. The retention job is one bounded `UPDATE` a day on a partial set of rows. Submit and status paths gain one string check. |
| Logs/Audit | Asserted by omission, as in US-076: no captured log line contains submitted text, the `website` value or a password. Account creation writes exactly one `audit_logs` row. The retention job logs a count and nothing else. |

## Fixtures

- `tests/_fakedb.FakeDB`, as in US-076, seeded with public rows on both sides of
  `retention_until` and one already-redacted row. Seed non-public rows too
  (`manual`, `chat`, a dataset source) to prove they are untouched.
- A stub `predict_feedback` with a fixed classification.
- Fixed client IPs from TEST-NET-3 (`203.0.113.10`, `203.0.113.11`) sent as
  `X-Forwarded-For`. Rate limiters are reset between tests.
- Tokens or `AuthUser` doubles for `admin`, `manager`, `staff`, `pending`, and an
  unknown role string.
- A fake `auth.admin.create_user` that records its arguments and can raise the
  duplicate-email error.
- A fixed `now` passed to `redact_expired_public_feedback(now=...)`.
- For the local migration run: one seeded `guest` profile that owns a feedback
  row, an alert and a chat message, so the before/after counts mean something.

## Commands

> **Warning:** plain `pytest` loads the repo-root `.env`
> (`pipeline/env_config.py`), which points at PRODUCTION. Always run the suite
> with the offline Supabase values below. `load_dotenv(override=False)` keeps
> the inline values, so any stray Supabase call goes to a closed local port
> (`127.0.0.1:9`) instead of production.
> `test_rag_query.py` is a script that calls Supabase and Cohere at import time,
> so it is ignored.

```text
cd pipeline && SUPABASE_URL=http://127.0.0.1:9 VITE_SUPABASE_URL=http://127.0.0.1:9 SUPABASE_SERVICE_ROLE_KEY=offline-test .venv/bin/python -m pytest -q --ignore=test_rag_query.py
cd app && npx tsc --noEmit && npm run build && npm run test
cd customer-web && npm run typecheck && npm run build && npm run test
docker build -t customer-web --build-arg VITE_BACKEND_API_URL=http://127.0.0.1:8000 customer-web
docker run --rm -e PORT=8080 -p 8080:8080 customer-web   # then GET / and /status/abc
```

Local database only. Export the local stack's URL and keys inline for the command.
Never use the repo-root `.env`, which points at production. See US-076's
validation for the pattern.

```text
cd supabase && supabase start && supabase db reset
```

The `customer-web` image builds with that folder as its context (the
`Dockerfile` header says so; on Railway the service Root Directory is
`customer-web`).

## Known Gaps

- Whether `auth.admin.create_user` keeps working after "Allow new users to sign
  up" is turned off in the Supabase Dashboard is not verified from the Supabase
  docs. The E2E row above covers it on the local stack. The owner should also
  create one test account right after flipping the switch in the Dashboard.
- The retention job clears `correction_logs.note` for redacted rows. It does not
  reach copies that have no `feedback_id` link. Every such copy stays
  unredacted:
  - `alerts.title` and `alerts.description`. In no-LLM mode,
    `llm_agent.mock_spike_response` quotes up to 3 samples of 120 characters
    each.
  - P5 alert webhook payloads (`pipeline/webhook_notifier.py`, from
    `pipeline/spike_detector.py:268`), sent to `WEBHOOK_URL` or printed to
    stdout when it is unset. A delivered webhook cannot be recalled.
  - `tasks.title` and `tasks.summary`: `pipeline/main.py` passes
    `alert.description[:300]` to `create_ticket_task`.
  - `department_reports.content` (Markdown) and `root_cause_summary`: LLM
    output derived from feedback samples.
  - `chat_messages`, via alert text the assistant quotes.
  - External LLM providers, which receive the samples in prompts.
  - `model_router`'s `prompt_preview` (first 160 characters, after
    `sanitize_pii_payload`) in `pipeline/logs/agent.log`
    (`pipeline/agent/model_router.py:358, 380`), on the container filesystem
    when deployed.
  - Supabase backups and PITR.

  Claim 4 covers the `feedback` row and `correction_logs.note` only.

## Acceptance Evidence

2026-09-27, branch `feat/customer-web` on base `a69c4ee`.

- **Unit / integration:** pytest (neutralised command above) 415 passed,
  3 skipped, 2 xfailed; baseline 287 passed, 0 regressions. flake8 CI gate 0.
  Staff web: tsc clean, vitest 21 passed, build ok. Customer web: tsc clean,
  vitest 20 passed, build ok; `docker build` then curl `/` and `/status/<code>`
  200 with Content-Security-Policy and Strict-Transport-Security headers.
- **Migration:** `20260927000000_retire_guest_role.sql` verified on the local
  stack (`supabase db reset --local`, and upgrade over seeded guest data;
  `is_ops_staff()` false for a JWT with `app_metadata.must_change_password`,
  false for pending, true after the change). Applied to production
  `gvtoqbowulwmpzfogjwp`: 2 guest profiles became pending, no rows deleted.
  A schema dump and the guest ids were saved before the push for rollback.
- **E2E (chrome-devtools, local servers on the production database):**
  - Customer web: submit returns a 12-character Lookup code and shows no AI
    label; the status page shows only status and date; the API returns exactly
    `{public_ref, status, created_at}`; an unknown code is 404. The stored row
    has `user_id` NULL, `source='public'`, AI labels, the phone number masked
    and `retention_until` +180 days.
  - Staff web: `/auth` is login only with a link to the Customer web; the
    Customer row shows the "Khách hàng" badge; admin "Tạo tài khoản" works; the
    new account's first login shows only "Đổi mật khẩu", `/api/me` reports the
    flag and ops routes answer 403 until `POST /api/me/password` (200) clears
    it in `app_metadata`.
  - Pending account: waiting screen only, also on a direct `/admin`;
    PostgREST returns 0 rows for feedback, alerts and graph_nodes; a
    self-update of `profiles.role` is denied (42501).
  - Cleanup: E2E accounts and the E2E feedback row were deleted. The temporary
    E2E admin could not be deleted (`audit_logs.actor_id` is NOT NULL with ON
    DELETE SET NULL, backlog #12), so it was demoted to pending, banned and
    given an unknown random password.
