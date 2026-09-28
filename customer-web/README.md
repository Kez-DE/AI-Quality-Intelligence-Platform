# Customer web

The separate website where a **Customer** submits Feedback and checks its
**Feedback status** with a **Lookup code**, with no account. A Customer may
also sign up for an optional **Customer account** (role `guest`) to see their
own Feedback and use the assistant. Terms follow the repo glossary in
`../CONTEXT.md`. Stories: US-077 (decision 0017), US-078 (decision 0018).

It is a static Vite + React SPA with no Staff web code. The browser calls the
backend directly. Supabase is used for Auth only (`src/supabase.ts`); every
data read and write goes through the backend with the access token.

| Path | Page |
| --- | --- |
| `/` | Submit Feedback (text, channel, area) plus a "Tra cứu mã" lookup box |
| `/status/:code` | Feedback status and submitted date for one Lookup code |
| `/dang-nhap` | Log in: email + password, Google, Facebook |
| `/dang-ky` | Sign up: full name, email, password (same 5 criteria as the Staff web) |
| `/quen-mat-khau` | Send a password reset email |
| `/dat-lai-mat-khau` | Set a new password after the reset link |
| `/cua-toi` | "Phản hồi của tôi": own Feedback, newest first, each linking to its status |

A trailing slash is accepted; any other path redirects to `/`. A floating
assistant button sits on every page: a Customer account can chat, a logged-out
visitor is asked to log in. The UI is Vietnamese only.

Without `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` the site builds
and runs logged-out only: no header login link, no assistant button, and the
account pages say login is not enabled.

## Develop

```sh
cd customer-web
npm install
npm run dev          # http://localhost:5175
```

Env vars (all baked in at build time, all public):

| Variable | Purpose |
| --- | --- |
| `VITE_BACKEND_API_URL` | Backend base URL. Default `http://127.0.0.1:8000`. |
| `VITE_SUPABASE_URL` | Supabase project URL, for Customer account login. Optional. |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Supabase publishable (anon) key. Optional. Never the service-role key. |

Put local values in `customer-web/.env.local` (gitignored):

```sh
VITE_BACKEND_API_URL=http://127.0.0.1:8099
VITE_SUPABASE_URL=http://127.0.0.1:54321
VITE_SUPABASE_PUBLISHABLE_KEY=<local publishable key>
```

Vite reads env files from this folder only. The repo-root `.env` points at
production and is deliberately not read.

| Script | What it does |
| --- | --- |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` | vitest (API client, status labels, form, auth-aware submit, role gate, history, password criteria, routes) |
| `npm run build` | production build into `dist/` |
| `npm run preview` | serve `dist/` on port 5175 |

## Build and run the container

The Docker build context is this folder.

```sh
docker build \
  --build-arg VITE_BACKEND_API_URL=https://<backend-domain> \
  --build-arg VITE_SUPABASE_URL=https://<project-ref>.supabase.co \
  --build-arg VITE_SUPABASE_PUBLISHABLE_KEY=<publishable-key> \
  -t customer-web customer-web
docker run --rm -e PORT=8080 -p 8080:8080 customer-web
```

The three `VITE_*` values are baked into the bundle at build time, so changing
any of them needs a rebuild. The image is nginx: it renders
`nginx.conf.template` with `$PORT`, `$BACKEND_ORIGIN` and `$SUPABASE_ORIGIN` at start-up (port
default 8080), serves `dist/` with an SPA fallback to `index.html`, turns
`server_tokens` off, and sends:

- `Content-Security-Policy`: `default-src 'self'; script-src 'self'`, with
  `connect-src 'self' $BACKEND_ORIGIN $SUPABASE_ORIGIN`. The Dockerfile sets
  `BACKEND_ORIGIN` from the same `VITE_BACKEND_API_URL` build arg the bundle
  uses (default `http://127.0.0.1:8000`) and `SUPABASE_ORIGIN` from
  `VITE_SUPABASE_URL` (default empty), so the CSP allows exactly the backend
  and the Supabase Auth URL the bundle calls. OAuth and email links are
  top-level navigations, which `connect-src` does not govern. Styles allow `'unsafe-inline'` (sonner injects a `<style>`) and Google
  Fonts; `frame-ancestors 'none'`, `base-uri 'none'`, `form-action 'self'`.
- `Strict-Transport-Security: max-age=31536000`.
- `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff` and
  `X-Frame-Options: DENY`.

## Railway service (not set up yet)

These steps are documented only; nothing here has been run. Deploying waits on
backlog #7 (no CI runner, no live Railway deployment).

1. Create a new service, for example `customer-web`, from this repo.
2. Set its Root Directory to `customer-web` so the build context and
   `Dockerfile` are this folder. The repo-root `railway.json` is shared by every
   service, so confirm in the dashboard that this service builds with its
   Dockerfile.
3. Add the variables `VITE_BACKEND_API_URL` = the public backend URL, and
   `VITE_SUPABASE_URL` + `VITE_SUPABASE_PUBLISHABLE_KEY` = the same values the
   Staff web uses. The Staff web relies on Railway passing service variables
   to the Docker build as build args (`app/Dockerfile`), and this Dockerfile
   declares the same ARGs.
4. Do not set `PORT`; Railway provides it and nginx listens on it.
5. Generate a public domain. Set the Staff web's `VITE_CUSTOMER_WEB_URL` to it
   and rebuild the Staff web. Pick a domain that will not change: QR codes
   printed on vehicles will point at it.

No backend change is needed for the new origin: CORS is `allow_origins=["*"]`
today (`pipeline/main.py`). The GitHub deploy workflow does not know this
folder (path filters in `.github/workflows/railway.yml`), so pushes do not
deploy it. Adding CI for it is a backlog item.

## Supabase Auth settings

Customer accounts need these in the Supabase dashboard (Authentication → URL
Configuration → Redirect URLs), or in `supabase/config.toml`
`additional_redirect_urls` for a local stack:

- `http://localhost:5175/**` (local dev and `npm run preview`)
- `https://<customer-web-domain>/**` (the production domain from step 5 above)

The app sends Supabase back to `${origin}/` after Google/Facebook login and
sign-up confirmation, and to `${origin}/dat-lai-mat-khau` after a reset email;
a redirect URL that is not allowed falls back to the Site URL (the Staff web).
Google and Facebook must be enabled as providers for their buttons to work.
Whether sign-up needs email confirmation is a project setting; the sign-up page
handles both (no session yet → "Kiểm tra email").

A new sign-up gets role `guest` from the `handle_new_user` trigger (migration
`20260928000000_customer_accounts.sql`); this app never sets a role.

## Contract and safety

- `src/api.ts` uses `credentials: "omit"` everywhere. The public routes never
  get `Authorization`; only `/api/me` and `/api/customer/*` get the Supabase
  access token as `Bearer`.
- A session is not a Customer account: `src/auth.tsx` reads the role from
  `/api/me`. Only role `guest` calls `/api/customer/*` (feedback, history,
  chat). Any other role (staff, pending, …) sees "Tài khoản nhân viên dùng
  Staff web", submits through the public route, and makes no customer calls.
  While the role is being checked, the submit button waits.
- The history list reads only `public_ref`, `status`, `created_at` and `text`;
  any other field is dropped in `listMyFeedback`. Chat replies render as plain
  text, never HTML.
- `src/password.ts` is a copy of `app/src/lib/password.ts` (the 5 criteria).
- Do not put a proxy or server function in front of the API: the public rate
  limit keys on the client IP, so a proxy would put every Customer into one
  bucket.
- The form posts `{ text, channel, area, website }`. `website` is a honeypot:
  an off-screen, `tabIndex=-1`, `autocomplete="off"` input that people leave
  empty. The backend rejects a non-empty value with 400.
- HTTP errors map to Vietnamese copy by status (400/422, 404, 429 with the
  `Retry-After` wait, 5xx, network, timeout), because some backend messages
  are English.
- The success state shows only the Lookup code (copy button) and a link to its
  status page. AI labels (topic, sentiment, severity) are never shown.
- Status labels: `received` → "Đã tiếp nhận", `under_review` → "Đang xem xét",
  `reviewed` → "Đã xem xét". Any other value shows "Đang cập nhật". A 404
  (unknown, expired or redacted code) shows a not-found message.
- One `<Toaster/>` is mounted in `App.tsx`. Submit, 429 and network errors use
  toasts; empty text uses an inline error summary plus a field error.
- `src/regions.ts` is a copy of `app/src/lib/regions.ts`, which mirrors
  `pipeline/regions.py`. Keep all three in sync.

## Design decisions

The UI was built with the `impeccable` skill, run non-interactively because the
direction was already settled (SPEC item 4). These are the choices the skill
would normally ask about:

- **Mode: Operate.** The Customer is completing a task, not being persuaded.
- **Established world, new surface.** The brand is the Staff web's
  (`app/src/styles.css`, US-UI-01): the cyan/teal tokens, radius, shadows, the
  mint mesh ground and aurora-bordered cards. Only the page structure was new.
- **Structure.** The skill's concept seed (key `33b3add2`, surface scope)
  dealt positions 7, 4 and 5 of a ranked list of structures, with 7 leading.
  The lead was built: a plain public-service form (question headings, hints
  under labels, an error summary that links to the field, a confirmation
  panel carrying one reference, and a summary list on the status page). This is
  the opposite of the cockpit: one column, no sidebar, no stats. The two
  alternates not built were a one-question-per-screen wizard (#4) and a
  segmented "Gửi | Tra cứu" switcher (#5). Disclosure: the ranked list was
  written down after the seed script printed its indices, not before.
- **Build path: code-led.** No image generation was available, so no comps.
- **Fonts kept from the brand** (Space Grotesk headings, Inter body, JetBrains
  Mono only for the Lookup code) although the skill lists the first two as
  overused defaults. The brief pins the Staff web identity.
- **Light and dark** follow `prefers-color-scheme`, using the Staff web's dark
  tokens. The Customer web has no settings to toggle a `.dark` class.
- **Token changes, all in `src/styles.css`:** `--muted-foreground` darkened
  (L 0.50 → 0.47) and `--destructive` (0.62 → 0.55) for 4.5:1 text contrast;
  `--input` darkened (0.92 → 0.80) so field borders reach 3:1. New tokens:
  `--primary-strong` (a cyan dark enough for icons and links on white),
  `--band` (the header strip and confirmation panel, from the hero gradient's
  dark stops), and one ink per status tag.
- **Aurora cards without the hover lift.** They hold forms, and a form should
  not move under the pointer.
- **Area is optional** ("Chọn khu vực", sent as an empty string, which the
  backend stores as NULL). The old `/f` form preselected Cầu Giấy, which
  silently attributed unchanged reports to one district. Channel keeps the old
  default ("Ứng dụng") and the same four values.
- **The Lookup code is shown in groups of four** (spacing in CSS only, so
  copying still gives the exact code). The lookup box strips spaces.
- **One authored motion:** the answer (confirmation panel, status result)
  sharpens in; `prefers-reduced-motion` turns it and the aurora spin off.
- **Review.** The skill's finish review ran inline because no subagent tool
  was available. Its two fixes (a mesh seam from `background-attachment: fixed`,
  and the textarea resize grip drawing outside the rounded corner) were applied
  and verified in the recapture. No `DESIGN.md` was written: it would belong
  at the repo root, outside this workstream, and the Staff web has none yet.
  `PRODUCT.md` in this folder holds the inferred product facts the skill needs.

## Dependency notes

- `@supabase/supabase-js` is `^2` like the Staff web (`app/package.json`),
  used for Auth only.
- `vite` is pinned to `7.3.5` (the Staff web's version) and `overrides` forces
  every Vite in the tree to it. Without that, npm 10 resolves vitest's optional
  `vite` peer to Vite 8 and crashes (`Cannot read properties of null (reading
  'edgesOut')`).
- `vitest` is `^4.1.11`, which fixes the `@vitest/mocker` advisory
  GHSA-82fw-gwwq-j7x9.
- `npm audit` still reports one low advisory (esbuild GHSA-g7r4-m6w7-qqqr, the
  Windows dev server only). Vite 7.3.5 cannot take the fixed esbuild, and the
  production image serves static files with nginx.

## Known limitations

- Fonts load from Google Fonts, a third party, as on the Staff web.
  `no-referrer` keeps the status URL out of those requests.
- The Lookup code travels in the URL path. It can end up in browser history and
  screenshots, like any bearer link.
- Tests mock `fetch` and the Supabase client. No run has gone against a live
  backend or Supabase project from a browser, so the OAuth, confirmation and
  reset redirects are untested end to end.
- If `/api/me` fails, the header still shows the email and logout, but the
  account is treated as logged out for submit; a reload retries.
