#!/usr/bin/env bash
set -euo pipefail

# Resolve nexus-enhanced package root (parent of scripts/)
_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$_repo_root" || exit 1

# NEXUS Enhanced gate runner
# Workflow order (as requested):
# 1) localhost tests
# 2) OpenEnv validate
# 3) optional OpenEnv push
# 4) optional HF Space validation

HF_URL=""
DO_PUSH=0
REPO_ID=""
SKIP_REGRESSION=0
SKIP_LOCAL_API=0
PORT=7860

# Load optional .env values for repo/url naming defaults.
if [[ -f ".env" ]]; then
  # shellcheck source=/dev/null
  set -a
  source .env
  set +a
fi

DEFAULT_SPACE_SUFFIX="${DEFAULT_SPACE_SUFFIX:-stage}"
DEFAULT_SPACE_NAME="nexus-enhanced-${DEFAULT_SPACE_SUFFIX}"
HF_USERNAME="${HF_USERNAME:-kunalkachru23}"
DEFAULT_REPO_ID="${SPACE_REPO_ID:-${HF_USERNAME}/${DEFAULT_SPACE_NAME}}"
DEFAULT_HF_URL="${HF_SPACE_URL:-https://${DEFAULT_REPO_ID/\//-}.hf.space}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --hf-url)
      HF_URL="${2:-}"
      shift 2
      ;;
    --push)
      DO_PUSH=1
      shift
      ;;
    --repo-id)
      REPO_ID="${2:-}"
      shift 2
      ;;
    --skip-regression)
      SKIP_REGRESSION=1
      shift
      ;;
    --skip-local-api)
      SKIP_LOCAL_API=1
      shift
      ;;
    --port)
      PORT="${2:-7860}"
      shift 2
      ;;
    -h|--help)
      cat <<EOF
Usage: ./gate.sh [options]   (repo root wrapper) or: bash scripts/shell/gate.sh [options]

Options:
  --hf-url <url>         Validate deployed HF space and run remote regression tests.
  --push                 Run openenv push after local gates pass.
  --repo-id <id>         Repo id for openenv push (default: ${DEFAULT_REPO_ID}).
  --hf-username <name>   Override HF username used for default repo/url generation.
  --space-suffix <name>  Space suffix for default repo/url (default: ${DEFAULT_SPACE_SUFFIX}).
  --skip-regression      Skip python test_regression_local.py.
  --skip-local-api       Skip localhost API smoke checks.
  --port <port>          Local FastAPI port for smoke tests (default: 7860).
  -h, --help             Show this help.

After \`--push\`, the gate polls the HF Space until GET /health returns status=healthy
and GET /metadata returns 200 (Docker rebuild). Override wait with:
  NEXUS_POST_PUSH_WAIT_MAX (seconds, default 360) and
  NEXUS_POST_PUSH_WAIT_INTERVAL (seconds, default 15).

Examples:
  ./gate.sh
  ./gate.sh --push
  ./gate.sh --hf-url ${DEFAULT_HF_URL}
  ./gate.sh --push --repo-id ${DEFAULT_REPO_ID} --hf-url ${DEFAULT_HF_URL}
EOF
      exit 0
      ;;
    --hf-username)
      HF_USERNAME="${2:-}"
      shift 2
      DEFAULT_REPO_ID="${HF_USERNAME}/${DEFAULT_SPACE_NAME}"
      DEFAULT_HF_URL="https://${HF_USERNAME}-${DEFAULT_SPACE_NAME}.hf.space"
      ;;
    --space-suffix)
      DEFAULT_SPACE_SUFFIX="${2:-}"
      shift 2
      DEFAULT_SPACE_NAME="nexus-enhanced-${DEFAULT_SPACE_SUFFIX}"
      DEFAULT_REPO_ID="${HF_USERNAME}/${DEFAULT_SPACE_NAME}"
      DEFAULT_HF_URL="https://${HF_USERNAME}-${DEFAULT_SPACE_NAME}.hf.space"
      ;;
    *)
      echo "Unknown arg: $1"
      echo "Run ./gate.sh --help"
      exit 1
      ;;
  esac
done

if [[ "$DO_PUSH" -eq 1 && -z "$REPO_ID" ]]; then
  REPO_ID="$DEFAULT_REPO_ID"
fi

if [[ -z "$HF_URL" && "$DO_PUSH" -eq 1 ]]; then
  # If pushing and URL not explicitly provided, validate against default new space URL.
  HF_URL="$DEFAULT_HF_URL"
fi

section() {
  printf "\n%s\n" "======================================================================"
  printf "%s\n" "$1"
  printf "%s\n" "======================================================================"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1"; exit 1; }
}

SERVER_PID=""
cleanup() {
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# Poll HF Space after openenv push — new revision often needs 1–5+ minutes before
# `openenv validate --url` passes (old container still serving).
wait_for_hf_space_ready() {
  local raw="${1:-}"
  local base="${raw%/}"
  local max_sec="${NEXUS_POST_PUSH_WAIT_MAX:-360}"
  local interval="${NEXUS_POST_PUSH_WAIT_INTERVAL:-15}"
  local elapsed=0
  if [[ -z "$base" ]]; then
    echo "wait_for_hf_space_ready: empty URL, skipping."
    return 0
  fi
  printf "\n%s\n" "Polling ${base} for post-push readiness (max ${max_sec}s, every ${interval}s)..."
  while [[ "${elapsed}" -lt "${max_sec}" ]]; do
    local hc mc st
    hc="$(curl -sS -o /tmp/nexus_gate_health.json -w "%{http_code}" "${base}/health" 2>/dev/null || echo "000")"
    mc="$(curl -sS -o /dev/null -w "%{http_code}" "${base}/metadata" 2>/dev/null || echo "000")"
    if [[ "${hc}" == "200" && "${mc}" == "200" ]]; then
      st="$(python3 -c "import json; d=json.load(open('/tmp/nexus_gate_health.json')); print(d.get('status',''))" 2>/dev/null || echo "")"
      if [[ "${st}" == "healthy" ]]; then
        printf "%s\n" "Space looks ready after ${elapsed}s (health=healthy, metadata=200)."
        return 0
      fi
    fi
    printf "%s\n" "  ... waiting (health HTTP ${hc}, metadata HTTP ${mc}, ${elapsed}s / ${max_sec}s)"
    sleep "${interval}"
    elapsed=$((elapsed + interval))
  done
  printf "%s\n" "WARN: Timed out after ${max_sec}s — build may still be running; remote validate may fail."
  return 1
}

section "PRE-FLIGHT"
require_cmd python
require_cmd pytest
require_cmd openenv
require_cmd curl
echo "Python: $(python --version)"
echo "Pytest: $(pytest --version | head -n 1)"
echo "OpenEnv CLI: available"
echo "Default deploy repo: ${DEFAULT_REPO_ID}"
echo "Default deploy URL:  ${DEFAULT_HF_URL}"

section "LOCAL TESTS (PRIMARY GATE)"
pytest tests/ -q

if [[ "$SKIP_REGRESSION" -eq 0 ]]; then
  section "LOCAL REGRESSION SCRIPT"
  python test_regression_local.py
fi

if [[ "$SKIP_LOCAL_API" -eq 0 ]]; then
  section "LOCALHOST API SMOKE"
  uvicorn server.app:app --host 127.0.0.1 --port "$PORT" >/tmp/nexus-gate-uvicorn.log 2>&1 &
  SERVER_PID="$!"
  sleep 2

  python - <<PY
import requests, sys
base = "http://127.0.0.1:${PORT}"

try:
    h = requests.get(f"{base}/health", timeout=5)
    h.raise_for_status()
    health = h.json()
    assert health.get("status") in ("ok", "healthy"), f"Unexpected health: {health}"

    r = requests.post(f"{base}/reset", json={"incident_id": "INC003"}, timeout=10)
    r.raise_for_status()
    reset_data = r.json()
    session_id = reset_data["session_id"]

    step_payload = {
        "situation_assessment": "Gate smoke step",
        "hypothesis": "Investigating memory pressure",
        "resolution_confidence": 0.0,
        "l2_directive": {"action": "check_all_alerts", "parameters": {}, "reasoning": "smoke"},
        "sre_directive": {"action": "list_runbooks", "parameters": {}, "reasoning": "smoke"},
    }
    s = requests.post(f"{base}/step/{session_id}", json=step_payload, timeout=10)
    s.raise_for_status()
    step_data = s.json()
    assert "observation" in step_data and "reward" in step_data, "Malformed step response"

    m = requests.get(f"{base}/metrics", timeout=5)
    m.raise_for_status()
    lc = requests.get(f"{base}/learning-curve", timeout=5)
    lc.raise_for_status()
    print("Local API smoke: PASS")
except Exception as e:
    print(f"Local API smoke: FAIL -> {e}")
    sys.exit(1)
PY
fi

section "OPENENV VALIDATION (LOCAL)"
openenv validate .

if [[ "$DO_PUSH" -eq 1 ]]; then
  section "OPENENV PUSH (HF SPACE DEPLOY)"
  echo "Target repo: ${REPO_ID}"
  # OpenEnv does not auto-load .hfignore; pass it so push staging matches lean Hub policy.
  openenv push . --repo-id "$REPO_ID" --exclude .hfignore
  if [[ -n "$HF_URL" ]]; then
    section "WAIT FOR HF SPACE (POST-PUSH DOCKER REBUILD)"
    wait_for_hf_space_ready "$HF_URL" || true
  fi
fi

if [[ -n "$HF_URL" ]]; then
  section "OPENENV VALIDATION (REMOTE URL)"
  openenv validate --url "$HF_URL"

  section "HF SPACE REGRESSION TESTS"
  python test_hf_space_deployment.py --url "$HF_URL"
fi

section "GATE COMPLETE"
echo "All requested gates passed."
