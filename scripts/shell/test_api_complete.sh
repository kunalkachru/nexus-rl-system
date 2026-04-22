#!/bin/bash

_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$_repo_root" || exit 1

# Complete API Test with Runbook Step Dropdown Fix
# Tests 6 steps of INC003 with proper runbook directives

BASE_URL="http://localhost:7860"

echo "================================================================================"
echo "SECTION 1: API TEST - Complete Episode Lifecycle with Proper Runbook Directives"
echo "================================================================================"

# Reset episode
echo ""
echo "[RESET] Starting INC003 episode..."
RESET_RESPONSE=$(curl -s -X POST "$BASE_URL/reset" \
  -H "Content-Type: application/json" \
  -d '{"incident_id": "INC003", "difficulty": "medium"}')

SESSION_ID=$(echo "$RESET_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")
echo "✅ Session created: $SESSION_ID"

# Step 1: Detection
echo ""
echo "[STEP 1] Detection - L2 & L1 Investigation"
curl -s -X POST "$BASE_URL/step/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "situation_assessment": "Incident: Memory Leak Under Load",
    "hypothesis": "ML model feature vector cache issue",
    "resolution_confidence": 0.20,
    "l2_directive": {"action": "check_all_alerts", "parameters": {}, "reasoning": "Investigate"},
    "l1_directive": {"action": "check_customer_reports", "parameters": {}, "reasoning": "Check impact"}
  }' | python3 -c "import sys, json; d = json.load(sys.stdin); o = d['observation']; print(f'  Phase: {o[\"phase\"]:15} | Step: {o[\"step\"]:2} | Done: {d[\"done\"]} | Reward: {d[\"reward\"]:.4f}')"

# Step 2: Triage
echo "[STEP 2] Triage - Deploy History Check"
curl -s -X POST "$BASE_URL/step/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "situation_assessment": "L2 confirms recent deployment v4.2.1",
    "hypothesis": "ML model v4 feature vector cache has no eviction",
    "resolution_confidence": 0.30,
    "l2_directive": {"action": "check_all_alerts", "parameters": {}, "reasoning": "Investigate"},
    "l1_directive": {"action": "check_customer_reports", "parameters": {}, "reasoning": "Check impact"}
  }' | python3 -c "import sys, json; d = json.load(sys.stdin); o = d['observation']; print(f'  Phase: {o[\"phase\"]:15} | Step: {o[\"step\"]:2} | Done: {d[\"done\"]} | Reward: {d[\"reward\"]:.4f}')"

# Step 3: Investigation - Heap Profile
echo "[STEP 3] Investigation - Heap Profile (rb_heap_profile)"
curl -s -X POST "$BASE_URL/step/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "situation_assessment": "L2 found heap at 14GB, cache consuming all memory",
    "hypothesis": "ML model v4 feature vector cache has no eviction",
    "resolution_confidence": 0.40,
    "l2_directive": {"action": "check_all_alerts", "parameters": {}, "reasoning": "Investigate"},
    "sre_directive": {"action": "execute_runbook_step", "parameters": {"step_id": "rb_heap_profile"}, "reasoning": "Profile heap"}
  }' | python3 -c "import sys, json; d = json.load(sys.stdin); o = d['observation']; print(f'  Phase: {o[\"phase\"]:15} | Step: {o[\"step\"]:2} | Done: {d[\"done\"]} | Reward: {d[\"reward\"]:.4f}')"

# Step 4: Mitigation 1 - Check Cache Config
echo "[STEP 4] Mitigation - Check Cache Config (rb_check_cache_config)"
curl -s -X POST "$BASE_URL/step/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "situation_assessment": "Heap profiler confirms cache issue. Need to check cache configuration.",
    "hypothesis": "ML model v4 feature vector cache has no eviction",
    "resolution_confidence": 0.50,
    "sre_directive": {"action": "execute_runbook_step", "parameters": {"step_id": "rb_check_cache_config"}, "reasoning": "Check cache config"},
    "pm_directive": {"action": "track_revenue_impact", "parameters": {}, "reasoning": "Track impact"}
  }' | python3 -c "import sys, json; d = json.load(sys.stdin); o = d['observation']; print(f'  Phase: {o[\"phase\"]:15} | Step: {o[\"step\"]:2} | Done: {d[\"done\"]} | Reward: {d[\"reward\"]:.4f}')"

# Step 5: Mitigation 2 - Set Cache Eviction
echo "[STEP 5] Mitigation - Apply LRU Eviction (rb_set_cache_eviction)"
curl -s -X POST "$BASE_URL/step/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "situation_assessment": "Cache config confirmed: no eviction policy. Applying LRU eviction.",
    "hypothesis": "ML model v4 feature vector cache has no eviction",
    "resolution_confidence": 0.70,
    "sre_directive": {"action": "execute_runbook_step", "parameters": {"step_id": "rb_set_cache_eviction"}, "reasoning": "Enable LRU eviction"},
    "pm_directive": {"action": "track_revenue_impact", "parameters": {}, "reasoning": "Track impact"}
  }' | python3 -c "import sys, json; d = json.load(sys.stdin); o = d['observation']; print(f'  Phase: {o[\"phase\"]:15} | Step: {o[\"step\"]:2} | Done: {d[\"done\"]} | Reward: {d[\"reward\"]:.4f}')"

# Step 6: Resolution - High Confidence
echo "[STEP 6] Resolution - High Confidence (Completes Episode)"
FINAL_RESPONSE=$(curl -s -X POST "$BASE_URL/step/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "situation_assessment": "LRU eviction applied. Heap returned to normal. Service stable.",
    "hypothesis": "ML model v4 feature vector cache had no eviction - RESOLVED",
    "resolution_confidence": 0.85,
    "l1_directive": {"action": "check_customer_reports", "parameters": {}, "reasoning": "Verify customer impact resolved"}
  }')

echo "$FINAL_RESPONSE" | python3 << 'PYEOF'
import sys, json
d = json.load(sys.stdin)
o = d['observation']
print(f'  Phase: {o["phase"]:15} | Step: {o["step"]:2} | Done: {d["done"]} | Reward: {d["reward"]:.4f}')

if d['done']:
    print(f'\n✅ Episode COMPLETED at step {o["step"]}')
    breakdown = d.get('info', {}).get('reward_breakdown', {})
    print(f'  MTTR: {breakdown.get("mttr", 0):.4f}')
    print(f'  Diagnosis: {breakdown.get("diagnosis", 0):.4f}')
    print(f'  Customer: {breakdown.get("customer", 0):.4f}')
    print(f'  Coordination: {breakdown.get("coordination", 0):.4f}')
    print(f'  Oversight: {breakdown.get("oversight", 0):.4f}')
    print(f'  Depth Bonus: {breakdown.get("depth_bonus", 0):.4f}')
    print(f'  TOTAL: {breakdown.get("total", 0):.4f}')
PYEOF

echo ""
echo "================================================================================"
echo "✅ API TEST COMPLETED - Episode progressed naturally from detection → postmortem"
echo "================================================================================"
