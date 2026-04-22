# Archived Files Index

This index records files moved out of `nexus-enhanced/` into the top-level archive for final cleanup validation.

Archive root: `/Users/kunalkachru/Documents/hackathon-final-cursor/archive/nexus-enhanced`

## Bucket A (high-confidence unused now)

- `legacy-ui/gradio_app_backup.py` — backup variant, not in runtime/gate/tests.
- `legacy-ui/gradio_app_minimal.py` — minimal variant, not in runtime/gate/tests.
- `legacy-ui/streamlit_app.py` — old Streamlit UI; canonical path is `streamlit_app_v2.py`.
- `legacy-ui/training_simulator.py` — no active gate/runtime/test references.
- `legacy-notebooks/grpo_colab.ipynb` — superseded by `notebooks/grpo_colab_v2.ipynb`.

## Bucket B (legacy path requested for archive)

- `legacy-compose/docker-compose.yml` — old compose flow, not used by Dockerfile/start.sh HF path.
- `legacy-compose/gradio_app.py` — used only by old compose stack.
- `legacy-compose/router.py` — used only by old compose stack.

## Deferred restores (required by `openenv push` contract checks)

These were attempted for archive but restored to repo root because full release gate failed without them:

- `models.py` — `openenv push` errors with “Required file missing: models.py”.
- `client.py` — `openenv push` errors with “Required file missing: client.py”.
- `train.py` — restored together with `client.py` to keep OpenEnv package shape stable.
- `inference.py` — restored together with `client.py` to keep OpenEnv package shape stable.

## Validation expectation

- Active runtime remains: `Dockerfile` + `start.sh` + `server/*` + `streamlit_app_v2.py` + `web/*`.
- Gate/test path remains: `./gate.sh`, `scripts/shell/gate.sh`, `pytest tests/`, `test_regression_local.py`, `test_hf_space_deployment.py`.
