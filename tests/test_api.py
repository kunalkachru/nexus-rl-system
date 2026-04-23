"""Tests for FastAPI endpoints — full /reset → /step → /state → /metrics flow."""

import pytest
from fastapi.testclient import TestClient
from server.app import app
from server.incidents import get_incident

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_has_openenv_status(self):
        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "healthy"

    def test_health_has_version(self):
        resp = client.get("/health")
        assert "version" in resp.json()

    def test_health_tracks_active_sessions(self):
        resp = client.get("/health")
        assert "active_sessions" in resp.json()


class TestCurriculumEndpoint:
    def test_curriculum_returns_200(self):
        resp = client.get("/curriculum")
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_difficulty_tier"] == "easy"
        assert "promote_threshold" in data
        assert "recent_avg_reward" in data


class TestOpenEnvContractStubs:
    def test_metadata_endpoint(self):
        resp = client.get("/metadata")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data and "description" in data

    def test_schema_endpoint(self):
        resp = client.get("/schema")
        assert resp.status_code == 200
        data = resp.json()
        assert "action" in data and "observation" in data and "state" in data

    def test_state_root_stub(self):
        resp = client.get("/state")
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_mcp_stub_jsonrpc(self):
        resp = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("jsonrpc") == "2.0"


class TestResetEndpoint:
    def test_reset_returns_session_id(self):
        resp = client.post("/reset", json={})
        assert resp.status_code == 200
        assert "session_id" in resp.json()

    def test_reset_with_incident_id(self):
        resp = client.post("/reset", json={"incident_id": "INC001"})
        assert resp.status_code == 200
        data = resp.json()
        obs = data["observation"]
        assert obs["incident_id"] == "INC001"

    def test_reset_returns_observation(self):
        resp = client.post("/reset", json={"incident_id": "INC003"})
        obs = resp.json()["observation"]
        assert "phase" in obs
        assert "severity" in obs
        assert "incident_id" in obs

    def test_reset_inc003_has_competing_hypotheses(self):
        resp = client.post("/reset", json={"incident_id": "INC003"})
        obs = resp.json()["observation"]
        assert len(obs.get("competing_hypotheses", [])) >= 2

    def test_reset_creates_unique_session_ids(self):
        r1 = client.post("/reset", json={}).json()["session_id"]
        r2 = client.post("/reset", json={}).json()["session_id"]
        assert r1 != r2


class TestStepEndpoint:
    def _start_session(self, incident_id="INC001"):
        resp = client.post("/reset", json={"incident_id": incident_id})
        return resp.json()["session_id"]

    def test_step_returns_four_fields(self):
        sid = self._start_session()
        resp = client.post(f"/step/{sid}", json={
            "situation_assessment": "Investigating payment failures.",
            "resolution_confidence": 0.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "observation" in data
        assert "reward" in data
        assert "done" in data
        assert "info" in data

    def test_step_increments_phase(self):
        sid = self._start_session("INC003")
        for _ in range(5):
            resp = client.post(f"/step/{sid}", json={
                "situation_assessment": "Gathering evidence from all agents to identify root cause.",
                "l2_directive": {"action": "check_all_alerts", "parameters": {}, "reasoning": "sweep"},
                "resolution_confidence": 0.0,
            })
        obs = resp.json()["observation"]
        assert obs["step"] == 5

    def test_step_unknown_session_returns_404(self):
        resp = client.post("/step/nonexistent-session-id", json={})
        assert resp.status_code == 404

    def test_step_reward_nonzero_at_terminal(self):
        sid = self._start_session("INC001")
        reward = 0.0
        for _ in range(25):
            resp = client.post(f"/step/{sid}", json={
                "situation_assessment": "Identified Stripe API version mismatch. Applying fix.",
                "hypothesis": "Stripe API v2023-11 header mismatch",
                "l2_directive": {"action": "check_all_alerts", "parameters": {}, "reasoning": "verify"},
                "sre_directive": {"action": "execute_runbook_step", "parameters": {"step_id": "rb_check_logs"}, "reasoning": "runbook"},
                "l1_directive": {"action": "send_notification", "parameters": {"message": "investigating", "severity": "high"}, "reasoning": "notify"},
                "pm_directive": {"action": "track_revenue_impact", "parameters": {}, "reasoning": "sla"},
                "resolution_confidence": 0.9,
                "escalation_required": True,
            })
            data = resp.json()
            reward = data["reward"]
            if data["done"]:
                break
        assert reward > 0.0


class TestStateEndpoint:
    def test_state_returns_200(self):
        resp = client.post("/reset", json={"incident_id": "INC001"})
        sid = resp.json()["session_id"]
        state_resp = client.get(f"/state/{sid}")
        assert state_resp.status_code == 200

    def test_state_unknown_session_404(self):
        resp = client.get("/state/no-such-session")
        assert resp.status_code == 404

    def test_state_has_incident_id(self):
        resp = client.post("/reset", json={"incident_id": "INC002"})
        sid = resp.json()["session_id"]
        state = client.get(f"/state/{sid}").json()
        assert state["incident_id"] == "INC002"

    def test_state_step_zero_at_start(self):
        resp = client.post("/reset", json={"incident_id": "INC001"})
        sid = resp.json()["session_id"]
        state = client.get(f"/state/{sid}").json()
        assert state["step"] == 0


class TestIncidentsEndpoint:
    def test_incidents_returns_all_registered(self):
        resp = client.get("/incidents")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["incidents"]) == 8

    def test_incidents_detail_returns_200(self):
        resp = client.get("/incidents/INC001")
        assert resp.status_code == 200

    def test_incidents_detail_unknown_returns_404(self):
        resp = client.get("/incidents/INC999")
        assert resp.status_code == 404


class TestHistoryAndCurveEndpoints:
    def test_history_returns_200(self):
        resp = client.get("/history")
        assert resp.status_code == 200

    def test_history_has_episodes_key(self):
        resp = client.get("/history")
        assert "episodes" in resp.json()

    def test_learning_curve_returns_200(self):
        resp = client.get("/learning-curve")
        assert resp.status_code == 200

    def test_learning_curve_has_baseline(self):
        resp = client.get("/learning-curve")
        assert resp.json()["baseline"] == 0.265

    def test_learning_curve_has_rewards_list(self):
        resp = client.get("/learning-curve")
        assert "rewards" in resp.json()
        assert "rolling_avg" in resp.json()


class TestWebEndpoint:
    def test_web_returns_200(self):
        resp = client.get("/web")
        assert resp.status_code == 200

    def test_web_returns_html(self):
        resp = client.get("/web")
        assert "text/html" in resp.headers["content-type"]

    def test_web_has_nexus_title(self):
        resp = client.get("/web")
        assert "NEXUS" in resp.text

    def test_web_has_interactive_elements(self):
        resp = client.get("/web")
        # Dashboard should have interactive controls like buttons, inputs, etc.
        assert "button" in resp.text.lower() or "Start" in resp.text


class TestMetricsEndpoint:
    def test_metrics_returns_200(self):
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_metrics_has_episode_count(self):
        resp = client.get("/metrics")
        assert "episode_count" in resp.json()


class TestDemoEndpoint:
    def test_demo_inc003_completes(self):
        resp = client.post("/demo/run/INC003")
        assert resp.status_code == 200
        data = resp.json()
        assert data["incident_id"] == "INC003"
        assert "transcript" in data and len(data["transcript"]) >= 2
        assert data.get("done") is True
        assert data.get("demo_completed") is True
        assert data.get("reward_breakdown") is not None


class TestFullEpisodeFlow:
    def test_full_reset_step_state_flow(self):
        """End-to-end: reset → multiple steps → state shows accumulated findings."""
        # Reset
        reset_resp = client.post("/reset", json={"incident_id": "INC003"})
        assert reset_resp.status_code == 200
        sid = reset_resp.json()["session_id"]

        # Step 1 — detection
        client.post(f"/step/{sid}", json={
            "situation_assessment": "Memory pressure on recommendation-service. High heap usage. Dispatching L2 to investigate.",
            "l2_directive": {"action": "check_all_alerts", "parameters": {}, "reasoning": "sweep"},
            "l1_directive": {"action": "send_notification", "parameters": {"message": "P1 in progress", "severity": "high"}, "reasoning": "notify"},
            "resolution_confidence": 0.0,
        })

        # Step 2 — triage
        client.post(f"/step/{sid}", json={
            "situation_assessment": "L2 confirms heap at 14GB vs 8GB limit. OOM restarts every 90s.",
            "hypothesis": "Memory leak in recommendation-service ML model",
            "l2_directive": {"action": "check_deploy_history", "parameters": {}, "reasoning": "recent deploys"},
            "resolution_confidence": 0.1,
        })

        # State check
        state = client.get(f"/state/{sid}").json()
        assert state["step"] == 2
        assert state["incident_id"] == "INC003"
        assert state["notifications_sent"] >= 0  # L1 may have sent

        # Reward check (mid-episode)
        reward_resp = client.get(f"/reward/{sid}")
        assert reward_resp.status_code == 200
        rb = reward_resp.json()
        assert "total" in rb
        assert rb["total"] >= 0.0

    def test_step_until_done_records_episode_for_metrics(self):
        """
        Full episode via POST /step (not /demo/run) must append completion so
        /metrics and /learning-curve episode_count reflect real training traffic.
        INC008 has the smallest max_steps (18) in the library for a bounded loop.
        """
        before = client.get("/metrics").json()["episode_count"]

        reset_resp = client.post(
            "/reset",
            json={"incident_id": "INC008", "run_id": "pytest_full_episode_metrics"},
        )
        assert reset_resp.status_code == 200
        sid = reset_resp.json()["session_id"]
        cap = get_incident("INC008").max_steps + 5

        minimal_action = {
            "situation_assessment": "Test harness: advancing episode until termination.",
            "resolution_confidence": 0.0,
        }

        last_done = False
        for _ in range(cap):
            step_resp = client.post(f"/step/{sid}", json=minimal_action)
            assert step_resp.status_code == 200, step_resp.text
            body = step_resp.json()
            last_done = body.get("done") is True
            if last_done:
                break

        assert last_done is True
        state = client.get(f"/state/{sid}").json()
        assert state["done"] is True

        assert client.get("/metrics").json()["episode_count"] == before + 1

        scoped = client.get(
            "/metrics", params={"run_id": "pytest_full_episode_metrics"}
        ).json()
        assert scoped["episode_count"] >= 1

        curve = client.get(
            "/learning-curve", params={"run_id": "pytest_full_episode_metrics"}
        ).json()
        assert curve.get("episode_count", 0) >= 1
        assert len(curve.get("rewards", [])) >= 1
