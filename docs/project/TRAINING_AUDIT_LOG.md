# Training Audit Log

Purpose: maintain a concise, judge-readable ledger showing what changed, why it changed, and what behavior moved.

## Logging policy

- One row per meaningful run or snapshot window.
- Include both scalar outcomes and behavior observations.
- Keep references to reproducible artifacts (snapshot files, endpoints, scripts).

## Run ledger

| UTC timestamp | Run type | Config note | Reward evidence | Behavior evidence | Risks/notes | Artifact |
|---|---|---|---|---|---|---|
| 2026-04-22T13:58:09Z | Stage snapshot | Canonical stage snapshot for pitch | Episodes 120, avg 0.4063, best 0.9484, +53.3% vs baseline 0.265 | INC003 auto-demo reaches postmortem with structured progression | Metric drift possible if new episodes are appended | `docs/project/snapshots/submission_snapshot_20260422T140018Z.md` |
| 2026-04-22T14:00:18Z | Submission freeze snapshot | Timestamped export before winner-boost docs finalization | Snapshot JSON+MD generated from `/metrics` + `/learning-curve` | Manual and auto-demo references aligned in pitch docs | Ensure future pitch cites refreshed values only after intentional update | `docs/project/snapshots/submission_snapshot_20260422T140018Z.json` |
| 2026-04-22T17:08:24Z | Component metrics freeze | Added component-level export script and captured latest stage values | Avg 0.4063, baseline 0.265, +53.3%, best 0.9484 | Component snapshot includes latest derived dimension signals and success/step telemetry | `/training-metrics` dimensions are diagnostic (derived), not raw per-episode logs | `docs/project/snapshots/component_metrics_20260422T170824Z.md` |
| 2026-04-22T17:08:25Z | Submission refresh | Refreshed submission snapshot after enhancement docs pass | Updated timestamped summary with stable canonical metrics set | Ready for pitch/video script alignment and final demo runbook | Re-freeze if further training runs change episode history | `docs/project/snapshots/submission_snapshot_20260422T170825Z.md` |
| 2026-04-22T17:25:10Z | Compact ablation run | Executed deterministic reward-behavior micro-ablations | Evidence gating: 0.10 -> 0.50; customer gating: 0.30 -> 1.00; coordination noise: 0.45 -> 0.70 | Confirms anti-shortcut reward controls are directionally aligned | Controlled synthetic-state ablations; use with transcript evidence for final claims | `docs/project/snapshots/reward_ablation_20260422T172510Z.md` |
| 2026-04-22T17:25:11Z | Snapshot refresh | Refreshed component and submission snapshots after behavior/reward updates | Canonical metrics remain stable for story sync | Evidence pack updated for final sign-off | Re-freeze once more if any late training updates occur | `docs/project/snapshots/submission_snapshot_20260422T172511Z.md` |

## Ongoing template (copy for future runs)

| UTC timestamp | Run type | Config note | Reward evidence | Behavior evidence | Risks/notes | Artifact |
|---|---|---|---|---|---|---|
| YYYY-MM-DDTHH:MM:SSZ | quick/full/ablation | prompt count, expert criteria, incident mix | avg/best/recent/improvement | phase transitions, notification timing, coalition quality | drift, timeout, exploit observations | path/to/snapshot |

## Audit checklist per run

1. Capture `/metrics` and `/learning-curve`.
2. Capture one transcript (`/demo/run/INC003` or selected incident).
3. Note at least one behavior-level delta (not only scalar change).
4. Record any suspected exploit pattern and whether controls caught it.
5. Link immutable artifact files.
