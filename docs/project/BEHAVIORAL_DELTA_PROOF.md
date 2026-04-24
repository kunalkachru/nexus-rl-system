# Criterion 4 Behavioral Delta Proof

This sheet demonstrates BRD §18.2 Criterion 4 intent: measurable improvement in **how the agent acts**, not only reward numbers.

## Fixed evaluation set (canonical)

- Environment URL: `https://kunalkachru23-nexus-enhanced-stage.hf.space`
- Incidents:
  - `INC003` (memory leak, red herrings, runbook discipline)
  - `INC008` (personalized delegation conflict)
  - `INC006` (hard multi-region coordination)
- Evidence channels:
  - `POST /demo/run/INC003`
  - Dashboard manual validation (`/web`) for `INC008` and hard-case progression
  - Aggregate metrics snapshot (`/metrics`, `/learning-curve`)
  - Frozen submission snapshot: `submission_snapshot_20260424T164826Z.md`

## Baseline -> trained behavior shift

### Baseline-style pattern (pre-training benchmark)

- Generic, low-commitment hypotheses in early phases.
- Delayed customer-impact communication in service-affecting incidents.
- More repeated / low-information tool calls.
- Higher chance of stalling in triage/investigation without decisive runbook progression.

### Trained pattern (post-training observed)

- Earlier and more explicit root-cause commitment in `INC003`.
- Cleaner sequencing: detection -> triage -> investigation -> mitigation -> resolution -> postmortem.
- Better specialist orchestration (L2/SRE/PM directives are more goal-directed).
- Stronger consistency on customer-facing notification/escalation behavior.
- Fewer redundant actions and faster progression out of investigation.

## Quantitative deltas (frozen)

From `docs/project/snapshots/submission_snapshot_20260424T164826Z.md`:

- Baseline reward: `0.265`
- Trained average reward: `0.4634`
- Best reward: `1.0032`
- Improvement vs baseline: `+74.9%`

From `docs/project/snapshots/component_metrics_20260424T164826Z.md`:

- Latest diagnosis signal: `0.1340`
- Latest coordination signal: `0.0804`
- Latest customer signal: `0.1072`

These support that gain is not only speed; diagnosis/coordination/customer dimensions also move.

## Live checks judges can run

1. `POST /demo/run/INC003`:
   - verify full phase progression and final reward breakdown.
2. Manual tab (`/web`) on `INC008`:
   - run guided/manual steps to verify delegation/conflict behavior.
3. Compare metrics endpoints:
   - `GET /metrics`
   - `GET /learning-curve`
   - confirm aggregate improvement trend and rolling average.

## Why this satisfies Criterion 4

Criterion 4 asks for coherent reward logic and meaningful pipeline-driven behavior change.
NEXUS evidence shows:

- Coherent multi-dimensional reward decomposition (MTTR, diagnosis, customer, coordination, oversight, depth).
- Consistent post-training behavioral improvements in sequencing, coordination, and completion outcomes, aligned with reward gains.
