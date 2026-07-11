# C2-App-116 Audit → Fix → Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Find and fix every bug in C2-App-116, verify locally with real services, ship to main (auto-deploy 6 Railway services), verify production parity.

**Architecture:** Audit funnel — cheap signals (test battery) → real flow at small volume → targeted logic read → single triage table → fix wave (TDD per fix) → re-run → review → ship → prod verify. Spec: `docs/superpowers/specs/2026-07-11-system-audit-fix-deploy-design.md`.

**Tech Stack:** Python FastAPI (`pipeline/`, venv at `pipeline/.venv`), TanStack Start + React 19 (`app/`, bun), Supabase cloud, Railway (6 services, deploy via GitHub Actions on push to main).

## Global Constraints

- Branch: `fix/audit-2026-07` (from origin/main). Merge to main only at Task 6.
- Every bug found gets fixed this run (user instruction). Non-bug improvements → `scripts/bin/harness-cli backlog add --summary "<text>"`.
- Every fix ships with a test that fails before the fix and passes after.
- Real services (Supabase cloud + LLM keys from `.env`), small volume (~30 records).
- Failure budgets: deploy fix ×1; prod-parity fix+redeploy ×1; per-fix review ×2. Exceeded → stop and report to user (in Vietnamese).
- User-facing reporting in Vietnamese; code/commits/records in English.
- Do not touch `feat/greensm-pitch-deck` branch or untracked `short/`.

---

### Task 1: Test battery

**Skills:** systematic-debugging (triage failures, no guessing)

**Files:** none modified — output is `scratchpad/audit/triage.md` (create; triage table: | # | severity | area | evidence | file:line | status |)

- [ ] Step 1: `cd pipeline && source .venv/bin/activate && python -m pytest -q` — expect ~166 pass; record any failure verbatim in triage table
- [ ] Step 2: `cd app && bunx tsc --noEmit` — expect 0 errors
- [ ] Step 3: `cd app && bun run lint 2>&1 | tail -20` — record errors (not warnings) as findings
- [ ] Step 4: `cd app && bun run test` — vitest; record failures
- [ ] Step 5: `cd app && bun run build` — expect successful build
- [ ] Step 6: Commit triage table skeleton: `git add scratchpad/audit/ && git commit -m "audit: test battery results"`

### Task 2: Real operational flow, small volume

**Skills:** webapp-testing

**Interfaces:** Produces per-stage observations appended to `scratchpad/audit/triage.md` and raw evidence in `scratchpad/audit/flow/`.

- [ ] Step 1: Boot backend: `cd pipeline && source .venv/bin/activate && python -m uvicorn main:app --host 127.0.0.1 --port 8000` (background); verify `curl -s localhost:8000/health`
- [ ] Step 2: Boot frontend: `cd app && bun run dev` (background); verify page loads at printed port
- [ ] Step 3: Ingest ~30 records from `data/demo/seed_demo_150.json` via the repo's documented ingest path (API endpoint or ingest worker one-shot — follow `docs/project/co_che.md`); save request/response evidence
- [ ] Step 4: Verify each stage against real Supabase data: PII masked (no phone/email/plate in stored text), classification labels present and plausible vs `data/taxonomy/routing_table.json`, spike/alert behavior, ticket creation rules, department report structure (3 blocks), report→task link
- [ ] Step 5: Exercise auth: login each role (admin/manager/staff/guest per `docs/project/guest-account.md`), confirm RBAC boundaries on the pages touched by the flow
- [ ] Step 6: Record every anomaly as a triage row with evidence path; commit

### Task 3: Targeted logic read of core-flow modules

**Skills:** find-bugs, variant-analysis, fastapi-pro

- [ ] Step 1: `codegraph impact` / `codegraph callers` on the entry points used by the flow (ingest endpoint, classify service, ticket workflow, report generator) to map the exact call graph
- [ ] Step 2: Read, in order: `pipeline/services/` (ticket workflow, live stream), `pipeline/worker_ticket.py`, `pipeline/worker_ingest.py`, `pipeline/worker_ml.py`, `pipeline/worker_agent.py`, `data/taxonomy/routing_table.json` + `severity_rules.json` consumers, spike detection module — hunting: off-by-one, timezone/schedule bugs, race between web-API scheduler and workers, dedup logic, error swallowing, unchecked LLM output parsing, Supabase write failures ignored
- [ ] Step 3: Each suspected logic bug → triage row with file:line + reasoning; verify each is real (write a quick repro or trace inputs) before marking confirmed; commit triage update

### Task 4: Fix wave — one TDD cycle per confirmed finding

**Skills:** test-driven-development, systematic-debugging

For EACH confirmed triage row, in severity order:

- [ ] Step 1: Write failing test in the matching suite (`pipeline/tests/test_*.py` or `app/src/**/*.test.ts*`) reproducing the bug
- [ ] Step 2: Run it, confirm FAIL for the expected reason
- [ ] Step 3: Minimal fix at root cause (grep all callers of the touched function first)
- [ ] Step 4: Run test → PASS; run the module's full test file → no regressions
- [ ] Step 5: `git add <test> <fix> && git commit -m "fix(<area>): <finding #N summary>"`; mark triage row fixed

If ≥4 confirmed findings are in disjoint files, independent fixes MAY be dispatched to parallel subagents (superpowers:dispatching-parallel-agents), each carrying this exact TDD cycle.

### Task 5: Re-run everything + code review

**Skills:** verify (Claude Code built-in), code-review:code-review

- [ ] Step 1: Repeat Task 1 battery — all green required
- [ ] Step 2: Repeat Task 2 flow (fresh ~30 records) — all stages clean
- [ ] Step 3: Invoke Skill(code-review:code-review) on `git diff origin/main...HEAD` — critical findings: one fix round (TDD cycle from Task 4); still critical → STOP, report
- [ ] Step 4: Minor review findings → `harness-cli backlog add`; commit any review fixes

### Task 6: Ship to main

**Skills:** git-pushing

- [ ] Step 1: `git checkout main && git pull origin main && git merge fix/audit-2026-07 --no-ff -m "fix: system audit 2026-07-11 — <n> bugs fixed"`
- [ ] Step 2: `git push origin main`
- [ ] Step 3: Watch deploy: `gh run watch` (workflow `.github/workflows/railway.yml`) until success; on failure → read logs, one fix round (commit to main via same TDD discipline), re-watch; still failing → STOP, report

### Task 7: Production verification on Railway

**Skills:** deployment-procedures

- [ ] Step 1: `/health` on backend public domain + frontend loads + `railway status` shows all 6 services healthy
- [ ] Step 2: Login on prod frontend (demo admin per `docs/project/guest-account.md`)
- [ ] Step 3: Run the same small E2E flow on prod (few records), capture per-stage results
- [ ] Step 4: Compare stage-by-stage with local Task 5 results — any divergence = new finding: one fix + redeploy round; still divergent → STOP, report with evidence
- [ ] Step 5: Harness records: `harness-cli story update` (create story if needed) + decision record if any architectural decision emerged; final report to user in Vietnamese

## Self-review

- Spec coverage: battery(T1)/flow(T2)/logic-read(T3)/fix-all-bugs(T4)/re-run+review(T5)/ship(T6)/prod-verify(T7) — all spec sections covered ✓
- No placeholders: audit tasks carry exact commands; fix tasks are parameterized by triage rows (inherent to audits — the failing test IS the finding's repro) ✓
- Engine: executing-plans — tasks strictly sequential, each consumes the previous task's triage state; subagent-driven would lose accumulated audit context (D5). Parallel subagents only for the bounded fix-wave case in Task 4 ✓
