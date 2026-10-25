# Design

## Domain Model

Vocabulary is fixed in the repo-root `CONTEXT.md`. This story adds one term and
widens another:

- **Customer** — a person outside the company. May use the Customer web with or
  without an account.
- **Customer account** (new) — a Customer who signed up. `profiles.role =
  'guest'`. It logs in to the Customer web only. In the code its Feedback is
  `source = 'customer'`, `user_id = <the account>`, with a `public_ref`.
- **Pending account** — unchanged meaning: no access until an admin grants a
  Staff role, and the fail-closed value for a missing or unknown role. It is no
  longer where self sign-up lands.
- **Staff account** — unchanged. Only an admin creates one.

Invariants this story adds:

> A Customer account holds no Staff right. `is_ops_staff()` and `is_admin()` are
> false for `guest`. Every Staff route answers it with 403. The Staff web shows it
> one screen and fetches nothing.

> A Customer account writes Feedback only through the backend, and only through
> the same cleaning, classifier, rules, severity and honeypot as public intake.
> No path lets it choose its own labels, the chat tool included.

> A Customer account reads only its own Feedback, only through the backend
> (`GET /api/customer/feedback`), and never an AI label (`topic`, `sentiment`,
> `severity`). RLS gives it no `feedback` or `alerts` row at all.

> A self sign-up never lands in the admin's approval queue.

US-077's invariants all still hold. `pending` still reaches nothing but
`GET /api/me`, `POST /api/me/password` and `/health`.

Roles after this story: `VALID_ROLES = {admin, manager, staff, pending, guest}`.
`OPS_ROLES` is unchanged: `{admin, manager, staff}`.

## Application Flow

Sign-up (Customer web → Supabase Auth):

```
/dang-ky  email, password (5 criteria, checked client side), full_name
  -> supabase.auth.signUp(...)            or signInWithOAuth(google|facebook,
                                             redirectTo `${origin}/`)
  -> auth.users insert
  -> handle_new_user: first profile ever -> 'admin', else -> 'guest'
  -> (email confirmation, if the owner turned it on)
  -> session in the Customer web
```

Role check on the Customer web:

```
session present
  -> GET /api/me (Bearer)
  -> role == 'guest'  -> Customer account UI (history, chat, customer submit)
  -> any other role   -> "Tài khoản nhân viên dùng Staff web"; no /api/customer call
```

Submit as a Customer account (`POST /api/customer/feedback`):

```
Bearer token
  -> get_current_user -> require_customer (role == 'guest', else 403)
  -> pydantic validation                  same limits as public intake
  -> rate limit (key: user id)            429 + Retry-After
  -> honeypot: website.strip() != ""      400, nothing stored
  -> clean_text() -> classifier, rules, severity   same code path as public
  -> insert feedback  user_id = caller, source = 'customer', public_ref
  -> 200 { public_ref, status, created_at }
```

History (`GET /api/customer/feedback`):

```
require_customer
  -> select own rows (user_id = caller), newest first
  -> map each to { public_ref, status, created_at, text }
     status derived as on the public route
```

Customer chat (`POST /api/customer/chat`):

```
require_customer
  -> rate limit (key: user id)
  -> customer assistant: old guest tier from a69c4ee
       public knowledge base only, PUBLIC system prompt
  -> tool submit_feedback -> the same function POST /api/customer/feedback uses
       (no labels or severity from the model; the old fixed P3 is gone)
```

Staff web (`app/src/routes/_authenticated/route.tsx`):

```
profile role -> toRole(): admin|manager|staff|guest pass through, else 'pending'
staffWebGate():
  must_change_password -> 'change-password'
  pending              -> 'pending'   (waiting screen)
  guest                -> 'customer'  ("Đây là tài khoản khách hàng",
                                       link to VITE_CUSTOMER_WEB_URL, logout)
  blocked prefix       -> redirect /dashboard
  else                 -> AppShell
```

## Interface Contract

`POST /api/customer/feedback` — `Authorization: Bearer <Supabase JWT>`, role
`guest`.

| | |
| --- | --- |
| Body | `{ "text", "channel"?, "area"?, "website"? }`, same limits as `POST /api/public/feedback` |
| 200 | `{ "status": "success", "data": { "public_ref", "status", "created_at" } }` |
| 400 | Honeypot filled, or text empty after cleaning. Nothing stored. |
| 401 | No or invalid session. |
| 403 | Role is not `guest`. |
| 422 | Body fails validation. |
| 429 | Per-user rate limit; `Retry-After`. |

`GET /api/customer/feedback` — role `guest`.

| | |
| --- | --- |
| 200 | `{ "status": "success", "data": [ { "public_ref", "status", "created_at", "text" } ] }`, newest first, own rows only. Never `topic`, `sentiment`, `severity`, `user_id` or `submitter_hash`. |
| 401 / 403 | As above. |

`POST /api/customer/chat` — role `guest`.

| | |
| --- | --- |
| Body | `{ "messages": [...] }` |
| 200 | The assistant reply. |
| 401 / 403 / 429 | As above. |

Other contract changes:

- `GET /api/me` answers a `guest` token with its role.
- Every Staff route (`require_ops_staff`, `require_admin`, `require_manager`)
  answers `guest` with 403. The US-077 pending sweep runs with a `guest` token
  too.
- `/api/public/*` is unchanged and still reads no token.
- The unauthenticated route set is unchanged; the pinned guard test passes as
  is.

## Data Model

One forward-only migration,
`supabase/migrations/20260928000000_customer_accounts.sql`:

| Change | Reason |
| --- | --- |
| `profiles` role CHECK → `admin, manager, staff, pending, guest` | Allow the Customer account. |
| `mcp_tokens.role` CHECK → same list | Same vocabulary on the legacy column. |
| `handle_new_user`: first profile → `admin`, else → `guest` | Self sign-up lands as a Customer account, not in the approval queue. |
| Column DEFAULT on `profiles.role` stays `pending` | A profile inserted outside the trigger still gets no access. |
| `feedback` / `alerts` SELECT → `is_ops_staff()` only (section 3) | The own-row half is dropped, so no Customer or Pending account reads raw rows with AI labels through PostgREST. |

No `UPDATE` or `DELETE` of existing rows. The two `pending` ex-guests stay
`pending`.

No RLS loosening. `is_ops_staff()` names only the three Staff roles, so `guest`
has no ops rights by construction. Section 3 tightens `feedback` and `alerts`
`SELECT` to `is_ops_staff()` only: a Customer account (and a `pending` or
password-flagged account) reads no row of either table through PostgREST, not
even its own. Its history comes only from `GET /api/customer/feedback`
(service role, allowlisted fields). `feedback` `INSERT` stays ops-only, so its
only write path is the backend. `graph_nodes` and `graph_edges` stay ops-only.

`feedback.source` gains the value `customer`. It is a plain TEXT column, so no
schema change is needed for it.

`POST /api/admin/users` still works: the trigger now inserts the profile as
`guest`, and the handler sets the Staff role right after. If that update fails,
the handler deletes the new auth user as before.

Retention: `customer` rows are stored with `retention_until = NULL` (decision
0018 §9). The 0017 job redacts `source = 'public'` only, and the status lookup
treats a NULL deadline as "never expires", so a Customer account's Lookup code
resolves with no time limit. The text lives until the account is deleted
(cascade). A longer-term policy is a 0018 Follow-Up.

## UI / Platform Impact

Customer web (`customer-web/`):

- `@supabase/supabase-js` client from build-time `VITE_SUPABASE_URL` and
  `VITE_SUPABASE_PUBLISHABLE_KEY`. The nginx CSP `connect-src` adds the Supabase
  URL (a Dockerfile ENV set from a build arg).
- Pages `/dang-nhap`, `/dang-ky`, `/quen-mat-khau` (`resetPasswordForEmail`,
  redirect `${origin}/dat-lai-mat-khau`), `/dat-lai-mat-khau` (`updateUser`
  after recovery), `/cua-toi`.
- Header: logged out → "Đăng nhập"; logged in → email, "Phản hồi của tôi",
  "Đăng xuất".
- A floating chat button for logged-in Customer accounts; logged out, a prompt
  to log in.
- Same brand, mobile-first, Vietnamese copy, a11y, vitest for new logic.

Staff web (`app/`):

- `app/src/lib/access.ts`: `toRole` keeps `guest`; `staffWebGate` returns
  `customer` for it.
- `app/src/components/AccountGate.tsx`: `CustomerAccountScreen`, "Đây là tài
  khoản khách hàng", a link to `VITE_CUSTOMER_WEB_URL` and a logout button.
- `app/src/lib/api.ts`: `Role` gains `guest`, labelled "Khách hàng".
- Admin user list: a `guest` row is read-only. It shows the "Khách hàng" label
  instead of the role select and no department select; only delete stays. The
  Staff web never offers `guest` as a role to assign, and never offers a Staff
  role to a `guest`.
- Dashboard employee panel (`EmployeesPanel.tsx`): lists Staff roles only
  (`isStaffRole` from `app/src/lib/access.ts`), so Customer and Pending accounts
  never show as employees.
- Feedback list: the "Khách hàng" badge for `source === 'public'` or
  `'customer'`.

Supabase Auth (owner / orchestrator, outside the repo): sign-up, Email, Google
and Facebook stay on. Redirect URLs add `http://localhost:5175/**` and, later,
the production Customer web domain. Email confirmation is the owner's choice.

## Observability

- A honeypot rejection on the customer route logs no body, as on the public
  route.
- Rate limit events key on the user id; the log carries the id, never the text.
- Customer volume is a plain `source = 'customer'` query, separate from
  `public`.
- The chat never logs message text beyond what `model_router` already logs
  after `sanitize_pii_payload` (US-077 known gap).

## Alternatives Considered

Recorded in full in `docs/harness/decisions/0018-customer-accounts.md`:

- Keep 0017 as is, with no Customer accounts.
- Reuse `pending` as the Customer account.
- A new role name instead of `guest`.
- PostgREST writes from the Customer web with the user's JWT.
- Keep the chat tool's own labelling.
- Rewrite the two pending ex-guests to `guest`.
