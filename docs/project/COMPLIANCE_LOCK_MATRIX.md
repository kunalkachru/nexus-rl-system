# Compliance Lock Matrix (BRD-Aligned)

Purpose: freeze hard-gate and scoring-criterion traceability so implementation changes remain compliant.

## Hard gates (pass/fail)

| Gate | Requirement | Project evidence | Verification command |
|---|---|---|---|
| OpenEnv latest workflow | Use OpenEnv validation/deployment workflow | `openenv.yaml`, `server/app.py`, deployment scripts | `openenv validate .` and `openenv validate --url https://kunalkachru23-nexus-enhanced-stage.hf.space` |
| Colab training script | Minimal Colab script with TRL/Unsloth path | `notebooks/grpo_colab_v2.ipynb` | Notebook config + run cells |
| Public artifact | HF blog or <2 min video | `docs/blog/*`, `docs/pitch/YOUTUBE_RECORDING_SCRIPT.md` | Submission URL checklist |

## Weighted scoring criteria map

| Criterion | BRD weight | What judges need | NEXUS evidence |
|---|---:|---|---|
| Environment Innovation | 40% | Novel, challenging, realistic environment mechanics | `server/environment.py`, `server/incidents.py`, `docs/project/SUBTHEME_EVIDENCE_MATRIX.md` |
| Storytelling | 30% | Clear and engaging 3-minute narrative + easy follow demo | `docs/pitch/PITCH.md`, `docs/pitch/DEMO_WALKTHROUGH.md`, `docs/project/FINAL_OPERATIONS_RUNBOOK.md` |
| Improvement in Rewards | 20% | Observable metric movement and before/after behavior | `/metrics`, `/learning-curve`, `docs/project/snapshots/*`, `docs/project/BEHAVIORAL_DELTA_PROOF.md` |
| Reward + Training Pipeline | 10% | Coherent reward logic and behavior-level training impact | `server/reward.py`, `notebooks/grpo_colab_v2.ipynb`, `docs/project/REWARD_HACKING_DEFENSE.md` |

## Non-regression compliance checklist

Before sign-off, all must be true:

1. `pytest tests/ -q` passes.
2. `openenv validate .` passes.
3. `openenv validate --url https://kunalkachru23-nexus-enhanced-stage.hf.space` passes.
4. `python test_hf_space_deployment.py --url https://kunalkachru23-nexus-enhanced-stage.hf.space` passes.
5. Pitch/demo/video script metrics match latest frozen snapshot in `docs/project/snapshots/`.
