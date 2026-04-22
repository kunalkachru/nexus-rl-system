# NEXUS Enhanced — Judging Evidence Index

Snapshot timestamp (UTC): `2026-04-22T13:58:09Z`  
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
   - Blog draft: `docs/blog/blog_post.md`
   - Ready-to-publish variant: `docs/blog/blog_post_hf.md`
   - Owner action: publish final link and add URL to submission package.

## Live metrics snapshot (Criterion 3 evidence)

Source endpoints:
- `GET /metrics`
- `GET /learning-curve`

Snapshot values:
- Episode count: `120`
- Average reward: `0.4063`
- Best reward: `0.9484`
- Baseline reward: `0.265`
- Improvement: `+53.3%`

Visualization artifact:
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

## Pipeline and deployment proof

- Runtime entry: `start.sh` (FastAPI + Streamlit)
- API host app: `server/app.py`
- Full gate runner: `scripts/shell/gate.sh`
- Remote regression suite: `test_hf_space_deployment.py` (8/8 expected)

## Story/demo evidence pointers

- 3-minute script: `docs/pitch/PITCH.md`
- 2-minute live walkthrough: `docs/pitch/DEMO_WALKTHROUGH.md`
- Manual demo test cases: `docs/pitch/DEMO_MANUAL_TEST_CASES.md`
- Criterion-4 behavior proof sheet: `docs/project/BEHAVIORAL_DELTA_PROOF.md`
- Sub-theme matrix: `docs/project/SUBTHEME_EVIDENCE_MATRIX.md`

## Submission-day proof checklist

- Capture `openenv --version` screenshot.
- Capture latest `/metrics` and `/learning-curve` snapshot.
- Confirm blog or <2 min video URL is live.
- Keep stage URL and repo URL in final submission form.
