# NEXUS Enhanced — HF Spaces Deployment Guide (Phase 6)

## Architecture

```
Judge sees:              Colab training calls:
┌──────────────────┐     ┌──────────────────────┐
│ HF Space (7860)  │◄────│ Colab (TRL GRPO)     │
├──────────────────┤     └──────────────────────┘
│ FastAPI          │
│ • GET /          │ Returns HTML dashboard
│ • POST /reset    │ Start episode
│ • POST /step     │ Execute IC action
│ • GET /metrics   │ Training metrics
│ • GET /learning-curve │ Reward curves
└──────────────────┘
  ↓ (internal, not public)
┌──────────────────┐
│ Streamlit (8501) │ Validation UI (developers only)
│ Calls localhost:7860 │
└──────────────────┘
```

## Pre-Deployment Checklist (Local)

- [x] All 7 regression tests pass locally
- [x] FastAPI endpoints verified (/health, /reset, /step, /metrics, /learning-curve)
- [x] Streamlit connects to FastAPI on localhost:7860
- [x] Dockerfile builds successfully
- [x] start.sh runs both services in parallel
- [ ] Docker image tested locally (requires Docker daemon)
- [ ] Run `bash test_local_deployment.sh` to confirm all integration tests pass

## Deployment Steps

### Step 1: Set HF Token

```bash
# Get your HF token from: https://huggingface.co/settings/tokens
# (Create a new token with read+write permissions)

export HF_TOKEN='hf_xxxxxxxxxxxxx'
```

### Step 2: Deploy Directly to HF Spaces

```bash
# From nexus-enhanced directory
python deploy_to_hf_spaces.py

# Expected output:
#   📤 Uploading: Dockerfile... ✅
#   📤 Uploading: start.sh... ✅
#   📤 Uploading: server/app.py... ✅
#   ... (all files uploaded)
#   ✅ Uploaded: 25+ files
#   🎉 Deployment complete!
```

### Step 3: Verify Deployment (Takes ~5-10 min)

Once HF Spaces shows "Running" status:

```bash
# Test judge dashboard endpoint
curl -s https://kunalkachru23-nexus-enhanced.hf.space/health | jq .

# Test reset endpoint
curl -s -X POST https://kunalkachru23-nexus-enhanced.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"incident_id": "INC003"}' | jq .

# Test metrics endpoint
curl -s https://kunalkachru23-nexus-enhanced.hf.space/metrics | jq .

# Test learning curve
curl -s https://kunalkachru23-nexus-enhanced.hf.space/learning-curve | jq .
```

### Step 6: Update Colab Notebook

In `notebooks/grpo_colab_v2.ipynb`, ensure BASE_URL points to deployed space:

```python
BASE_URL = "https://kunalkachru23-nexus-enhanced.hf.space"  # YOUR SPACE URL
```

Then run connectivity check:
```python
response = requests.get(f"{BASE_URL}/health")
assert response.status_code == 200, f"Space not ready: {response.text}"
print("✅ Connected to HF Space!")
```

## Post-Deployment Testing (Phase 7)

Once deployed, run full regression test against public URL:

```bash
# Create temporary test file
cat > test_hf_space_deployment.py << 'EOF'
import requests
import json

BASE_URL = "https://kunalkachru23-nexus-enhanced.hf.space"

def test_health():
    resp = requests.get(f"{BASE_URL}/health")
    assert resp.status_code == 200
    print("✅ Health check passed")

def test_reset():
    resp = requests.post(f"{BASE_URL}/reset", 
        json={"incident_id": "INC003"})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["phase"] == "detection"
    print(f"✅ Reset passed (session: {data['session_id'][:8]}...)")
    return data["session_id"]

def test_step(session_id):
    action = {
        "situation_assessment": "Testing INC003",
        "hypothesis": "root cause",
        "resolution_confidence": 0.0,
        "l1_action": {"action": "send_notification", "parameters": {}, "reasoning": ""},
        "l2_action": {"action": "query_logs", "parameters": {}, "reasoning": ""},
        "sre_action": {"action": "list_runbooks", "parameters": {}, "reasoning": ""},
        "pm_action": {"action": "get_sla_status", "parameters": {}, "reasoning": ""},
        "severity_assessment": "p2",
        "escalation_required": False,
    }
    resp = requests.post(f"{BASE_URL}/step/{session_id}", json=action)
    assert resp.status_code == 200
    data = resp.json()
    assert "observation" in data
    print("✅ Step passed")

def test_learning_curve():
    resp = requests.get(f"{BASE_URL}/learning-curve")
    assert resp.status_code == 200
    data = resp.json()
    assert "episodes" in data
    print(f"✅ Learning curve passed ({len(data.get('episodes', []))} episodes)")

def test_metrics():
    resp = requests.get(f"{BASE_URL}/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "episode_count" in data
    print(f"✅ Metrics passed (total episodes: {data['episode_count']})")

if __name__ == "__main__":
    print(f"Testing HF Space: {BASE_URL}\n")
    test_health()
    session_id = test_reset()
    test_step(session_id)
    test_metrics()
    test_learning_curve()
    print("\n✅ ALL HF SPACE TESTS PASSED")
EOF

python test_hf_space_deployment.py
```

## Troubleshooting

### "Connection refused" or "Space not running"
- Check HF Spaces dashboard for build status
- If "Failed", check build logs for errors
- Common issues:
  - Dockerfile syntax error → fix and re-push
  - Missing dependencies in requirements.txt → add and re-push
  - Port conflict (7860 already in use) → change in Dockerfile/start.sh

### Slow response times
- HF Spaces cold start after 48h of inactivity (normal)
- First request may take 30s, subsequent requests <1s
- Solution: Keep Colab notebook running (keeps space warm)

### Streamlit endpoint returns 404
- Streamlit (port 8501) is internal only, not exposed via HF Spaces
- Only FastAPI (port 7860) is public
- For validation UI, access HF Spaces machine directly via SSH (advanced)

### Training rewards stuck at 0
- Verify `/health`, `/reset`, `/step` all return 200 before starting training
- Check Colab notebook has correct `BASE_URL`
- Run single step manually to debug action parsing

## Monitoring During Training (Colab)

While Colab trains:

1. **Watch reward curves**: https://kunalkachru23-nexus-enhanced.hf.space/learning-curve
2. **Check metrics**: `curl https://kunalkachru23-nexus-enhanced.hf.space/metrics`
3. **Monitor Colab logs** for reward_fn errors
4. **Expected pattern**: First 5-10 episodes ~0.2 reward, then gradual improvement to 0.6-0.8

## Rollback

If deployment breaks judges' demo:

```bash
# Revert to previous commit
git revert HEAD --no-edit
git push origin main
# HF Spaces auto-rebuilds with previous version
```

## Next Steps

- **Phase 7**: Run full regression tests against deployed HF Space
- **Blog Post**: Write HF blog explaining NEXUS architecture (hard gate)
- **Pitch**: Prepare 3-minute demo for judges (hard gate)
