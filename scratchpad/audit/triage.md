# Audit Triage — 2026-07-11

| # | Severity | Area | Finding | Evidence | Status |
|---|----------|------|---------|----------|--------|
| 1 | high | frontend tests | Smoke tests crash without cloud env: components touch real supabase client in effects; no global mock → CI/dev without VITE_SUPABASE_* cannot run tests | vitest 2 FAIL, `client.ts:18` throw via SupportChatWidget/useRealtimeNotifications/useCockpitRealtime | FIXED — global supabase mock in setupTests.ts |
| 2 | info | frontend lint | 1281 eslint errors: 1242 prettier format, 37 no-explicit-any, 9 react-refresh, 1 prefer-const, 1 ts-comment — style, not bugs | `eslint .` output | BACKLOG |
| 3 | check | frontend hooks | 5 × react-hooks/exhaustive-deps — possible stale closures, verify in Task 3 | eslint output | OPEN → T3 |

## Battery results (Task 1)

- pytest (pipeline): 194 passed, 3 skipped, 2 xfailed — GREEN
- tsc --noEmit (app): 0 errors — GREEN
- eslint (app): see #2/#3
- vitest (app): 2 FAIL → #1 → fixed, 11/11 pass
- vite build (app): success — GREEN
