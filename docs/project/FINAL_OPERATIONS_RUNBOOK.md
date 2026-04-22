# Final Operations Runbook

Purpose: deterministic final-day operations with explicit fallback paths and no regression surprises.

## Canonical URLs and artifacts

- Stage URL: `https://kunalkachru23-nexus-enhanced-stage.hf.space`
- Evidence index: `docs/project/JUDGING_EVIDENCE_INDEX.md`
- Pitch script: `docs/pitch/PITCH.md`
- Demo walkthrough: `docs/pitch/DEMO_WALKTHROUGH.md`

## Pre-flight checks (T-60 to T-30 min)

1. Validate local:
   - `pytest tests/ -q`
   - `openenv validate .`
2. Validate remote:
   - `openenv validate --url https://kunalkachru23-nexus-enhanced-stage.hf.space`
   - `python test_hf_space_deployment.py --url https://kunalkachru23-nexus-enhanced-stage.hf.space`
3. Freeze fresh snapshots:
   - `python scripts/export_submission_snapshot.py --url https://kunalkachru23-nexus-enhanced-stage.hf.space`
   - `python scripts/export_component_metrics.py --url https://kunalkachru23-nexus-enhanced-stage.hf.space`
4. Confirm evidence docs reflect current frozen values.

## Canonical 3-minute demo path

1. Open `/web`.
2. Show metrics/reward context (10-15s).
3. Run auto-demo on INC003 (20-30s).
4. Show completed phase progression + reward breakdown.
5. Close with one innovation claim + one anti-hacking claim + one measurable improvement claim.

## Fallback branches

## Branch A — UI partially degraded

- Use terminal calls:
  - `curl -s https://kunalkachru23-nexus-enhanced-stage.hf.space/metrics`
  - `curl -s https://kunalkachru23-nexus-enhanced-stage.hf.space/learning-curve`
  - `curl -s -X POST https://kunalkachru23-nexus-enhanced-stage.hf.space/demo/run/INC003`
- Narrate using frozen snapshots in `docs/project/snapshots/`.

## Branch B — API latency spikes

- Use pre-generated artifacts:
  - `docs/images/training_reward_curve.png`
  - latest `submission_snapshot_*.md`
  - latest `component_metrics_*.md`
- Continue storyline from evidence pack without live retries.

## Branch C — Unexpected endpoint behavior

- Immediately run:
  - `/health`
  - `/metadata`
  - `/schema`
- Pivot to hard-gate proof + archived transcript evidence.
- Do not attempt risky hotfixes during final window.

## Roles and ownership

- **Driver:** live demo execution and narration.
- **Observer:** endpoint/watchdog and quick fallback decision.
- **Recorder:** captures timestamps, screenshots, and post-demo notes.

## Stop-doing list (final 24h)

- No broad refactors.
- No dependency churn.
- No non-essential UI redesign.
- No metric value changes in pitch docs without refreshed snapshot artifacts.
