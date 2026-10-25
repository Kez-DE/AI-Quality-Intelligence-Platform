# 0016 Anonymous public feedback intake

Date: 2026-09-23

## Status

Accepted. Superseded in part by decision 0017 (2026-09-27), which moves the
public routes out of the Staff web into a separate Customer web, cuts the status
response to `public_ref`, `status` and `created_at`, renames `resolved` to
`reviewed`, and turns the retention follow-up into daily redaction.

## Context

A xanhSM rider who has just had an incident (unsafe driving, a hostile driver, a
broken vehicle) needs to report it in seconds, from the street, on a phone. Every
write path into `public.feedback` today requires a Supabase JWT:

- `POST /api/feedback/submit` and the chat tool `submit_feedback` both run behind
  `Depends(get_current_user)` (`pipeline/main.py:1673`, `pipeline/agent/chat_tools.py:108`).
- `feedback.user_id` is `UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE`
  (`supabase/migrations/20260606100321_*.sql:20`), so a row cannot exist without an
  account.
- `anon` holds no privilege on the table at all after decision 0014
  (`supabase/migrations/20260827034856_dispatch_hardening.sql:110-115`).
- The landing page widget answers unauthenticated visitors from a canned local
  reply and never calls the backend (`app/src/components/SupportChatWidget.tsx:178-195`).

"Guest" in this codebase means an authenticated account whose `profiles.role` is
`guest`, rendered inside the `_authenticated` route tree. It is not an anonymous
visitor. The urgent reporter is therefore forced through signup, email
confirmation and login before the platform will accept a single word — at exactly
the moment they are least willing to do it. The incident goes to a hotline, a
social post, or nowhere, and the pipeline never sees it.

## Decision

Open one unauthenticated intake surface and make anonymity a first-class state of
a feedback row.

1. `feedback.user_id` becomes nullable. A row carries an identity in exactly one
   of two ways, enforced by a CHECK constraint: an account (`user_id`) or a
   public tracking reference (`public_ref`).
2. Two public routes, no `Depends(get_current_user)`:
   `POST /api/public/feedback` and `GET /api/public/feedback/{public_ref}`.
   Both live in `pipeline/public_intake.py`, mounted as a router, so the public
   contract is one small reviewable file rather than two more endpoints inside
   `main.py`.
3. Anonymous rows are written with `source='public'` and an unguessable
   `public_ref` (72 bits from `secrets.token_urlsafe`). The reference is the only
   credential for reading back status; possession of it is the authorization.
4. Abuse control keys on a salted SHA-256 of the client IP (`submitter_hash`),
   because there is no `user.id` to key on. The client IP is the rightmost entry
   of `X-Forwarded-For` — Railway's edge appends the address it actually saw, so
   a forged leading entry cannot move the bucket.
5. Submitted text is treated as PII: `clean_text()` masks phone, email and plate
   before storage, the raw body is never logged, and every anonymous row carries
   `retention_until`.
6. Classification stays server-side. An anonymous submitter supplies text,
   channel and area, never topic, sentiment or severity — the same rule as the
   authenticated path.

RLS needs no new policy. The existing `SELECT` policy is
`auth.uid() = user_id OR public.is_ops_staff()`; with `user_id IS NULL` the first
term is NULL, never true, so anonymous rows are readable only by ops staff. `anon`
stays fully revoked and never touches the table — the backend writes with the
service-role key, as every other ingest path does.

## Alternatives Considered

1. **Supabase anonymous sign-in.** Keeps `user_id NOT NULL` and every existing
   policy untouched, and the login is invisible to the user. Rejected on two
   counts. The FK is `ON DELETE CASCADE`, so the inevitable cleanup job for
   accumulated anonymous accounts would silently delete the feedback attached to
   them — a data-loss trap aimed straight at the rows this story exists to
   capture. It also depends on a toggle in the Supabase dashboard that no code in
   this repo can assert, verify, or restore after decision 0013's project move.
2. **One shared "anonymous" account.** All public rows carry a single `user_id`.
   Rejected: the `SELECT` policy is `auth.uid() = user_id`, so any holder of that
   account's session reads every anonymous report ever filed — a cross-tenant
   read hole dressed as a shortcut.
3. **Drop the identity requirement entirely** (nullable `user_id`, no
   `public_ref`). Rejected: it satisfies the intake half of the problem and
   abandons the other half. The reporter gets no way back to their own report,
   and rate limiting has nothing to key on.
4. **Email-to-ticket.** No new public HTTP surface at all. Rejected for this
   story: it adds an external provider dependency (a hard gate of its own) and
   is slower for the rider than a QR code already printed in the vehicle.

## Consequences

Positive:

- An urgent report costs one page load and one paragraph. No account, no
  confirmation email, no app install.
- QR codes in vehicles and at hubs resolve to the same route as the public link,
  so the physical surface needs no separate backend.
- Anonymous reports enter the identical classifier, rule, risk-scoring, spike and
  routing pipeline as authenticated ones; nothing downstream learns a new case.
- `retention_until` gives the platform a defensible answer about how long
  unsolicited personal text is kept.

Tradeoffs:

- `user_id` is nullable, so every future reader of `feedback` must handle the
  NULL case. The CHECK constraint makes the invariant explicit rather than
  implied.
- IP-keyed rate limiting is coarse: a corporate NAT or a shared 4G gateway shares
  one bucket. The limit is set high enough for a household, low enough to make
  bulk submission tedious.
- The limiter is in-memory and per-process (`pipeline/rate_limiter.py:59`), so
  the effective ceiling scales with replica count. This is a pre-existing
  property of the limiter, now reachable without an account.
- Possession of a `public_ref` is full authorization to read that report's status.
  It is unguessable, but it is a bearer token in a URL: it will end up in browser
  history and in screenshots.

## Follow-Up

- A scheduled job to purge rows past `retention_until`. Nothing deletes them yet;
  the column records intent and today is only read by humans.
- Redis-backed rate limiting if the public surface is ever served by more than
  one replica and the per-process ceiling stops being acceptable.
- Turnstile or an equivalent challenge if the rate limiter alone proves
  insufficient in production.
