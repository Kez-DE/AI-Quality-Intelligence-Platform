# Exec Plan

## Goal

A xanhSM rider with an urgent problem can file it from a phone in seconds — no
account, no login — and the report enters the existing classification, routing
and HITL pipeline unchanged.

## Scope

In scope:

- `feedback.user_id` becomes nullable; anonymous rows identified by `public_ref`.
- `POST /api/public/feedback` — unauthenticated submit.
- `GET /api/public/feedback/{public_ref}` — unauthenticated status read-back.
- IP-fingerprint rate limiting for both public routes.
- PII masking and a retention stamp on every anonymous row.
- Public frontend routes `/f` (form) and `/f/status/$code` (lookup).

Out of scope:

- Deleting rows past `retention_until` (column is recorded, no purge job).
- Captcha / Turnstile.
- Email or SMS notification of the submitter.
- QR image generation — a QR encodes the `/f` URL and needs no backend.
- Changing anything about the authenticated `POST /api/feedback/submit` path.

## Risk Classification

Risk flags:

- Auth — a route that deliberately has no authentication.
- Authorization — `public_ref` possession becomes a read credential.
- Data model — `user_id` loses `NOT NULL`; three columns added.
- Audit/security — unsolicited free text from the open internet, treated as PII.
- Public contracts — two new client-visible routes.
- External systems — the open internet is now an ingest source; abuse surface.

Hard gates: Auth, Data model, Audit/security. Lane is high-risk.

## Work Phases

1. Discovery — map every existing write path and its guard; confirm `anon` has no
   table privilege and `user_id` is `NOT NULL` with `ON DELETE CASCADE`.
2. Design — choose the identity model against three alternatives; record
   decision `0016`.
3. Validation planning — enumerate the cases below before writing the endpoint.
4. Implementation — migration, `pipeline/public_intake.py`, router mount, public
   frontend routes.
5. Verification — pytest, tsc, vite build, vitest.
6. Harness update — story and decision rows in `harness.db`.

## Stop Conditions

Pause for human confirmation if:

- The migration would need to rewrite or drop existing `feedback` rows.
- RLS would need a new policy granting `anon` any privilege on a table.
- Rate limiting has to be removed to make a test pass.
- The public route would return any field belonging to another submitter.
