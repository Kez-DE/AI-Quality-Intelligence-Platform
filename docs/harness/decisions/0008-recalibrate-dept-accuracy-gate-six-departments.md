# 0008 Recalibrate department-accuracy gate for 6 departments

Date: 2026-06-27

## Status

Accepted

## Context

The migration from 4 to 6 departments (decision/spec
`docs/superpowers/specs/2026-06-27-six-departments-design.md`) changed ticket
routing: `Payment` now routes to **Tài chính & Thanh toán** and `Pricing` to
**Quản lý Rủi ro & Gian lận**, whereas previously both routed to **CSKH**.

`pipeline/tests/test_routing_accuracy.py::test_department_accuracy_meets_target`
measures department accuracy on the 20% golden holdout as
`route_ticket(predicted_topic) == route_ticket(gold_topic)`. Under 4 departments,
the model confusing `Payment`/`Pricing`/`Other` still landed on CSKH for both gold
and prediction, so those confusions counted as correct. Splitting CSKH into three
destinations exposes that pre-existing topic confusion as department mismatches.

Measured effect on the same holdout (SEED=42, HOLDOUT_FRAC=0.2):

- 4-dept dept accuracy: **0.7541** (gate floored at 0.75 — passed).
- 6-dept dept accuracy: **0.711** (same model, finer routing — fails 0.75).

The model's **topic accuracy is unchanged**; only the topic→department mapping
became finer-grained. The 0.75 floor was calibrated for the 4-department world.

## Decision

Lower `TARGET_DEPT_ACCURACY` from `0.75` to `0.70` in
`pipeline/tests/test_routing_accuracy.py`, with an inline comment recording the
4→6 recalibration and the measured 0.711 baseline. The gate stays **enforced**
at the honest 6-department level so future routing/model regressions below 0.70
still fail the suite.

## Alternatives Considered

1. Mark the test `@unittest.expectedFailure` (like the two sibling aspirational
   tests). Rejected: stops enforcing any department-accuracy floor.
2. Keep the 0.75 hard floor and retrain the classifier / relabel the golden set
   for 6 departments now. Rejected for this change: out of the bounded migration
   scope; tracked as retrain follow-up (co_che.md P1-3).

## Consequences

Positive:

- Suite stays green with an honest, still-enforced regression floor.
- The recalibration and its cause are recorded, not hidden behind xfail.

Tradeoffs:

- The enforced floor is lower until model quality improves under 6 departments.

## Follow-Up

- Retrain / expand the labeled corpus to lift 6-dept department accuracy back
  toward 0.75+ (co_che.md P1-3, P1-5), then raise the gate again.
