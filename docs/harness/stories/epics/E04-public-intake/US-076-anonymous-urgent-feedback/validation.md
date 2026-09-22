# Validation

## Proof Strategy

Three claims carry this story, and each one fails loudly if broken:

1. **A stranger can write.** The submit route accepts a request with no
   `Authorization` header and produces a row with `user_id` NULL.
2. **A stranger can read only their own report, and only part of it.** The status
   route answers on an exact reference and returns no field that belongs to
   anyone else or to the platform's internals.
3. **Opening the door did not open it wider than intended.** PII is masked before
   storage, submissions are rate limited without an account to key on, and the
   authenticated path is untouched.

The third claim is the one that matters most: this story's whole risk is that an
unauthenticated route becomes a hole. Tests assert the absence of fields, not
just the presence of the happy path.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | `public_ref` is unguessable and unique across generations; client IP resolves to the rightmost `X-Forwarded-For` entry so a forged leading entry cannot move the rate-limit bucket; fingerprints differ per IP; derived status maps `reviewed` -> resolved, `needs_review` -> under_review, else received. |
| Integration | Submit with no auth header -> 200 with a reference; stored row has `user_id` None, `source='public'`, a `submitter_hash`, a `retention_until`; empty and 4001-char `text` -> 422; PII (phone, email, plate) masked in the stored text; rate limit -> 429 with `Retry-After`; separate IPs get separate buckets; status lookup by reference -> 200; unknown reference -> 404; status response omits `user_id`, `submitter_hash`, `retention_until`, `text`, `confidence` and the risk columns; classification fields are server-assigned and a client-supplied `severity` is ignored. |
| E2E | Not run. The story ships behind a public route with no session; browser proof is deferred to the next deploy window. |
| Platform | `tsc --noEmit`, `vite build`, `vitest run` for the two new routes. |
| Performance | None. The submit path performs the same single classifier call and single insert as the authenticated path. |
| Logs/Audit | Asserted by omission: no test captures a log line containing submitted text, and the endpoint contains no log statement that takes the body. |

## Fixtures

- `tests/_fakedb.FakeDB` with an empty `feedback` table — the in-memory Supabase
  double already used across the suite.
- A stub `predict_feedback` returning a fixed classification, so assertions about
  stored columns do not depend on the trained model.
- Fixed client IPs `203.0.113.10` and `203.0.113.11` (TEST-NET-3) passed as
  `X-Forwarded-For`, for deterministic fingerprint and bucket tests.
- Rate limiters are reset between tests; the limiter holds process-global state
  and would otherwise leak counts across cases.

## Commands

```text
cd pipeline && .venv/bin/python -m pytest -q
cd app && npx tsc --noEmit && npm run build && npm run test
```

## Acceptance Evidence

Run 2026-09-23, commit base `79b04ae`.

| Gate | Result |
| --- | --- |
| `pytest -q` | 287 passed, 3 skipped, 2 xfailed. 18 new in `tests/test_public_intake.py`; baseline before this story was 269, so zero regressions. |
| `tsc --noEmit` | No errors. |
| `vite build` | Built; `routeTree.gen.ts` regenerated with `/f` and `/f/status/$code`, both outside `_authenticated`. |
| `vitest run` | 16 passed (5 new in `src/lib/api.publicFetch.test.ts`; was 11). |
| `eslint` | Clean on all four touched frontend files. |

Two findings the run produced, both fixed in this story:

- `main.py`'s `HTTPException` handler dropped `exc.headers`, so every `Retry-After`
  the rate limiter set was silently discarded — a pre-existing bug affecting the
  guest feedback and chat limiters too, not just the new routes. Fixed at the
  handler, which covers all callers.
- The route-guard test first scanned `app.routes` shallowly and saw nothing.
  FastAPI nests an included router as one `_IncludedRouter` entry rather than
  flattening it, so a shallow scan misses every routed module. The test now
  recurses; a sanity assertion on `/api/users` keeps it honest.

Not yet done, and deliberately so:

- E2E against the deployed app, deferred. The database is ready and the code is
  on `main` (`4a735f8`), but nothing is serving it.

  Two separate blockers, both pre-existing and neither caused by this story:

  1. Both GitHub Actions workflows are `runs-on: self-hosted` and the repository
     has **zero** registered runners, so `Deploy to Railway` sits queued
     indefinitely. The previous run was cancelled after 24h for the same reason.
  2. The Railway `backend` service is **not running**.
     `GET https://backend-production-2f4d.up.railway.app/health` returns
     `{"status":"error","code":404,"message":"Application not found"}` from
     Railway's edge. Its last deployment (2026-09-15, commit `79b04ae`) is
     `REMOVED`; every other service's latest deployment is `FAILED`, the newest
     from 2026-06-17; `mcp-http` has never deployed at all.

  Deploying is out of scope for this story by the owner's decision. Until a
  deploy happens, `/f` has no server to answer it.

Migration applied 2026-09-23 by the repo owner via `supabase db push` against
Supabase `gvtoqbowulwmpzfogjwp`:

```text
Applying migration 20260915143000_lock_down_dispatch_rpc.sql...
Applying migration 20260923000000_public_anonymous_intake.sql...
{"upToDate":false,"dryRun":false,"migrations":[...],"message":"Finished supabase db push."}
```

The decision 0015 RPC lockdown rode along, as it was the other pending
migration. Checked safe before pushing: `grep -rn "\.rpc(" app/src` returns
nothing, so no browser code calls the function directly, and the only caller is
`pipeline/main.py:962` running under the service-role key, which keeps its
`EXECUTE` grant.
