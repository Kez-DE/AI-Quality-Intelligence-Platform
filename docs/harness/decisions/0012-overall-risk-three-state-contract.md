# 0012 — overall_risk three-state contract

- **Date:** 2026-07-11
- **Status:** accepted
- **Context:** Audit 2026-07-11 found the LLM-failure fallback left
  `feedback.overall_risk` NULL, so ml-worker refetched the same rows every
  30s forever (LLM cost burn, queue blocked). Separately, ingest popped
  `overall_risk` before insert, forcing ml-worker to re-score every negative
  a second time (double LLM cost).
- **Decision:** `overall_risk` has exactly three states, and every consumer
  must honor them:
  - `NULL` — never queued for scoring (ml-worker picks these up)
  - `0` — scoring attempted and failed; `needs_review=true`; a human decides.
    Never counted as a real score, never rescored to P1 by maintenance jobs.
  - `1–5` — scored (Waterfall output)
  Ingest now persists `overall_risk` (no pop); the LLM cache never memoizes
  failed scorings.
- **Consumers aligned:** `spike_detector._severity_number`,
  `main._feedback_team`, `main.cockpit_overview` risk_distribution,
  `rescore_overall_risk.rescore_feedback`.
- **Alternatives considered:** retry-forever (cost burn, rejected);
  retry-count column (schema change for little gain, rejected).
- **Proof:** `pipeline/tests/test_worker_ml.py`,
  `tests/test_rescore_sentinel.py`, `tests/test_cockpit_overview.py`
  (sentinel case), `tests/test_ingest.py` (persist + cache cases).
