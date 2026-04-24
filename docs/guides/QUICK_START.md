# NEXUS Enhanced — Quick Start Guide

## TL;DR: Phases 1-7 Complete

**Status**: Ready to deploy to HF Spaces and train on Colab

### Local Verification (2 min)
```bash
# Single command gate (localhost tests -> openenv validate)
./gate.sh --skip-regression

# Optional deeper local run:
./gate.sh
```

### Deploy to HF Spaces (5-10 min)
```bash
# Set HF token (use your actual token)
export HF_TOKEN='hf_xxxxxxxxxxxxx'

# Preferred: OpenEnv push (no git required)
openenv validate .
openenv push . --repo-id kunalkachru23/nexus-enhanced-stage --exclude .hfignore

# Same as: ./gate.sh --push   (gate passes --exclude .hfignore for you)

# Monitor: https://huggingface.co/spaces/kunalkachru23/nexus-enhanced-stage
# Wait for "Running" status
```

**Why `--exclude .hfignore`?** The OpenEnv CLI does **not** read `.hfignore` automatically. Without this flag, `openenv push` only applies its tiny built-in ignore list, so **tests, `scripts/`, backups, and other paths listed in `.hfignore` would still be uploaded** and the Space file tree stays bloated. Passing `--exclude .hfignore` makes push staging match this repo’s **lean Hub policy**. The file deliberately uses **no `!` negation** lines, because OpenEnv **skips** negated patterns and they would not work as intended.

**If you omit `--exclude .hfignore`:** the push and Space build **still succeed** (they do not “crash” for that reason alone). You only lose the extra exclusions—more files get uploaded than intended until you prune the Space again or add the flag next time.

### Verify Deployment (2 min)
```bash
# Validate deployed space via same gate pipeline
./gate.sh --skip-regression --skip-local-api --hf-url https://kunalkachru23-nexus-enhanced-stage.hf.space

# Expected: ✅ remote tests pass (see test_hf_space_deployment.py; gate runs full suite)
```

### Start Training on Colab (6 hours)
```
1. Open: notebooks/grpo_colab_v2.ipynb
2. Verify: BASE_URL = "https://kunalkachru23-nexus-enhanced-stage.hf.space"
3. Run cells in order. Tunables (`BASE_URL`, `ONE_ROUND_TRAINING`, prompt counts, model id, GRPO batching, etc.) live in the **configuration cell** near the top (or set `NEXUS_*` environment variables before running it). For a **first successful round**, keep `ONE_ROUND_TRAINING = True` there (or `NEXUS_ONE_ROUND=true`); use `False` / `NEXUS_ONE_ROUND=false` for the full run.
4. Watch dashboard: https://kunalkachru23-nexus-enhanced-stage.hf.space/
```

### Export reward plot for slides (observable improvement evidence)
```bash
python scripts/export_reward_plot.py --url https://kunalkachru23-nexus-enhanced-stage.hf.space
# or from local episode_rewards.json:
python scripts/export_reward_plot.py --file episode_rewards.json --out docs/images/training_reward_curve.png
```

---

## What's Complete

| Phase | Component | Status |
|-------|-----------|--------|
| 1 | Local regression tests (7/7) | ✅ |
| 2 | Judge dashboard (HTML + Chart.js) | ✅ |
| 3 | Validation UI (Streamlit 3 modes) | ✅ |
| 4 | Colab training script (GRPO) | ✅ |
| 5 | Docker multi-service (FastAPI + Streamlit) | ✅ |
| 6 | HF Spaces deployment guide | ✅ |
| 7 | Remote regression tests (8/8) | ✅ |
| 8 | Training on Colab GPU | ⏳ Next |
| 9 | Blog post + Video | 📋 TODO |

---

## Key Files

**Core Environment**:
- `server/app.py` - FastAPI endpoints
- `server/environment.py` - NexusEnvironment
- `server/incidents.py` - 7 incident cases

**Deployment**:
- `Dockerfile` - Multi-service Docker
- `start.sh` - Launch script
- `requirements.txt` - Dependencies

**Testing**:
- `test_regression_local.py` - Phase 1 tests (7/7 passing)
- `test_hf_space_deployment.py` - Phase 7 tests (ready)
- `test_local_deployment.sh` - Integration tests

**UI**:
- `server/static/index.html` - Judge dashboard
- `streamlit_app_v2.py` - Validation UI

**Training**:
- `notebooks/grpo_colab_v2.ipynb` - GRPO pipeline

**Shell automation** (canonical copies under `scripts/shell/`; root `gate.sh`, `test_local_deployment.sh`, `test_api_complete.sh` are thin wrappers so old commands keep working):

- `scripts/shell/gate.sh` — pytest + OpenEnv + optional HF checks (same as `./gate.sh`).
- `scripts/shell/test_local_deployment.sh` — local FastAPI + Streamlit integration harness.
- `scripts/shell/test_api_complete.sh` — curl INC003 walkthrough (needs API on port 7860).
- `start.sh` — **stays at repo root** (Docker `CMD`); not under `scripts/shell/`.

**Documentation** (paths from `nexus-enhanced/` root):
- `docs/project/IMPLEMENTATION_SUMMARY.md` - Overview
- `docs/deployment/HF_SPACES_DEPLOYMENT.md` - Deployment steps
- `docs/deployment/DEPLOYMENT_CHECKLIST.md` - Pre-flight checks
- `docs/guides/QUICK_START.md` - This file

---

## Commands

### Local Testing
```bash
# Test all 7 incident cases
python test_regression_local.py

# Full integration test (starts both services)
bash test_local_deployment.sh
```

### Start Services Locally
```bash
# Start both FastAPI (7860) + Streamlit (8501)
bash start.sh

# OR manually:
uvicorn server.app:app --host 0.0.0.0 --port 7860 &
streamlit run streamlit_app_v2.py --server.port=8501 &
```

### Deploy to HF Spaces
```bash
cd nexus-enhanced
git add -A
git commit -m "Deploy phase 6"
git push hf main

# Monitor: https://huggingface.co/spaces/kunalkachru23/nexus-enhanced-stage
```

### Test Deployed Environment
```bash
python test_hf_space_deployment.py --url https://kunalkachru23-nexus-enhanced-stage.hf.space
```

---

## URLs

| Service | Local | Deployed |
|---------|-------|----------|
| Judge Dashboard | `http://localhost:7860/` | `https://kunalkachru23-nexus-enhanced-stage.hf.space/` |
| API Health | `http://localhost:7860/health` | `.../health` |
| Validation UI | `http://localhost:8501` | (Internal only) |
| Metrics | `http://localhost:7860/metrics` | `.../metrics` |
| Learning Curve | `http://localhost:7860/learning-curve` | `.../learning-curve` |

---

## Expected Results

### After Phase 7 (Deployment)
```
✅ Judge dashboard loads
✅ All 7 endpoints respond
✅ Metrics show 0 episodes (no training yet)
✅ Learning curve is empty (no training yet)
```

### After Colab Training (Phase 8)
```
✅ Dashboard updates every 5 seconds
✅ Learning curve shows episodes
✅ Reward curve: baseline 0.28 → improve to 0.6-0.8
✅ Rolling average (green line) clearly ascending
```

### Judging Criteria
| Criterion | Weight | Evidence |
|-----------|--------|----------|
| Innovation | 40% | 6-agent system + coalition mechanics |
| Storytelling | 30% | CrowdStrike narrative + dashboard |
| Reward Progress | **20%** | Chart.js curves on dashboard ← **KEY** |
| Pipeline | 10% | GRPO on Colab GPU → HF Space API |

**🎯 Priority**: Ensure reward curves are visible and improving to support the observable-improvement rubric row.

---

## Troubleshooting

**Q: Tests fail locally**  
A: Run `python test_regression_local.py` to see which test fails. Check `server/` files for errors.

**Q: Docker build fails on HF**  
A: Check HF Spaces build logs for error. Common: missing dependency in `requirements.txt`.

**Q: Can't connect Colab to HF Space**  
A: Verify BASE_URL in notebook matches your space URL. Test: `python test_hf_space_deployment.py --url <URL>`

**Q: Reward always 0 during training**  
A: This is expected (sparse reward design). Wait until `done=True` to get final reward.

**Q: Dashboard doesn't update**  
A: Check that FastAPI is running: `curl https://kunalkachru23-nexus-enhanced-stage.hf.space/health`

---

## Timeline

- **Today (Apr 21)**: Phases 1-5 complete, Phase 6-7 ready
- **This evening**: Push to HF Spaces, verify deployment
- **Apr 22-23**: Run Colab training (6 hours), collect reward curves
- **Apr 23**: Write blog post + record video
- **Apr 24-25**: On-site pitching to judges

---

## Contact

- **User**: Kunal Kachru (kunalkachru23@gmail.com)
- **Team**: Falcons
- **Event**: Meta PyTorch OpenEnv Hackathon
- **Date**: April 25-26, 2026

---

**Status**: ✅ Ready to deploy. Awaiting user confirmation.

Next: Push to HF Spaces → Verify endpoints → Launch Colab training
