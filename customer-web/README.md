# Customer web

The separate website where a **Customer** (no account) submits Feedback and
checks its **Feedback status** with a **Lookup code**. Terms follow the repo
glossary in `../CONTEXT.md`. Story: US-077, decision 0017.

It is a static Vite + React SPA with no Supabase client, no Supabase env vars
and no Staff web code. The browser calls the backend directly.

| Path | Page |
| --- | --- |
| `/` | Submit Feedback (text, channel, area) plus a "Tra cứu mã" lookup box |
| `/status/:code` | Feedback status and submitted date for one Lookup code |

Any other path redirects to `/`. The UI is Vietnamese only.

## Develop

```sh
cd customer-web
npm install
npm run dev          # http://localhost:5175
```

The backend URL comes from `VITE_BACKEND_API_URL` and defaults to
`http://127.0.0.1:8000`. For a local backend on another port, put it in
`customer-web/.env.local` (gitignored):

```sh
VITE_BACKEND_API_URL=http://127.0.0.1:8099
```

Vite reads env files from this folder only. The repo-root `.env` points at
production and is deliberately not read.

| Script | What it does |
| --- | --- |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` | vitest (API client, status labels, form) |
| `npm run build` | production build into `dist/` |
| `npm run preview` | serve `dist/` on port 5175 |

## Build and run the container

The Docker build context is this folder.

```sh
docker build --build-arg VITE_BACKEND_API_URL=https://<backend-domain> -t customer-web customer-web
docker run --rm -e PORT=8080 -p 8080:8080 customer-web
```

`VITE_BACKEND_API_URL` is baked into the bundle at build time, so changing the
backend URL needs a rebuild. The image is nginx: it renders
`nginx.conf.template` with `$PORT` and `$BACKEND_ORIGIN` at start-up (port
default 8080), serves `dist/` with an SPA fallback to `index.html`, turns
`server_tokens` off, and sends:

- `Content-Security-Policy`: `default-src 'self'; script-src 'self'`, with
  `connect-src 'self' $BACKEND_ORIGIN`. The Dockerfile sets `BACKEND_ORIGIN`
  from the same `VITE_BACKEND_API_URL` build arg the bundle uses (default
  `http://127.0.0.1:8000`), so the CSP allows exactly the backend the bundle
  calls. Styles allow `'unsafe-inline'` (sonner injects a `<style>`) and Google
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
3. Add the variable `VITE_BACKEND_API_URL` = the public backend URL. The Staff
   web relies on Railway passing service variables to the Docker build as
   build args (`app/Dockerfile`), and this Dockerfile declares the same ARG.
4. Do not set `PORT`; Railway provides it and nginx listens on it.
5. Generate a public domain. Set the Staff web's `VITE_CUSTOMER_WEB_URL` to it
   and rebuild the Staff web. Pick a domain that will not change: QR codes
   printed on vehicles will point at it.

No backend change is needed for the new origin: CORS is `allow_origins=["*"]`
today (`pipeline/main.py`). The GitHub deploy workflow does not know this
folder (path filters in `.github/workflows/railway.yml`), so pushes do not
deploy it. Adding CI for it is a backlog item.

## Contract and safety

- `src/api.ts` never sends `Authorization` and uses `credentials: "omit"`.
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
- Tests mock `fetch`. No run has gone against a live backend from a browser.
