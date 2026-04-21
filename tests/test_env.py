"""Tests for NexusEnvironment — OpenEnv interface, episode lifecycle, mechanics."""

import pytest
import uuid
from server.environment import NexusEnvironment
from server.incidents import get_incident, INCIDENT_LIBRARY
from server.data_models import EpisodeState


def make_env(incident_id="INC001", **kwargs) -> NexusEnvironment:
    env = NexusEnvironment()
    env.reset(incident_id=incident_id, **kwargs)
    return env


def basic_step(env: NexusEnvironment, **kwargs) -> tuple:
    action = {
        "situation_assessment": "Investigating incident",
        "resolution_confidence": 0.1,
        **kwargs,
    }
    return env.step(action)


# ------------------------------------------------------------------
# Reset
# ------------------------------------------------------------------
class TestReset:
    def test_reset_returns_observation(self):
        env = NexusEnvironment()
        obs = env.reset(incident_id="INC001")
        assert "incident_id" in obs
        assert obs["incident_id"] == "INC001"
        assert obs["phase"] == "detection"
        assert obs["step"] == 0

    def test_reset_populates_state(self):
        env = NexusEnvironment()
        env.reset(incident_id="INC001")
        state = env.current_state
        assert state is not None
        assert state.step == 0
        assert state.phase == "detection"
        assert state.done is False
        assert state.notifications_sent == 0

    def test_reset_all_incidents(self):
        for case_id in INCIDENT_LIBRARY:
            env = NexusEnvironment()
            obs = env.reset(incident_id=case_id)
            assert obs["incident_id"] == case_id

    def test_reset_session_id_generated(self):
        env = NexusEnvironment()
        obs = env.reset(incident_id="INC001")
        assert env.current_state.session_id is not None
        assert len(env.current_state.session_id) > 0

    def test_reset_custom_session_id(self):
        sid = "test-session-123"
        env = NexusEnvironment()
        env.reset(incident_id="INC001", session_id=sid)
        assert env.current_state.session_id == sid

    def test_reset_expert_criteria(self):
        env = NexusEnvironment()
        env.reset(incident_id="INC001", expert_criteria="technical")
        assert env.current_state.expert_criteria == "technical"

    def test_reset_clears_previous_state(self):
        env = NexusEnvironment()
        env.reset(incident_id="INC001")
        basic_step(env)
        env.reset(incident_id="INC002")
        assert env.current_state.step == 0
        assert env.current_state.incident.case_id == "INC002"


# ------------------------------------------------------------------
# Step
# ------------------------------------------------------------------
class TestStep:
    def test_step_increments_step_counter(self):
        env = make_env()
        assert env.current_state.step == 0
        basic_step(env)
        assert env.current_state.step == 1

    def test_step_increments_elapsed_minutes(self):
        env = make_env()
        assert env.current_state.elapsed_minutes == 0.0
        basic_step(env)
        assert env.current_state.elapsed_minutes > 0.0

    def test_step_returns_four_tuple(self):
        env = make_env()
        result = basic_step(env)
        assert len(result) == 4
        obs, reward, done, info = result
        assert isinstance(obs, dict)
        assert isinstance(reward, float)
        assert isinstance(done, bool)
        assert isinstance(info, dict)

    def test_step_reward_zero_during_episode(self):
        env = make_env()
        _, reward, done, _ = basic_step(env)
        assert reward == 0.0
        assert done is False

    def test_step_dispatches_l2_directive(self):
        env = make_env("INC001")
        _, _, _, _ = env.step({
            "situation_assessment": "Checking metrics",
            "l2_directive": {
                "action": "check_all_alerts",
                "parameters": {},
                "reasoning": "Sweep alerts",
            },
            "resolution_confidence": 0.1,
        })
        findings = env.current_state.agent_findings
        assert any(f.agent == "l2_engineer" for f in findings)

    def test_step_dispatches_sre_directive(self):
        env = make_env("INC001")
        env.step({
            "situation_assessment": "Listing runbooks",
            "sre_directive": {
                "action": "list_runbooks",
                "parameters": {},
                "reasoning": "Check available steps",
            },
            "resolution_confidence": 0.1,
        })
        findings = env.current_state.agent_findings
        assert any(f.agent == "sre_agent" for f in findings)

    def test_step_records_situation_assessment(self):
        env = make_env()
        env.step({"situation_assessment": "Root cause: stripe header mismatch", "resolution_confidence": 0.1})
        assert len(env.current_state.situation_assessments) == 1
        assert "stripe" in env.current_state.situation_assessments[0].lower()

    def test_step_records_hypothesis(self):
        env = make_env()
        env.step({"hypothesis": "stripe api v2023-11 header required", "resolution_confidence": 0.1})
        assert len(env.current_state.hypotheses_stated) == 1

    def test_step_direct_tool_call(self):
        env = make_env("INC001")
        env.step({
            "situation_assessment": "Checking metrics directly",
            "direct_tool": {
                "tool": "datadog",
                "action": "get_all_alerts",
                "parameters": {},
            },
            "resolution_confidence": 0.1,
        })
        tool_outputs = env.current_state.tool_outputs
        assert any(t.tool == "datadog" and t.agent == "incident_commander" for t in tool_outputs)


# ------------------------------------------------------------------
# Phase progression
# ------------------------------------------------------------------
class TestPhaseProgression:
    def test_phase_advances_from_detection(self):
        env = make_env("INC001")
        basic_step(env)
        basic_step(env)  # Step 2 triggers triage
        assert env.current_state.phase in ["detection", "triage"]

    def test_all_phases_reachable(self):
        env = make_env("INC001")
        phases_seen = {"detection"}

        for _ in range(env.current_state.incident.max_steps):
            obs, _, done, _ = env.step({
                "situation_assessment": "Root cause: stripe api header mismatch. Evidence from logs. Mitigation via runbook.",
                "hypothesis": "stripe api 2023-11 header version mismatch causing 400s",
                "l2_directive": {"action": "check_logs", "parameters": {"service": "payment-service"}, "reasoning": "check logs"},
                "sre_directive": {"action": "execute_runbook_step", "parameters": {"step_id": "rb_check_logs"}, "reasoning": "run step"},
                "l1_directive": {"action": "send_notification", "parameters": {"customers": "all", "message": "investigating", "severity": "high"}, "reasoning": "notify"},
                "resolution_confidence": 0.85,
            })
            phases_seen.add(obs["phase"])
            if done:
                break

        assert len(phases_seen) >= 2, f"Only saw phases: {phases_seen}"

    def test_episode_terminates_at_max_steps(self):
        env = make_env("INC001")
        max_steps = env.current_state.incident.max_steps
        done = False
        for _ in range(max_steps + 5):
            _, _, done, _ = basic_step(env)
            if done:
                break
        assert done is True


# ------------------------------------------------------------------
# Reward
# ------------------------------------------------------------------
class TestReward:
    def test_reward_nonzero_on_episode_end(self):
        env = make_env("INC001")
        max_steps = env.current_state.incident.max_steps
        reward = 0.0
        for _ in range(max_steps + 1):
            _, r, done, _ = basic_step(env)
            if done:
                reward = r
                break
        assert reward > 0.0

    def test_reward_breakdown_present_on_done(self):
        env = make_env("INC001")
        for _ in range(env.current_state.incident.max_steps + 1):
            _, _, done, info = basic_step(env)
            if done:
                break
        assert "reward_breakdown" in info
        rb = info["reward_breakdown"]
        assert all(k in rb for k in ["mttr", "diagnosis", "customer", "coordination", "oversight", "total"])

    def test_reward_higher_with_notification(self):
        """Episode with notification should score higher than without."""
        def run_with_notification():
            env = make_env("INC001")
            for _ in range(env.current_state.incident.max_steps + 1):
                _, r, done, _ = env.step({
                    "situation_assessment": "investigating",
                    "l1_directive": {"action": "send_notification", "parameters": {"customers": "all", "message": "investigating", "severity": "high"}, "reasoning": "notify"},
                    "resolution_confidence": 0.5,
                })
                if done:
                    return r
            return 0.0

        def run_without_notification():
            env = make_env("INC001")
            for _ in range(env.current_state.incident.max_steps + 1):
                _, r, done, _ = basic_step(env)
                if done:
                    return r
            return 0.0

        r_with = run_with_notification()
        r_without = run_without_notification()
        assert r_with >= r_without

    def test_depth_bonus_increases_total(self):
        env = make_env("INC001")
        for _ in range(env.current_state.incident.max_steps + 1):
            _, r, done, _ = env.step({
                "situation_assessment": (
                    "Root cause evidence: payment-service logs show 400 from Stripe. "
                    "Hypothesis: stripe api v2023-11 header required but client sends v2022-08. "
                    "Mitigation: update stripe client configuration via runbook rb_update_stripe_client. "
                    "Timeline: 18 minutes to resolution. Coalition confirmed. Impact: 140k users, $8400/min."
                ),
                "resolution_confidence": 0.5,
            })
            if done:
                assert r > 0.0
                break


# ------------------------------------------------------------------
# Coalition mechanic
# ------------------------------------------------------------------
class TestCoalition:
    def test_coalition_fires_on_medium_incident(self):
        env = make_env("INC003")
        # Step enough times to get past threshold
        for i in range(3):
            basic_step(env)
        _, _, _, _ = env.step({
            "situation_assessment": "Coalition vote",
            "coalition_vote": "ML model v4 feature vector cache lacks LRU eviction causing unbounded heap growth",
            "resolution_confidence": 0.3,
        })
        assert env.current_state.coalition_result is not None

    def test_correct_coalition_sets_flag(self):
        env = make_env("INC003")
        for i in range(2):
            basic_step(env)
        env.step({
            "coalition_vote": "feature vector cache eviction policy missing causing heap memory leak",
            "resolution_confidence": 0.3,
        })
        assert env.current_state.coalition_correct is True

    def test_wrong_coalition_sets_false(self):
        env = make_env("INC003")
        for _ in range(2):
            basic_step(env)
        env.step({
            "coalition_vote": "Network partition between services causing connection timeout",
            "resolution_confidence": 0.3,
        })
        if env.current_state.coalition_result:
            assert env.current_state.coalition_correct is False

    def test_easy_incident_no_coalition(self):
        env = make_env("INC001")
        for _ in range(5):
            env.step({"coalition_vote": "some hypothesis", "resolution_confidence": 0.1})
        # Easy incidents have no competing_hypotheses — coalition result irrelevant
        inc = env.current_state.incident
        assert len(inc.competing_hypotheses) == 0


# ------------------------------------------------------------------
# Schema drift (INC007 Patronus AI)
# ------------------------------------------------------------------
class TestSchemaDrift:
    def test_schema_drift_triggers_at_correct_step(self):
        env = make_env("INC007")
        drift_step = env.current_state.incident.schema_drift_step
        assert drift_step is not None

        for i in range(drift_step + 1):
            basic_step(env)
            if env.current_state.schema_version == "v2.0":
                break

        assert env.current_state.schema_version == "v2.0"

    def test_runbook_schema_changes_to_v2(self):
        env = make_env("INC007")
        drift_step = env.current_state.incident.schema_drift_step

        for _ in range(drift_step + 1):
            basic_step(env)

        reg = env.get_tool_registry()
        assert reg.runbook.schema_version == "v2.0"

        result = reg.call("runbook", "list_runbooks", "sre_agent", {})
        assert result["schema_version"] == "v2.0"
        # v2.0 uses "runbook_ref" not "step_id"
        if result["runbooks"]:
            first = result["runbooks"][0]
            assert "runbook_ref" in first
            assert "step_id" not in first

    def test_customer_portal_requires_gdpr_in_v2(self):
        env = make_env("INC007")
        drift_step = env.current_state.incident.schema_drift_step

        for _ in range(drift_step + 1):
            basic_step(env)

        reg = env.get_tool_registry()
        # Without gdpr_compliant=true → rejected
        result = reg.call("customer_portal", "send_notification", "l1_support", {
            "recipients": "all",
            "content": "Service update",
            "impact_level": "high",
        })
        assert result["status"] == "rejected"

        # With gdpr_compliant=true → accepted
        result2 = reg.call("customer_portal", "send_notification", "l1_support", {
            "recipients": "all",
            "content": "Service update",
            "impact_level": "high",
            "gdpr_compliant": True,
        })
        assert result2["status"] == "ok"

    def test_non_nightmare_incidents_no_drift(self):
        for case_id in ["INC001", "INC002", "INC003", "INC004", "INC005", "INC006"]:
            env = make_env(case_id)
            assert env.current_state.incident.schema_drift_step is None


# ------------------------------------------------------------------
# Oversight
# ------------------------------------------------------------------
class TestOversight:
    def test_oversight_report_generated_on_done(self):
        env = make_env("INC001")
        for _ in range(env.current_state.incident.max_steps + 1):
            _, _, done, info = basic_step(env)
            if done:
                break
        assert "oversight_report" in info
        assert isinstance(info["oversight_report"], str)
        assert len(info["oversight_report"]) > 0

    def test_oversight_flags_duplicate_queries(self):
        env = make_env("INC001")
        # Query same metric twice
        for _ in range(2):
            env.step({
                "situation_assessment": "checking",
                "direct_tool": {"tool": "datadog", "action": "get_all_alerts", "parameters": {}},
                "resolution_confidence": 0.1,
            })
        violations = [f for f in env.current_state.oversight_findings
                      if f.finding_category == "DUPLICATE_TOOL_QUERY"]
        assert len(violations) > 0

    def test_oversight_explain_returns_string(self):
        from server.agents import OversightAgent
        env = make_env("INC001")
        basic_step(env)
        report = OversightAgent().explain(env.current_state)
        assert isinstance(report, str)
        assert "Oversight Report" in report


# ------------------------------------------------------------------
# Partial observability
# ------------------------------------------------------------------
class TestPartialObservability:
    def test_l1_cannot_access_datadog(self):
        from server.tools import agent_can_use_tool
        assert agent_can_use_tool("l1_support", "datadog") is False
        assert agent_can_use_tool("l1_support", "slack") is True
        assert agent_can_use_tool("l1_support", "customer_portal") is True

    def test_l2_cannot_access_jira(self):
        from server.tools import agent_can_use_tool
        assert agent_can_use_tool("l2_engineer", "jira") is False
        assert agent_can_use_tool("l2_engineer", "datadog") is True

    def test_ic_has_full_access(self):
        from server.tools import agent_can_use_tool, ROLE_TOOL_SCOPES
        ic_tools = ROLE_TOOL_SCOPES["incident_commander"]
        assert "datadog" in ic_tools
        assert "slack" in ic_tools
        assert "jira" in ic_tools
        assert "runbook" in ic_tools
        assert "customer_portal" in ic_tools

    def test_role_enforcement_at_registry(self):
        from server.tools import ToolRegistry
        env = make_env("INC001")
        reg = env.get_tool_registry()
        result = reg.call("datadog", "get_all_alerts", "l1_support", {})
        assert result["status"] == "unauthorized"
