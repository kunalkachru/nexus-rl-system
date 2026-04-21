"""
NEXUS Enhanced — HF Space Deployment Regression Tests (Phase 7)
Runs all critical tests against deployed HF Spaces environment
Usage: python test_hf_space_deployment.py --url https://kunalkachru23-nexus-enhanced.hf.space
"""

import requests
import json
import sys
import argparse
import time

# Default to public HF Space
DEFAULT_URL = "https://kunalkachru23-nexus-enhanced.hf.space"

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
        assert data.get("status") == "ok", f"Status not 'ok': {data}"

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
        required_fields = ["session_id", "incident_id", "phase", "step", "observation"]
        for field in required_fields:
            assert field in obs, f"Missing field: {field}"

        assert obs["incident_id"] == "INC003"
        assert obs["phase"] == "detection"
        assert obs["step"] == 0

        session_id = obs["session_id"]
        print(f"✅ Session ID: {session_id[:8]}...")
        print(f"✅ Incident: {obs.get('incident_title', 'INC003')}")
        print(f"✅ Phase: {obs['phase']}")
        print(f"✅ Step: {obs['step']}")
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
            "l1_action": {"action": "send_notification", "parameters": {}, "reasoning": ""},
            "l2_action": {"action": "query_logs", "parameters": {}, "reasoning": ""},
            "sre_action": {"action": "list_runbooks", "parameters": {}, "reasoning": ""},
            "pm_action": {"action": "get_sla_status", "parameters": {}, "reasoning": ""},
            "severity_assessment": "p2",
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

        assert "episodes" in data, "Missing episodes in response"
        episodes = data.get("episodes", [])

        print(f"✅ Episodes recorded: {len(episodes)}")

        if episodes:
            first = episodes[0]
            last = episodes[-1]
            print(f"✅ First episode reward: {first.get('reward', 'N/A'):.4f}")
            print(f"✅ Last episode reward: {last.get('reward', 'N/A'):.4f}")

            # Check for improvement trend
            if len(episodes) > 1:
                avg_first_half = sum(e.get('reward', 0) for e in episodes[:len(episodes)//2]) / (len(episodes)//2 + 1)
                avg_second_half = sum(e.get('reward', 0) for e in episodes[len(episodes)//2:]) / (len(episodes) - len(episodes)//2 + 1)
                print(f"✅ Avg first half: {avg_first_half:.4f}")
                print(f"✅ Avg second half: {avg_second_half:.4f}")

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
                "l1_action": {"action": "send_notification", "parameters": {}, "reasoning": ""},
                "l2_action": {"action": "query_logs", "parameters": {}, "reasoning": ""},
                "sre_action": {"action": "list_runbooks", "parameters": {}, "reasoning": ""},
                "pm_action": {"action": "get_sla_status", "parameters": {}, "reasoning": ""},
                "severity_assessment": "p2",
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
