# Design

## Domain Model

**Feedback** gains an identity invariant it never had to state before, because
until now there was only one way to hold one.

> A feedback row is attributable in exactly one of two ways: it belongs to an
> **account** (`user_id`), or it carries a **public reference** (`public_ref`).
> Never neither.

Enforced in the database as `CHECK (user_id IS NOT NULL OR public_ref IS NOT NULL)`,
not in application code, because three separate writers (API, workers, dataset
ingest) can insert into this table and only the constraint covers all of them.

New terms:

- **Public reference** — an unguessable 72-bit token, the sole credential for
  reading an anonymous report's status. A bearer token, not an identifier: it is
  never displayed to ops staff as a searchable key and never logged.
- **Submitter fingerprint** — salted SHA-256 of the client IP. Exists only so
  abuse control has something to count. It is not an identity: two reporters
  behind one NAT share a fingerprint and the system is content with that.
- **Retention deadline** — the date past which an anonymous row's personal text
  has no reason to exist.

`source='public'` joins `manual`, `chat` and `app_store`. It means "arrived
without an account", which is a different fact from `channel`, the medium the
reporter says they were using.

## Application Flow

Submit — `POST /api/public/feedback`:

```
request
  -> fingerprint(client ip)              salted sha256, never stored raw
  -> rate limit check (fingerprint)      429 + Retry-After when exceeded
  -> pydantic validation                 text 1..4000 chars, 422 otherwise
  -> clean_text()                        masks phone / email / plate
  -> predict_feedback()                  topic, sentiment, severity, confidence
  -> insert feedback                     user_id NULL, source 'public',
                                         public_ref, submitter_hash,
                                         retention_until
  -> 200 { public_ref, status, created_at }
```

Status — `GET /api/public/feedback/{public_ref}`:

```
request
  -> rate limit check (fingerprint)      guards reference enumeration
  -> select by public_ref                exact match, limit 1
  -> 404 when absent                     same shape for "never existed" and
                                         "expired", so the endpoint is not an
                                         oracle for which references are real
  -> 200 { public_ref, status, created_at, topic, severity }
```

Downstream is unchanged. `scoring_agent`, `spike_detector`, `router_agent`,
`ticket_agent` and the HITL loop read the same columns they always did; none of
them reads `user_id`.

## Interface Contract

`POST /api/public/feedback` — no `Authorization` header, none read.

| | |
| --- | --- |
| Body | `{ "text": string (1..4000), "channel"?: string (<=40), "area"?: string (<=80) }` |
| 200 | `{ "status": "success", "data": { "public_ref": string, "status": "received", "created_at": string } }` |
| 422 | Body fails validation (empty or oversized `text`). |
| 429 | Rate limit exceeded; `Retry-After` header in seconds. |
| 503 | Database unreachable. |

`GET /api/public/feedback/{public_ref}` — no `Authorization` header.

| | |
| --- | --- |
| 200 | `{ "status": "success", "data": { "public_ref", "status", "created_at", "topic", "severity" } }` |
| 404 | No report for this reference. |
| 429 | Rate limit exceeded. |

`status` is derived, never stored: `resolved` when `reviewed`, `under_review`
when `needs_review`, otherwise `received`.

Deliberately absent from both responses: `user_id`, `submitter_hash`,
`retention_until`, `confidence`, `review_reason`, the five risk dimensions,
`overall_risk`, and the submitted `text` itself. A reference that leaks must not
hand over the report body or any internal scoring.

## Data Model

Migration `supabase/migrations/20260923000000_public_anonymous_intake.sql`:

| Change | Reason |
| --- | --- |
| `user_id` drops `NOT NULL` | An anonymous row has no account. |
| `+ public_ref TEXT` | Tracking reference. |
| `+ submitter_hash TEXT` | Abuse control key. |
| `+ retention_until TIMESTAMPTZ` | PII retention deadline. |
| `+ CHECK feedback_identity_chk` | The identity invariant above. |
| `+ UNIQUE INDEX feedback_public_ref_idx ... WHERE public_ref IS NOT NULL` | Reference uniqueness; partial so existing rows cost nothing. |
| `+ INDEX feedback_submitter_hash_idx ... WHERE submitter_hash IS NOT NULL` | Abuse investigation by fingerprint. |

Forward-only. Every existing row has a non-NULL `user_id`, so the CHECK is
satisfied on creation and no backfill runs.

RLS is untouched. The `SELECT` policy from `20260612120000_rbac_roles.sql` is
`auth.uid() = user_id OR public.is_ops_staff()`; with `user_id IS NULL` the left
side evaluates to NULL, never true, so anonymous rows are ops-only by
construction. `anon` keeps zero privileges — the public endpoints write with the
service-role key like every other ingest path, never from the browser.

Retention: `retention_until` is set to `now() + 180 days` on anonymous rows only.
No job reads it yet; that is follow-up work recorded in decision 0016.

## UI / Platform Impact

Two new public routes outside the `_authenticated` tree:

- `/f` — the form. One required textarea, optional channel and area. On success
  it shows the reference and a link to its status page. Deliberately not wired to
  `apiFetch`, which attaches a Supabase bearer token when a session happens to
  exist; `publicFetch` sends none, so the route behaves identically for a
  logged-in staff member and a stranger.
- `/f/status/$code` — the lookup.

A QR code is the `/f` URL and needs nothing from the backend.

No change to the authenticated app. `GuestDashboard`, `SupportChatWidget` and
`POST /api/feedback/submit` keep their current behavior.

## Observability

- The request body is never logged. A submission failure logs the exception type
  and the reference, not the text.
- `submitter_hash` is the only handle for investigating a burst, and it is
  reversible only by someone holding the salt.
- Anonymous rows are countable as `source='public'`, so intake volume through the
  public surface is a plain query rather than a new metric.
- 429s surface through the existing FastAPI access log with the route path; the
  fingerprint is not written to logs.

## Alternatives Considered

Recorded in full in `docs/harness/decisions/0016-anonymous-public-feedback-intake.md`:
Supabase anonymous sign-in (rejected — `ON DELETE CASCADE` data-loss trap plus a
dashboard toggle no code can assert), a single shared anonymous account (rejected
— collapses the RLS `SELECT` policy into a cross-reader hole), nullable `user_id`
with no reference (rejected — no read-back, nothing to rate-limit on), and
email-to-ticket (rejected for this story — external provider gate, slower than a
QR code in the vehicle).
