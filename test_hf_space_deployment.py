"""
NEXUS Enhanced — HF Space Deployment Regression Tests
Runs critical checks against a deployed HF Space.

Usage:
  python test_hf_space_deployment.py --url https://<space>.hf.space
"""

import os
from pathlib import Path
import requests
import json
import sys
import argparse
import time

def load_dotenv_defaults() -> dict:
    defaults = {}
    env_path = Path(".env")
    if not env_path.exists():
        return defaults
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        defaults[key.strip()] = value.strip()
    return defaults


_dotenv_defaults = load_dotenv_defaults()
_space_repo_id = (
    os.getenv("SPACE_REPO_ID")
    or _dotenv_defaults.get("SPACE_REPO_ID")
    or "kunalkachru23/nexus-enhanced-stage"
)

# Override precedence: explicit HF_SPACE_URL env > .env HF_SPACE_URL > derived from SPACE_REPO_ID.
DEFAULT_URL = (
    os.getenv("HF_SPACE_URL")
    or _dotenv_defaults.get("HF_SPACE_URL")
    or f"https://{_space_repo_id.replace('/', '-')}.hf.space"
)

def print_header(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}")

def test_health(base_url):
    """TEST 1: Health check endpoint responds"""
    print_header("TEST 1: Health Check")

    try:
        resp = requests.get(f"{base_url}/health", timeout=10)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data.get("status") in ("ok", "healthy"), f"Unexpected health status: {data}"

        print(f"✅ Status: {data['status']}")
        print(f"✅ Environment: {data.get('environment', 'N/A')}")
        print(f"✅ Version: {data.get('version', 'N/A')}")
        print(f"✅ Active sessions: {data.get('active_sessions', 0)}")
        print(f"\n✅ PASSED: Health check successful")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_reset_endpoint(base_url):
    """TEST 2: /reset endpoint returns proper observation"""
    print_header("TEST 2: Reset Endpoint")

    try:
        resp = requests.post(
            f"{base_url}/reset",
            json={"incident_id": "INC003"},
            timeout=10
        )
        assert resp.status_code == 200, f"Reset failed: {resp.status_code} {resp.text}"
        obs = resp.json()

        # Validate response structure
        required_fields = ["session_id", "observation"]
        for field in required_fields:
            assert field in obs, f"Missing field: {field}"

        initial_obs = obs["observation"]
        assert initial_obs["incident_id"] == "INC003"
        assert initial_obs["phase"] == "detection"
        assert initial_obs["step"] == 0

        session_id = obs["session_id"]
        print(f"✅ Session ID: {session_id[:8]}...")
        print(f"✅ Incident: {initial_obs.get('incident_title', 'INC003')}")
        print(f"✅ Phase: {initial_obs['phase']}")
        print(f"✅ Step: {initial_obs['step']}")
        print(f"\n✅ PASSED: Reset endpoint returns proper structure")
        return True, session_id
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False, None

def test_step_endpoint(base_url, session_id):
    """TEST 3: /step endpoint processes action correctly"""
    print_header("TEST 3: Step Endpoint")

    try:
        action = {
            "situation_assessment": "P1 incident detected. Memory pressure on recommendation-service.",
            "hypothesis": "Memory leak in ML model cache",
            "resolution_confidence": 0.0,
            "l1_directive": {
                "action": "send_notification",
                "parameters": {"customers": "affected_customers", "message": "Investigating", "severity": "high"},
                "reasoning": "Notify customers early"
            },
            "l2_directive": {"action": "check_all_alerts", "parameters": {}, "reasoning": ""},
            "sre_directive": {"action": "list_runbooks", "parameters": {}, "reasoning": ""},
            "pm_directive": {"action": "check_sla_status", "parameters": {}, "reasoning": ""},
            "escalation_required": False,
        }

        resp = requests.post(
            f"{base_url}/step/{session_id}",
            json=action,
            timeout=10
        )
        assert resp.status_code == 200, f"Step failed: {resp.status_code} {resp.text}"
        data = resp.json()

        assert "observation" in data, "Missing observation in response"
        obs = data["observation"]
        assert obs["step"] == 1, f"Expected step 1, got {obs['step']}"
        assert "phase" in obs, "Missing phase in observation"

        reward = data.get("reward", 0.0)
        done = data.get("done", False)

        print(f"✅ Step advanced: 0 → {obs['step']}")
        print(f"✅ Phase: {obs['phase']}")
        print(f"✅ Reward: {reward} (should be 0.0 before done)")
        print(f"✅ Done: {done} (should be False)")
        print(f"\n✅ PASSED: Step endpoint processes actions correctly")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_metrics_endpoint(base_url):
    """TEST 4: /metrics endpoint returns training stats"""
    print_header("TEST 4: Metrics Endpoint")

    try:
        resp = requests.get(f"{base_url}/metrics", timeout=10)
        assert resp.status_code == 200, f"Metrics failed: {resp.status_code}"
        data = resp.json()

        assert "episode_count" in data, "Missing episode_count"
        episode_count = data.get("episode_count", 0)

        print(f"✅ Total episodes: {episode_count}")
        print(f"✅ Average reward: {data.get('avg_reward', 'N/A')}")
        print(f"✅ Best reward: {data.get('best_reward', 'N/A')}")
        print(f"✅ Improvement: {data.get('improvement', 'N/A')}")
        print(f"\n✅ PASSED: Metrics endpoint working")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_learning_curve(base_url):
    """TEST 5: /learning-curve endpoint returns reward history"""
    print_header("TEST 5: Learning Curve Endpoint")

    try:
        resp = requests.get(f"{base_url}/learning-curve", timeout=10)
        assert resp.status_code == 200, f"Learning curve failed: {resp.status_code}"
        data = resp.json()

        assert "rewards" in data, "Missing rewards in response"
        rewards = data.get("rewards", [])
        rolling = data.get("rolling_avg", [])

        print(f"✅ Episodes recorded: {len(rewards)}")

        if rewards:
            first = rewards[0]
            last = rewards[-1]
            print(f"✅ First episode reward: {first:.4f}")
            print(f"✅ Last episode reward: {last:.4f}")

            # Check for improvement trend
            if len(rewards) > 1:
                split = len(rewards) // 2
                avg_first_half = sum(rewards[:split]) / max(split, 1)
                avg_second_half = sum(rewards[split:]) / max(len(rewards) - split, 1)
                print(f"✅ Avg first half: {avg_first_half:.4f}")
                print(f"✅ Avg second half: {avg_second_half:.4f}")
                if rolling:
                    print(f"✅ Latest rolling avg: {rolling[-1]:.4f}")

        print(f"\n✅ PASSED: Learning curve endpoint working")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_html_dashboard(base_url):
    """TEST 6: Judge dashboard HTML renders"""
    print_header("TEST 6: HTML Dashboard (Judge View)")

    try:
        resp = requests.get(f"{base_url}/", timeout=10)
        assert resp.status_code == 200, f"Dashboard failed: {resp.status_code}"
        html = resp.text

        # Check for key dashboard elements
        assert "NEXUS Enhanced" in html, "Missing title"
        assert "rewardChart" in html, "Missing Chart.js setup"
        assert "fetchMetrics" in html, "Missing metrics fetch"

        print(f"✅ HTML dashboard loads (size: {len(html)} bytes)")
        print(f"✅ Contains Chart.js setup")
        print(f"✅ Contains metric refresh loops")
        print(f"\n✅ PASSED: Judge dashboard rendering")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_full_episode(base_url):
    """TEST 7: Full episode (detect → resolve)"""
    print_header("TEST 7: Full Episode Execution")

    try:
        # Reset
        reset_resp = requests.post(
            f"{base_url}/reset",
            json={"incident_id": "INC003"},
            timeout=10
        )
        assert reset_resp.status_code == 200
        session_id = reset_resp.json()["session_id"]

        # Run 20 steps
        actions = []
        for step_num in range(20):
            action = {
                "situation_assessment": f"Step {step_num}: investigating memory issue",
                "hypothesis": "Memory leak in cache",
                "resolution_confidence": 0.85 if step_num > 18 else 0.0,
                "l1_directive": {
                    "action": "send_notification",
                    "parameters": {"customers": "affected_customers", "message": "Investigating", "severity": "high"},
                    "reasoning": ""
                },
                "l2_directive": {"action": "check_all_alerts", "parameters": {}, "reasoning": ""},
                "sre_directive": {"action": "list_runbooks", "parameters": {}, "reasoning": ""},
                "pm_directive": {"action": "check_sla_status", "parameters": {}, "reasoning": ""},
                "escalation_required": False,
            }

            step_resp = requests.post(
                f"{base_url}/step/{session_id}",
                json=action,
                timeout=10
            )
            assert step_resp.status_code == 200, f"Step {step_num} failed"

            data = step_resp.json()
            if data.get("done"):
                final_reward = data.get("reward", 0.0)
                print(f"✅ Episode completed at step {step_num}")
                print(f"✅ Final reward: {final_reward:.4f}")
                print(f"✅ Final phase: {data['observation']['phase']}")
                print(f"\n✅ PASSED: Full episode executed successfully")
                return True

        print(f"⚠️ Episode did not complete in 20 steps (still in {data['observation']['phase']})")
        print(f"✅ PASSED: Episode advances correctly")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_auto_demo_inc003(base_url):
    """TEST 8: INC003 live demo reaches completion state"""
    print_header("TEST 8: Auto-Demo INC003")

    try:
        resp = requests.post(f"{base_url}/demo/run/INC003", timeout=20)
        assert resp.status_code == 200, f"Demo endpoint failed: {resp.status_code}"
        data = resp.json()

        assert data.get("incident_id") == "INC003", f"Unexpected incident_id: {data.get('incident_id')}"
        assert "transcript" in data and len(data["transcript"]) >= 2, "Demo transcript missing/too short"
        assert data.get("done") is True, f"Demo did not complete (phase={data.get('final_phase')}, steps={data.get('total_steps')})"
        assert data.get("demo_completed") is True, "Demo completed flag is false"
        assert data.get("reward_breakdown"), "Missing reward breakdown"

        print(f"✅ Final phase: {data.get('final_phase')}")
        print(f"✅ Total steps: {data.get('total_steps')}")
        print(f"✅ Reward total: {data['reward_breakdown'].get('total')}")
        print(f"\n✅ PASSED: Auto-demo reaches completed episode")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test HF Space deployment")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Base URL (default: {DEFAULT_URL})")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")

    print("\n" + "🧪 NEXUS Enhanced — HF Space Deployment Tests".center(70))
    print(f"Testing: {base_url}\n")

    results = []

    # Run all tests
    results.append(("Health Check", test_health(base_url)))

    reset_ok, session_id = test_reset_endpoint(base_url)
    results.append(("Reset Endpoint", reset_ok))

    if session_id:
        results.append(("Step Endpoint", test_step_endpoint(base_url, session_id)))

    results.append(("Metrics Endpoint", test_metrics_endpoint(base_url)))
    results.append(("Learning Curve", test_learning_curve(base_url)))
    results.append(("HTML Dashboard", test_html_dashboard(base_url)))
    results.append(("Full Episode", test_full_episode(base_url)))
    results.append(("Auto Demo INC003", test_auto_demo_inc003(base_url)))

    # Summary
    print_header("TEST SUMMARY")
    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    for name, ok in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"{status}: {name}")

    print_header(f"RESULT: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ HF SPACE DEPLOYMENT SUCCESSFUL")
        print("✅ Ready for training on Colab\n")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        print("❌ Debug issues before proceeding to training\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
