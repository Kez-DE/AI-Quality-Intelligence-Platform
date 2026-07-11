# System Audit → Fix → Deploy → Prod Verify (2026-07-11)

Harness intake #5, lane: high-risk. Requested by user via /start.

## Understanding

Audit C2-App-116 end-to-end, fix all bugs found, verify locally with real
services, ship to main (auto-deploys 6 Railway services via GitHub Actions),
then verify production parity against local results.

## Decisions

- Work on `fix/audit-2026-07` branched from `origin/main`; merge to main
  locally and push (no PR). Pitch-deck branch and untracked `short/` untouched.
- Scope: full existing test battery + core operational flow
  (ingest → PII → classify → spike → ticket → report → task) exercised with
  real Supabase + real LLM keys at small volume (~30 records from
  `data/demo/seed_demo_150.json`). Other areas (chat RAG, agents detail, MCP,
  frontend UI) audited only on signal.
- Targeted logic read of core-flow modules (`services/`, `worker_*.py`,
  `data/taxonomy/*.json`, spike detection), codegraph-guided.
- **Every bug found is fixed in this run** (user instruction), regardless of
  area. Only non-bug improvements/style go to `harness-cli backlog add`.
- Each fix ships with a proving test. After the fix wave: full battery +
  real-flow re-run + `/code-review` on the whole diff (critical findings get
  one fix round).
- Ship: commit → merge main → push → watch GitHub Actions deploy.
- Prod verify: `/health` on all 6 services + frontend load + login + one small
  real E2E flow on prod, compared stage-by-stage with local results.
- Failure budgets (stop-and-report when exceeded): deploy fix ×1,
  prod-parity fix+redeploy ×1, per-task review fix ×2.
- Commit + push + deploy are pre-authorized by the user's request and
  re-confirmed at plan approval.

## Audit funnel (approach A — cheap signals first)

1. Battery: pytest (pipeline), tsc + eslint + vite build (app)
2. Boot local services, run real flow at small volume, log anomalies per stage
3. Targeted logic read of core-flow modules
4. Single triage table → fix wave → re-run battery + flow → review → ship →
   prod verify

## Alternatives rejected

- Code-audit-first (slow, theoretical findings before real signal)
- Test-expansion-first (slowest; LLM-dependent E2E tests are flaky)
