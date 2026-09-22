# Overview

## Current Behavior

Every write into `public.feedback` requires a Supabase JWT. `POST
/api/feedback/submit` is guarded by `Depends(get_current_user)`
(`pipeline/main.py:1673`); the chat tool refuses without an identity
(`pipeline/agent/chat_tools.py:108-109`); `feedback.user_id` is `UUID NOT NULL
REFERENCES auth.users(id)`; and `anon` was revoked from the table entirely by
decision 0014.

"Guest" is an authenticated role, not an anonymous visitor: `GuestDashboard.tsx`
renders inside the `_authenticated` route tree, which redirects to `/auth`
without a session (`app/src/routes/_authenticated/route.tsx:19-23`).

An unauthenticated visitor on the landing page gets a canned local reply from
`SupportChatWidget` and no network call at all
(`app/src/components/SupportChatWidget.tsx:178-195`).

Net effect: a rider who has just had an incident must sign up, confirm an email
and log in before the platform accepts one word. Most will not, and the report is
lost to a hotline, a social post, or silence.

## Target Behavior

Opening `/f` — from a link or from a QR code in the vehicle — shows a form with
one required field. Submitting it returns a tracking reference immediately. No
account exists and none is created.

The row lands in `feedback` with `user_id` NULL, `source='public'`, a unique
`public_ref`, a salted IP hash for abuse control, and a retention stamp. It is
classified, risk-scored, spike-detected and routed by the existing pipeline with
no special case.

`/f/status/<ref>` returns that one report's progress — received, under review, or
resolved — to whoever holds the reference, and nothing else.

## Affected Users

- Anonymous reporter (xanhSM rider) — new. The only unauthenticated writer in the
  system.
- Staff / Manager — anonymous rows appear in their department queues like any
  other feedback, with no submitter account to open.
- Admin — sees the new `source='public'` value in feedback listings.

## Affected Product Docs

- `docs/project/guest-account.md` — its endpoint list and its claim that every
  guest-reachable route except `/health` needs a JWT are both now incomplete.
- `docs/project/architecture/e2e-flow.md` — the ingest flow gains a fourth source.

## Non-Goals

- Turning the anonymous reporter into an account. There is no upgrade path and no
  prompt to create one.
- Notifying the submitter. The tracking page is pull-only; nothing is sent.
- Purging expired rows. `retention_until` is recorded, not acted on.
- Any change to the authenticated submit path's behavior or contract.
