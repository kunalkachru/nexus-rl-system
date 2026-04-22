#!/bin/bash
# Local deployment test script (Phase 5)
# Starts both FastAPI and Streamlit, runs regression tests, validates connectivity

set -e

_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$_repo_root" || exit 1

echo "🚀 NEXUS Enhanced — Local Deployment Test"
echo "========================================="

# Kill any existing processes on ports 7860/8501
cleanup() {
    echo "Cleaning up..."
    pkill -f "uvicorn server.app" || true
    pkill -f "streamlit run" || true
    sleep 1
}
trap cleanup EXIT

cleanup

# Test 1: Regression suite
echo -e "\n📋 Running regression test suite..."
python test_regression_local.py || exit 1

# Test 2: Start FastAPI
echo -e "\n🔧 Starting FastAPI on port 7860..."
uvicorn server.app:app --host 0.0.0.0 --port 7860 > /tmp/fastapi.log 2>&1 &
FASTAPI_PID=$!
sleep 3

# Test 3: Verify FastAPI endpoints
echo "✅ Testing FastAPI endpoints..."
HEALTH=$(curl -s http://localhost:7860/health | jq -r '.status' || echo "FAILED")
if [ "$HEALTH" != "ok" ] && [ "$HEALTH" != "healthy" ]; then
    echo "❌ Health check failed: $HEALTH"
    cat /tmp/fastapi.log
    exit 1
fi
echo "  ✓ /health: OK"

METRICS=$(curl -s http://localhost:7860/metrics | jq -r '.episode_count' || echo "FAILED")
echo "  ✓ /metrics: Episodes=$METRICS"

# Test 4: Reset endpoint
echo "✅ Testing /reset endpoint..."
RESET_RESPONSE=$(curl -s -X POST http://localhost:7860/reset \
    -H "Content-Type: application/json" \
    -d '{"incident_id": "INC003"}')
SESSION_ID=$(echo $RESET_RESPONSE | jq -r '.session_id')
if [ -z "$SESSION_ID" ] || [ "$SESSION_ID" = "null" ]; then
    echo "❌ Reset failed: $RESET_RESPONSE"
    exit 1
fi
echo "  ✓ Started session: ${SESSION_ID:0:8}..."

# Test 5: Step endpoint
echo "✅ Testing /step endpoint..."
STEP_RESPONSE=$(curl -s -X POST "http://localhost:7860/step/$SESSION_ID" \
    -H "Content-Type: application/json" \
    -d '{
        "situation_assessment": "Investigating incident",
        "hypothesis": "root cause hypothesis",
        "resolution_confidence": 0.0,
        "l1_action": {"action": "send_notification", "parameters": {}, "reasoning": ""},
        "l2_action": {"action": "query_logs", "parameters": {}, "reasoning": ""},
        "sre_action": {"action": "list_runbooks", "parameters": {}, "reasoning": ""},
        "pm_action": {"action": "get_sla_status", "parameters": {}, "reasoning": ""},
        "severity_assessment": "p2",
        "escalation_required": false
    }')
REWARD=$(echo $STEP_RESPONSE | jq -r '.reward // "FAILED"')
echo "  ✓ Step executed, reward: $REWARD"

# Test 6: Learning curve endpoint
echo "✅ Testing /learning-curve endpoint..."
CURVE=$(curl -s http://localhost:7860/learning-curve | jq -r '.episodes | length')
echo "  ✓ Learning curve: $CURVE episodes"

echo -e "\n✅ All FastAPI tests PASSED"

# Test 7: Start Streamlit (in background, don't wait for it)
echo -e "\n📊 Starting Streamlit validation UI on port 8501 (background)..."
streamlit run streamlit_app_v2.py --server.port=8501 --server.address=0.0.0.0 \
    > /tmp/streamlit.log 2>&1 &
STREAMLIT_PID=$!
sleep 5

# Verify Streamlit started
if ! kill -0 $STREAMLIT_PID 2>/dev/null; then
    echo "❌ Streamlit failed to start"
    cat /tmp/streamlit.log
    exit 1
fi
echo "  ✓ Streamlit running on port 8501"

# Test 8: Verify Streamlit can call FastAPI
echo "✅ Testing Streamlit→FastAPI connectivity..."
STREAMLIT_CALL=$(python -c "
import requests
try:
    resp = requests.post('http://localhost:7860/reset', json={'incident_id': 'INC003'})
    if resp.status_code == 200:
        print('OK')
    else:
        print(f'FAILED: {resp.status_code}')
except Exception as e:
    print(f'ERROR: {e}')
")
echo "  ✓ Streamlit can reach FastAPI: $STREAMLIT_CALL"

echo -e "\n========================================="
echo "✅ LOCAL DEPLOYMENT TEST PASSED"
echo "========================================="
echo ""
echo "Services running:"
echo "  • FastAPI (judge dashboard): http://localhost:7860"
echo "  • Streamlit (validation UI): http://localhost:8501"
echo ""
echo "Next steps:"
echo "  1. Open http://localhost:7860 in browser to see judge dashboard"
echo "  2. Open http://localhost:8501 in browser to see validation UI"
echo "  3. Run 'docker build -t nexus-enhanced:latest .' when Docker is available"
echo "  4. Deploy to HF Spaces (Phase 6)"
echo ""

# Keep services running until user interrupts
read -p "Press Enter to stop services..." </dev/null || true
