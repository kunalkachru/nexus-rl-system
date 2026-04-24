# NEXUS Enhanced — Judging Evidence Index

Snapshot timestamp (UTC): `2026-04-24T16:48:26Z`  
Stage URL: `https://kunalkachru23-nexus-enhanced-stage.hf.space`

## Hard-gate evidence (BRD Section 17)

1. OpenEnv latest-release workflow in use
   - Local package validate: `openenv validate .`
   - Remote contract validate: `openenv validate --url https://kunalkachru23-nexus-enhanced-stage.hf.space`
   - Runtime pass status is documented in `docs/project/PROJECT_STATUS.md`.

2. Minimal Colab training script (Unsloth/HF TRL)
   - Notebook: `notebooks/grpo_colab_v2.ipynb`
   - Uses Unsloth + TRL GRPO with remote environment reward calls.

3. Blog/video submission artifact
   - Blog draft: `docs/blog/blog_post_hf.md`
   - Video script (<2 min): `docs/pitch/YOUTUBE_RECORDING_SCRIPT.md`
   - Owner action: publish final link and add URL to submission package.

4. Compliance lock matrix
   - BRD criterion and hard-gate mapping: `docs/project/COMPLIANCE_LOCK_MATRIX.md`

## Live metrics snapshot (Criterion 3 evidence)

Source endpoints:
- `GET /metrics`
- `GET /learning-curve`
- Optional scoped view: `GET /metrics?run_id=<run_id>` and `GET /learning-curve?run_id=<run_id>`
- Run discovery endpoint: `GET /runs`

Scope policy:
- Canonical submission numbers use aggregate scope (`run_id=all` / no `run_id` query).
- Run-scoped views are for internal debugging and diagnostics only.
- If quoting run-scoped numbers in notes, include the explicit `run_id`.

Snapshot values:
- Episode count: `387`
- Average reward: `0.4634`
- Best reward: `1.0032`
- Baseline reward: `0.265`
- Improvement: `+74.9%`

Visualization artifact (tracked):
- `docs/images/training_reward_curve.png`
- Refresh command:

```bash
python scripts/export_reward_plot.py \
  --url https://kunalkachru23-nexus-enhanced-stage.hf.space \
  --out docs/images/training_reward_curve.png
```

Submission snapshot automation:

```bash
python scripts/export_submission_snapshot.py \
  --url https://kunalkachru23-nexus-enhanced-stage.hf.space
```

This writes timestamped snapshot files under `docs/project/snapshots/`.

Canonical demo-day snapshot set (stage URL only):
- `docs/project/snapshots/submission_snapshot_20260424T164826Z.md`
- `docs/project/snapshots/component_metrics_20260424T164826Z.md`

## Pipeline and deployment proof

- Runtime entry: `start.sh` (FastAPI + Streamlit)
- API host app: `server/app.py`
- Full gate runner: `scripts/shell/gate.sh`
- Remote regression suite: `test_hf_space_deployment.py` (11/11 expected; includes `/curriculum`, INC008 via `/incidents` + reset smoke)

## Story/demo evidence pointers

- 3-minute script: `docs/pitch/PITCH.md`
- 2-minute live walkthrough: `docs/pitch/DEMO_WALKTHROUGH.md`
- <2 minute recording script: `docs/pitch/YOUTUBE_RECORDING_SCRIPT.md`
- Manual demo test cases: `docs/pitch/DEMO_MANUAL_TEST_CASES.md`
- Criterion-4 behavior proof sheet: `docs/project/BEHAVIORAL_DELTA_PROOF.md`
- Sub-theme matrix: `docs/project/SUBTHEME_EVIDENCE_MATRIX.md`
- Reward-hacking defense: `docs/project/REWARD_HACKING_DEFENSE.md`
- Training audit ledger: `docs/project/TRAINING_AUDIT_LOG.md`
- Curriculum and ablation plan: `docs/project/CURRICULUM_AND_ABLATION.md`
- Latest ablation snapshot: `docs/project/snapshots/reward_ablation_20260422T172510Z.md`
- Final runbook: `docs/project/FINAL_OPERATIONS_RUNBOOK.md`
- HF Space UI verification: `docs/project/UI_VERIFICATION_REPORT.md`
- Final readiness report: `docs/project/FINAL_READINESS_REPORT.md`

## Submission-day proof checklist

- Capture `openenv --version` screenshot.
- Capture latest `/metrics` and `/learning-curve` snapshot.
- Capture latest component metrics snapshot (`export_component_metrics.py`).
- Confirm blog or <2 min video URL is live.
- Keep stage URL and repo URL in final submission form.
