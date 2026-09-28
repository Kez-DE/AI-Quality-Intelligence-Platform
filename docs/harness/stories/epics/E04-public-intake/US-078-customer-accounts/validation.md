# Validation

Proof status: **in progress** (2026-09-28).

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
- Whether an admin may move a `guest` to a Staff role through
  `PATCH /api/users/{id}/role` is a backend rule (decision 0018 Follow-Up). The
  Staff web does not offer it: `guest` rows are read-only in the admin list.

## Acceptance Evidence

2026-09-28, branch `feat/customer-accounts`.

- **Staff web:** `npx tsc --noEmit` clean; `npx vitest run` 5 files, 25 tests
  passed (adds `customer-accounts.test.tsx`: `guest` row read-only in the admin
  list, employee panel lists Staff roles only); `npm run build` ok.
- Backend, migration, Customer web and E2E: pending.
