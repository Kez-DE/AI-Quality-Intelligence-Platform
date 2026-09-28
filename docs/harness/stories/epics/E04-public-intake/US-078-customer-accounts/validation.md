# Validation

Proof status: **implemented** (2026-09-28), with open items. Two E2E cases
are blocked by the environment: delivery of a real reset email, and
Google/Facebook OAuth. The local
migration layer did not run, so the first-profile-admin branch and a behavioural
CHECK rejection are unproven. See Known Gaps and Acceptance Evidence.

## Proof Strategy

Four claims carry this story. Each one must fail loudly if it breaks:

1. **A Customer account gets the Customer web and nothing else.** Every Staff
   route answers a `guest` token with 403. RLS gives it no ops rights. The Staff
   web shows it one screen and fetches no data.
2. **Every Customer write goes through the classifier.** `POST
   /api/customer/feedback` and the chat `submit_feedback` tool store the same
   labels the public route would store for the same text. No path takes labels or
   severity from the caller or the model.
3. **A Customer account sees only its own rows, and no AI label.** The history
   has exactly `public_ref`, `status`, `created_at`, `text`.
4. **Sign-up changes no existing data and opens no Staff door.** The migration
   updates and deletes nothing. A new sign-up lands as `guest`, never `pending`
   or a Staff role (except the first profile ever). The column DEFAULT stays
   `pending`.

Claims 1 and 2 matter most. The failure mode of this story is a second non-Staff
role that some guard forgets. Tests sweep the whole route table with a `guest`
token, not a few endpoints.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | `auth_guard`: `guest` resolves to `guest`; missing or unknown roles still resolve to `pending`; `VALID_ROLES` is exactly `{admin, manager, staff, pending, guest}`. `require_customer` accepts `guest` only. Staff web `toRole`: the three Staff roles and `guest` pass through, anything else (including `"Guest"`, `""`, `null`) is `pending`. `staffWebGate`: `guest` → `customer` on every path; the password change still comes first. Staff web admin user list: a `guest` row has no role or department select; the dashboard employee panel lists Staff roles only (no `guest`, no `pending`). Customer web: the 5 password criteria; the role check sends a non-guest account to the staff message; the history maps status to the three Vietnamese labels. |
| Integration | Sweep every mounted Staff route with a `guest` token: 403, except `GET /api/me` (200, role `guest`), `POST /api/me/password`, `/health` and the public routes. Sweep `/api/customer/*` with admin, manager, staff and pending tokens: 403; without a token: 401. `POST /api/customer/feedback`: stores `source='customer'`, `user_id` = caller, a `public_ref`, and the classifier's labels for the text; honeypot filled → 400, nothing stored; the per-user limit returns 429; the response has exactly `public_ref`, `status`, `created_at`. `GET /api/customer/feedback`: own rows only, newest first, exactly `public_ref`, `status`, `created_at`, `text`. `POST /api/customer/chat`: rate limited per user; the `submit_feedback` tool calls the same insert path, and a stubbed model that proposes labels or P3 does not change the stored labels. `POST /api/admin/users` still sets the Staff role after the trigger inserts `guest`. The pinned unauthenticated-route guard test passes unchanged. |
| Migration (local DB) | Local stack only (`supabase start`, `supabase db reset`). Before/after counts of `profiles` and `feedback` are equal; no existing role value changes. The CHECK accepts `guest` and `pending` and rejects an unknown value, on `profiles` and `mcp_tokens`. The column DEFAULT is `pending`. The trigger makes the first profile `admin` and the second `guest`. As a `guest` user: `is_ops_staff()` is false; PostgREST `INSERT` into `feedback` is denied; `SELECT` on `feedback` and on `alerts` returns 0 rows, including rows whose `user_id` is the caller (same as a `pending` user); as an ops staff user, `SELECT` on both still returns rows; `SELECT` on `graph_nodes` / `graph_edges` returns no rows; `INSERT` / `DELETE` on `profiles` is denied; a self-update of `profiles.role` is denied. |
| E2E | Local stack, both webs. Customer web at a phone viewport: sign up → lands logged in (or after confirmation) → header shows email, "Phản hồi của tôi", "Đăng xuất"; submit → only a Lookup code; `/cua-toi` lists it, links to `/status/:code`, no AI label; chat answers and filing through chat shows up in `/cua-toi`; forgot password → reset link → new password works; logged out, the anonymous form still works. A Staff account logged in on the Customer web sees "Tài khoản nhân viên dùng Staff web" and the network log shows no `/api/customer` call. Staff web: a `guest` login shows "Đây là tài khoản khách hàng" only, also on a direct `/admin`, with no data request besides the profile read; the link opens the Customer web; the feedback list shows "Khách hàng" on `customer` rows. Google and Facebook OAuth return to the Customer web origin. |
| Platform | Staff web: `tsc --noEmit`, `vitest run`, `npm run build`. Customer web: typecheck, build, vitest; `docker build` with the Supabase build args, and the CSP `connect-src` contains the Supabase URL. |
| Performance | None expected. One more role check per request. |
| Logs/Audit | Asserted by omission: no captured log line contains submitted text, chat text, the `website` value or a password. |

## Fixtures

- `tests/_fakedb.FakeDB`, seeded with rows of two Customer accounts and a public
  row, to prove the history filters by `user_id`.
- A stub classifier with a fixed result, and a stub chat model that calls
  `submit_feedback` with its own labels and P3.
- `AuthUser` doubles for `admin`, `manager`, `staff`, `pending`, `guest`, and an
  unknown role string.
- Rate limiters reset between tests.
- For the local migration run: one existing `pending` profile, to prove it stays
  `pending`.

## Commands

> **Warning:** plain `pytest` loads the repo-root `.env`, which points at
> PRODUCTION. Always use the neutralised values below. `test_rag_query.py` is
> ignored because it calls Supabase and Cohere at import time.

```text
cd pipeline && SUPABASE_URL=http://127.0.0.1:9 VITE_SUPABASE_URL=http://127.0.0.1:9 SUPABASE_SERVICE_ROLE_KEY=offline-test .venv/bin/python -m pytest -q --ignore=test_rag_query.py
cd app && npx tsc --noEmit && npx vitest run && npm run build
cd customer-web && npm run typecheck && npm run build && npm run test
cd supabase && supabase start && supabase db reset
```

Local database only. Never `supabase db push` or `config push` from a working
copy; the orchestrator applies remote changes after the owner approves.

## Known Gaps

- Sign-up is open by design. Per-user rate limits do not stop a script that
  creates many accounts; captcha is a follow-up.
- `customer` rows have no `retention_until` (decision 0018 §9): the retention
  job never redacts them and their Lookup code never expires.
- `delete_user` still cascades, so deleting a Customer account deletes its
  history.
- `PATCH /api/users/{id}/role` refuses every change away from `guest` (400,
  "… Tạo tài khoản nhân viên qua form Tạo tài khoản"), `pending` included, so
  `guest → pending → staff` is closed too. `POST /api/users/bulk-approve` only
  touches `pending` rows. A Customer account can only be deleted (decision 0018
  §7). The Staff web shows `guest` rows read-only.
- Closed 2026-09-28 (owner's choice): `chat_completion` wrote `prompt_preview`
  (the first user message, PII-masked, up to 160 characters) to
  `pipeline/logs/agent.log`, which ops staff read through
  `GET /api/agent/logs`. It carried the Customer's chat text and, through the
  ml-worker scoring prompt, submitted Feedback text. `chat_completion` now takes
  `log_preview`; the public/customer chat tier and `call_llm` (scoring, analyst
  and task batch prompts) pass `False`. Staff web chat keeps its preview. The
  spike prompt in `llm_agent.py` keeps it: its first 160 characters are the
  fixed instruction text.

## Acceptance Evidence

2026-09-28, branch `feat/customer-accounts`.

- **Backend:** pytest with the neutralised env: 531 passed, 3 skipped, 2
  xfailed. Adds `test_customer_account_role_never_changes` (admin, manager,
  staff, pending: 400, role stays `guest`, no audit row) and
  `test_bulk_approve_skips_customer_accounts`. The customer route sweep covers
  admin, manager, staff and pending (403), and all three routes without a token
  (401). The pinned unauthenticated-route test body is unchanged; its `GUARDS`
  set gains `require_customer`, and
  `test_customer_routes_sit_behind_require_customer_only` pins the three
  customer routes to it. flake8 CI gate (`E9,F63,F7,F82`): 0.
- **Staff web:** `npx tsc --noEmit` clean; `npx vitest run` 5 files, 25 tests
  passed (adds `customer-accounts.test.tsx`: `guest` row read-only in the admin
  list, employee panel lists Staff roles only); `npm run build` ok.
- **Customer web:** `tsc --noEmit` clean; vitest 8 files, 65 tests passed
  (adds a regression for a `scrollIntoView` that returns a Promise); build ok.
  `docker build` with the `VITE_SUPABASE_*` build args: the CSP `connect-src`
  is `'self' http://127.0.0.1:8001 https://gvtoqbowulwmpzfogjwp.supabase.co`;
  HSTS is present; `/dang-nhap` answers 200.
- **Migration `20260928000000`:** not run on a local stack (local Supabase was
  stopped at the owner's request). Applied to production `gvtoqbowulwmpzfogjwp`
  on the owner's instruction, after `db push --dry-run` listed only this file.
  The schema snapshot taken before it is kept outside the repo. Production
  before and after, identical: profiles by role admin 1, manager 6, pending 3,
  staff 3; `auth.users` 13; `feedback` 5589; `alerts` 84; `chat_messages` 2.
  The 3 `pending` are the 2 ex-guests of decision 0017 and the US-077 temporary
  E2E admin, banned and demoted because an audit row blocks its deletion.
  After: the role CHECK on `profiles` and `mcp_tokens` is exactly the five roles
  (definition read, so an unknown value is rejected by construction; no insert
  was tried); `profiles.role` DEFAULT is `'pending'`; `handle_new_user` assigns
  `guest` (seen for a sign-up and for an Auth-admin-created user); "Feedback
  select" and "Alerts select" are `is_ops_staff()`; "Users manage own chat" is
  `auth.uid() = user_id AND is_ops_staff()` for USING and WITH CHECK;
  `authenticated` holds only SELECT, REFERENCES and TRIGGER on `profiles`, plus
  UPDATE on `full_name`; `migration list` shows local = remote. **Not
  verified:** the first-profile-admin branch, which needs an empty `profiles`
  table.
  - Ops staff still work (temporary `staff` account, PostgREST): `feedback`,
    `alerts`, `tasks`, `task_events` each return a row; a `chat_messages` row
    of its own saves (201), reads back and deletes (204). Realtime
    subscriptions were not exercised.
- **E2E**, 2026-09-28, chrome-devtools, local servers (backend :8001, Staff web
  :5174, Customer web :5175 at 390×844) on production Supabase:
  - Sign-up with email (autoconfirm on) lands logged in. The header shows the
    email, "Phản hồi của tôi" and "Đăng xuất". The profile is `guest`, with no
    `must_change_password` flag.
  - Logged-in submit: `POST /api/customer/feedback` 200 with exactly
    `public_ref`, `status`, `created_at`. The row has `source = 'customer'`,
    `user_id` = the account, the classifier's labels (Driver Behavior, negative,
    P3), phone and plate masked, and `retention_until` NULL (decision 0018 §9).
  - `/cua-toi` lists it and links to `/status/:code`, with no AI label.
    `GET /api/customer/feedback` returns exactly `public_ref`, `status`,
    `created_at`, `text`.
  - Logged out, the chat panel only asks the visitor to log in, and the
    anonymous form posts to `/api/public/feedback` (`source = 'public'`,
    `user_id` NULL, retention set).
  - Chat: `POST /api/customer/chat` 200 and the repl  - Chat: `POST /api/customer/chat` 200 and the reply renders. Found and fixed:
    in Chrome 153 the first reply blanked the page ("destroy is not a
    function"). The first run answered from the mock provider (the OpenRouter
    and OpenAI keys were rejected); the owner replaced the OpenRouter key and
    the run was repeated with a new test account:
    - A policy question ("để quên đồ trên xe") got a real answer from
      `openrouter` / `google/gemini-2.5-flash-lite`. Markdown such as `**…**`
      shows as plain text, since replies never render as HTML.
    - Asking the assistant to record a complaint made it call
      `submit_feedback`. The reply carried the stored Lookup code. The row has
      `source = 'customer'`, `channel = 'chat'`, the account's `user_id`, the
      classifier's labels (Safety, negative, P5, `needs_review`) and
      `retention_until` NULL. `/cua-toi` lists it as "Đang xem xét" with no AI
      label. The stored text is the model's rewording of the Customer's
      message, not the typed words.
    - The three new `agent.log` events (openrouter, ok) carry no
      `prompt_preview`; no line holds the chat text.
t with `redirect_to`
    `http://localhost:5175/dat-lai-mat-khau`. Supabase refused the test address
    (`email_address_invalid`), so no mail was sent. Found and fixed: the form
    said "try again in a few minutes"; it now explains `email_address_invalid`
    and `email_address_not_authorized`. A recovery link made with the Auth admin
    `generate_link` then opens `/dat-lai-mat-khau` logged in; the new password
    saves, the old one is refused, the new one logs in. **Not verified:**
    delivery of a real reset email.
  - A Staff account on the Customer web sees "Tài khoản nhân viên dùng Staff
    web" on `/` and `/cua-toi`; the network log has no `/api/customer` call.
  - Staff web, `guest` login: only "Đây là tài khoản khách hàng", also on a
    direct `/admin`. The link opens `http://localhost:5175/`. The only data
    requests are `auth/v1/user` and `profiles?select=role`.
  - Staff web, a `staff` login (Vận hành): the customer row shows the "Khách
    hàng" badge.
  - Live backend sweep with the `guest` JWT over every route in `openapi.json`:
    all 52 Staff routes answer 403 (51 in one pass, then
    `DELETE /api/users/{id}` on its own with a nil UUID). Only
    `/`, `/health`, `GET /api/me` (role `guest`) and
    `GET /api/customer/feedback` answer 200.
  - PostgREST with the `guest` JWT over all 14 public tables: 0 rows, except the
    account's own profile (1). Its own feedback row, by `public_ref`: 0 rows.
    `INSERT` into `chat_messages` and `feedback`: 403 (42501). `PATCH` of its
    own `profiles.role`: 403; the role stays `guest`. Tables with rows, so the
    0 is RLS: `tasks` 52, `task_events` 12, `task_completion_reports` 3,
    `alerts` 84, `feedback` 5589. `graph_nodes` and `graph_edges` are empty on
    production, so their 0 rows prove nothing alone; both SELECT policies are
    `is_ops_staff()`. `INSERT` and `DELETE` on `profiles` were not probed;
    `authenticated` holds no such grant (see Migration).
  - Logs: the uvicorn log holds no submitted text, chat text or password. The
    honeypot was not filled during E2E; its branches log nothing
    (`customer_api.py`, `public_intake.py`). During this E2E, before the fix,
    `agent.log` did record the test chat question as `prompt_preview`. After
    the fix, `test_customer_chat_text_never_reaches_the_agent_log` runs the
    real route down to `chat_completion` (mock provider) and finds no preview
    and no chat text; `test_batch_agents_call_the_router_without_a_preview`
    covers `call_llm`.
  - Cleanup: all three test accounts deleted (the cascade removed the customer
    row), the anonymous row and the probe chat row deleted. Production counts
    are back to the baseline above. No `audit_logs` row referenced the test
    accounts: both temporary Staff accounts came from the Auth admin API plus a
    role update, not from `POST /api/admin/users`.
- **Not run:** Google and Facebook OAuth. Both providers stay off on Supabase
  until the owner sets the client IDs.
