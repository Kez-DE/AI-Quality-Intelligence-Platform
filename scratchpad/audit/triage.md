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

## Task 2 — Real flow results (30 records, real Supabase + LLM)

- Ingest: 30/30 inserted, 0 failed (offset 900) — GREEN
- PII: no phone/email/plate leaked in stored text — GREEN
- Classification: all rows have topic/severity/area/confidence in range; P5⇒needs_review consistent — GREEN
- Spike detect: 30 records/24 groups → 0 spikes (correct for diverse small batch; thresholds reviewed in T3)
- Report (CSKH, real LLM): stored, 8 sections incl. Vấn đề/Phân tích/Đề xuất — GREEN
- Approve-and-dispatch: 2 tasks, report_id backlink, due_at=deadline 24h, double-approve 409, no-auth 401 — GREEN
- RBAC matrix (guest/staff/manager/admin): 6/6 PASS
- Frontend dev server: loads HTTP 200

## Task 3 — Confirmed logic bugs (fix wave)

| # | Sev | File | Bug |
|---|-----|------|-----|
| 4 | HIGH | worker_agent.py:59 | Report cron hour=9,14 uses container-local tz — Railway UTC fires 16:00/21:00 VN (local GMT+7 correct) → prod≠local |
| 5 | HIGH | worker_ml.py:48 + scoring_agent fallback | LLM-fail rows keep overall_risk NULL → re-fetched every 30s forever (LLM cost burn, queue blocked) |
| 6 | HIGH | worker_ml.py:28 | SELECT lacks needs_review → scoring writes False, wiping ingest's HITL flag (P5/safety) |
| 7 | HIGH | ingest.py:116 | pops overall_risk before insert though column exists → ml-worker re-scores every negative via LLM (double cost); evidence: 3 neg rows severity=P1 (scored) but overall_risk NULL |
| 8 | MED | ingest.py:179 | batch-insert failure: payload_batch not cleared (poison batch cascades), failed_count counts 1 instead of batch size |
| 8b | MED | ingest.py:101-111 | LLM cache stores fabricated overall_risk=3/severity P3 for failed-scoring items |

Non-bugs → backlog: calculate_overall_risk dead condition (fraud>=8 subsumed) + comment drift; _llm_cache unbounded; 5 exhaustive-deps warnings are intentional patterns.
