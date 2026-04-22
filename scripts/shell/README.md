# Shell scripts

| Script | Purpose |
|--------|--------|
| **`../../start.sh`** (repo root) | **Production** entrypoint for HF Docker: FastAPI + Streamlit. Must stay at root (`Dockerfile` `CMD`). |
| **`gate.sh`** | Pre-flight: `pytest`, optional `test_regression_local.py`, localhost API smoke, `openenv validate .`, optional `openenv push`, optional HF URL + `test_hf_space_deployment.py`. |
| **`test_local_deployment.sh`** | Integration test: regression, start uvicorn + curl checks, start Streamlit, leave services up until Enter. |
| **`test_api_complete.sh`** | Manual curl walkthrough for INC003 (expects API on `localhost:7860`). |

Run from anywhere; each script `cd`s to the `nexus-enhanced` package root. From repo root you can still use **`./gate.sh`** (thin wrapper) or **`bash scripts/shell/gate.sh`**.

After **`./gate.sh --push`**, the gate **polls the Space** until `GET /health` returns `status=healthy` and `GET /metadata` returns 200 (HF Docker rebuild), then runs `openenv validate --url` and `test_hf_space_deployment.py`. Override with **`NEXUS_POST_PUSH_WAIT_MAX`** (default 360) and **`NEXUS_POST_PUSH_WAIT_INTERVAL`** (default 15), in seconds.
