# Curriculum and Ablation Evidence

Purpose: show that improvement is intentional and causal, not accidental metric drift.

## Curriculum strategy used

NEXUS follows a staged difficulty pattern:

1. **Easy/medium onboarding**
   - Build non-zero reward trajectories quickly.
2. **Hard scenario exposure**
   - Increase red herring pressure and coordination demands.
3. **Nightmare stress testing (INC007)**
   - Validate schema drift and contract adaptation behavior.

The environment and reward system are explicitly structured to support this progression (`server/environment.py`, `server/difficulty.py`, `server/incidents.py`).

## Why this curriculum is valid for BRD + Self-Serve guidance

- Keeps success probability > 0 early (prevents RL stall).
- Increases branching complexity only after stable basic policy behavior.
- Preserves verifiable outcomes through deterministic endpoints and state inspection.

## Compact ablation plan (execution-ready)

These are recommended quick ablations to run in remaining time:

1. **Coordination penalty ablation**
   - Variant A: current coordination duplicate-call penalty.
   - Variant B: reduced/disabled duplicate penalty.
   - Expected: Variant A lowers redundant actions and improves phase progression quality.

2. **Customer-action gating ablation**
   - Variant A: current notification-required customer score.
   - Variant B: weaker/no gating.
   - Expected: Variant A improves proactive communication behavior and SLA handling quality.

3. **Expert-criteria adaptation ablation**
   - Variant A: adaptive expert criteria based on weak dimensions.
   - Variant B: static cycle only.
   - Expected: Variant A improves weak-dimension recovery over subsequent episodes.

## Measurement template for each ablation

| Ablation | Metric delta | Behavior delta | Interpretation |
|---|---|---|---|
| coordination_penalty_on_vs_off | avg reward, coordination component, duplicate query count | repeated tool-call frequency, specialist diversity in findings | Whether anti-redundancy logic improves actual teamwork |
| customer_gating_on_vs_off | customer component, notification timing | proactive notification occurrence before step threshold | Whether customer correctness is action-grounded |
| adaptive_expert_vs_static | weak-dimension recovery slope | role/phase consistency in transcripts | Whether adaptive review emphasis improves robustness |

## Artifact policy

- Store all ablation outputs under `docs/project/snapshots/`.
- Link each run in `docs/project/TRAINING_AUDIT_LOG.md`.
- Use only frozen snapshots in pitch narrative.

## Latest compact ablation snapshot

Latest run: `2026-04-22T17:25:10Z`  
Artifact: `docs/project/snapshots/reward_ablation_20260422T172510Z.md`

Observed directional outcomes:

- Diagnosis evidence gating:
  - without evidence: `0.10`
  - with evidence: `0.50`
- Customer action gating:
  - without notification: `0.30`
  - with proactive notification: `1.00`
- Coordination anti-noise behavior:
  - noisy/no-op pattern: `0.45`
  - coordinated multi-agent pattern: `0.70`

Interpretation: core anti-shortcut controls are directionally aligned with intended operational behavior.
