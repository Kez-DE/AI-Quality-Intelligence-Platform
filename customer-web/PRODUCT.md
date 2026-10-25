# Product

<!-- impeccable:product-schema 1 -->

Scope: the Customer web only (child app of the AI Quality Intelligence Platform).
Every fact below is inferred from SPEC US-077 / decision 0017, the repo glossary
(`../CONTEXT.md`) and the US-076 code it replaces. No interview round ran: the
build was delegated non-interactively and the direction was settled upstream.

## Platform

web

## Users

A Customer: a xanhSM rider outside the company, with no account, usually on a
phone right after a ride or an incident, often reaching the page by scanning a
QR code on the vehicle. (inferred)

## Product Purpose

Let a Customer report Feedback in under a minute without an account, receive a
Lookup code, and later check its Feedback status with that code. Success: the
report is stored and the Customer leaves holding the code. (inferred)

## Positioning

No account, no login, no identity: the Lookup code is the only way back to a
report. Personal data typed into the text is masked server-side before storage,
and the text is redacted after 180 days. (from SPEC items 5-8, 15-16)

## Operating Context

Outdoors or in a vehicle, one hand, mobile data, possibly stressed. The page is
the whole interaction; there is no follow-up email or SMS. (inferred)

## Capabilities and Constraints

- Two pages only: submit Feedback (`/`) with a small lookup box, and Feedback
  status (`/status/:code`). Vietnamese only.
- The browser calls the backend directly; no proxy (rate limit keys on client IP).
- Never show AI labels (topic, sentiment, severity). Status page shows only the
  Feedback status and the submitted date.
- Feedback status values: received "Đã tiếp nhận", under_review "Đang xem xét",
  reviewed "Đã xem xét". Reviewed means staff checked the classification, not
  that the problem is fixed.

## Brand Commitments

Same visual identity as the Staff web (product name on this site: AI-Quality), the cyan/teal token palette,
radius, shadows and aurora cards from `app/src/styles.css` (US-UI-01). It must
not look like the internal cockpit. (SPEC item 4)

## Evidence on Hand

No customer testimonials, statistics or response-time commitments exist. Do not
invent them.

## Accessibility & Inclusion

Mobile-first touch targets, readable in daylight, keyboard and screen-reader
usable form, reduced-motion respected. (inferred)
