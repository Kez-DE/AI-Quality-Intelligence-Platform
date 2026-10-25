# Overview

## Current Behavior

After US-077 (decision 0017):

- A Customer has no account. The Customer web (`customer-web/`) is a static SPA
  with no Supabase client. It posts to `POST /api/public/feedback` and reads
  `GET /api/public/feedback/{public_ref}`. To see an earlier Feedback, the
  Customer must keep its Lookup code.
- There is no customer assistant. 0017 recorded this as a tradeoff.
- The role `guest` does not exist. `profiles.role` is one of `admin`, `manager`,
  `staff`, `pending`. `handle_new_user` gives every new profile `pending`, except
  the first one ever, which becomes `admin`.
- The owner was asked to turn off sign-up and the Google and Facebook providers
  in the Supabase Dashboard (`docs/project/setup-supabase.md` §8.1).
- The Staff web gate maps any non-Staff value, a leftover `guest` included, to
  `pending` and shows the waiting screen (`app/src/lib/access.ts`).
- The feedback list shows the "Khách hàng" badge on `source = 'public'` rows only.

## Target Behavior

Logged out, the Customer web works exactly as in US-077.

A Customer can sign up on `/dang-ky` (email, password meeting the same 5
criteria, full name) or log in on `/dang-nhap` with email and password, Google or
Facebook. The new account lands as `guest`: a Customer account. Forgot and reset
password work from the Customer web.

A logged-in Customer account:

- sees its email, "Phản hồi của tôi" and "Đăng xuất" in the header;
- submits through `POST /api/customer/feedback` with its token. The row gets the
  same cleaning, classifier, rules, severity and honeypot as public intake,
  `source = 'customer'`, its own `user_id`, and a Lookup code. The success screen
  still shows only the Lookup code;
- sees `/cua-toi`: its own Feedback, newest first, with status, date and text,
  each linking to `/status/:code`. Never an AI label;
- can open the chat widget. The assistant answers from the public knowledge
  base only. When it files Feedback, the row goes through the classifier like
  any other.

A logged-in account whose role is not `guest` (a Staff or Pending account) sees
"Tài khoản nhân viên dùng Staff web" on the Customer web and makes no customer
API call.

On the Staff web, a Customer account sees one screen, "Đây là tài khoản khách
hàng", with a link to the Customer web and a logout button. The backend answers
it with 403 on every Staff route. Rows with `source = 'customer'` carry the
"Khách hàng" badge, like `public` rows.

The two `pending` ex-guests stay `pending`. Admin-created Staff accounts are
unchanged.

## Affected Users

- Customer — may now sign up. Without an account, nothing changes.
- Customer account — new term: a Customer who signed up; role `guest`. Customer
  web only.
- Pending account — no longer the landing role for self sign-up. Still the
  fail-closed value, still what the two ex-guests are.
- Staff / Manager — see the "Khách hàng" badge on `customer` rows too.
- Admin — the approval queue no longer fills with self sign-ups. Keeps sign-up
  and the OAuth providers on in the Supabase Dashboard; adds the Customer web
  redirect URLs.

## Affected Product Docs

- `CONTEXT.md` — new term "Customer account"; "Customer" no longer says "has no
  account".
- `docs/project/guest-account.md` — the Customer account next to Pending.
- `docs/project/setup-supabase.md` — sign-up and providers stay on; Customer web
  redirect URLs; Dashboard-created accounts land as `guest`.
- `docs/project/data-model.md` — `profiles.role` gains `guest`; `feedback.source`
  gains `customer`.
- `customer-web/README.md` — env vars and pages (Customer web slice).
- `docs/project/architecture.md` — 5 roles, bootstrap lands as `guest`, the
  Customer web's Supabase client and `/api/customer/*`.
- `docs/project/rbac-departments.md`, `co_che.md`, `giai_thich.md`,
  `mcp-server.md`, `docs/project/README.md` — role lists and "a Customer has no
  account" prose.

## Non-Goals

- Upgrading a Customer account to a Staff account. Staff accounts are still
  created by an admin.
- Rewriting the two `pending` ex-guests.
- Redaction for `customer` rows: they carry no `retention_until` (decision
  0018 §9).
- Notifications to the Customer.
- Any RLS loosening for `guest`.
- Deploying either web.
