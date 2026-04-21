"""Tests for specialist agents and OversightAgent — findings, partial obs, monitoring."""

import pytest
import uuid
from server.agents import (
    L1SupportAgent, L2EngineerAgent, SREAgent, ProductManagerAgent,
    OversightAgent, get_specialist_agents, build_agent_observation,
)
from server.data_models import (
    EpisodeState, AgentDirective, AgentFinding, OversightFinding,
)
from server.incidents import get_incident
from server.tools import ToolRegistry


def make_state(case_id="INC001", step=3, phase="triage", **kwargs) -> EpisodeState:
    inc = get_incident(case_id)
    defaults = dict(
        session_id=str(uuid.uuid4()),
        incident=inc,
        step=step,
        phase=phase,
        elapsed_minutes=step * 2.0,
        expert_criteria="technical",
        schema_version="v1.0",
        done=False,
    )
    defaults.update(kwargs)
    return EpisodeState(**defaults)


def make_registry(case_id="INC001"):
    return ToolRegistry(get_incident(case_id))


def make_directive(action="check_all_alerts", parameters=None, reasoning="test") -> AgentDirective:
    return AgentDirective(action=action, parameters=parameters or {}, reasoning=reasoning)


class TestL1SupportAgent:
    def test_act_returns_agent_finding(self):
        agent = L1SupportAgent()
        state = make_state(phase="triage")
        reg = make_registry()
        finding = agent.act(state, make_directive("check_customer_reports"), reg)
        assert isinstance(finding, AgentFinding)
        assert finding.agent == "l1_support"

    def test_l1_can_access_customer_portal(self):
        agent = L1SupportAgent()
        state = make_state()
        reg = make_registry()
        finding = agent.act(state, make_directive("send_notification", {"message": "P1 in progress", "severity": "high"}), reg)
        assert finding is not None
        assert "portal" in finding.tool_used or "notification" in finding.finding.lower()

    def test_l1_cannot_access_datadog(self):
        # Role enforcement lives in ToolRegistry.call() — test it directly
        from server.tools import agent_can_use_tool
        assert not agent_can_use_tool("l1_support", "datadog")

    def test_l1_finding_has_step(self):
        agent = L1SupportAgent()
        state = make_state(step=7)
        reg = make_registry()
        finding = agent.act(state, make_directive("check_customer_reports"), reg)
        assert finding.step == 7


class TestL2EngineerAgent:
    def test_act_returns_finding(self):
        agent = L2EngineerAgent()
        state = make_state()
        reg = make_registry()
        finding = agent.act(state, make_directive("check_all_alerts"), reg)
        assert isinstance(finding, AgentFinding)
        assert finding.agent == "l2_engineer"

    def test_l2_can_access_datadog(self):
        agent = L2EngineerAgent()
        state = make_state()
        reg = make_registry()
        finding = agent.act(state, make_directive("check_all_alerts"), reg)
        assert "datadog" in finding.tool_used or "alert" in finding.finding.lower()

    def test_l2_cannot_access_jira(self):
        from server.tools import agent_can_use_tool
        assert not agent_can_use_tool("l2_engineer", "jira")

    def test_l2_check_deploy_history(self):
        agent = L2EngineerAgent()
        state = make_state("INC001")
        reg = make_registry("INC001")
        finding = agent.act(state, make_directive("check_deploy_history"), reg)
        assert isinstance(finding, AgentFinding)


class TestSREAgent:
    def test_act_returns_finding(self):
        agent = SREAgent()
        state = make_state()
        reg = make_registry()
        finding = agent.act(state, make_directive("list_runbooks"), reg)
        assert isinstance(finding, AgentFinding)
        assert finding.agent == "sre_agent"

    def test_sre_can_execute_runbook(self):
        agent = SREAgent()
        state = make_state()
        reg = make_registry("INC001")
        inc = get_incident("INC001")
        first_step = inc.available_runbooks[0].step_id
        finding = agent.act(state, make_directive("execute_runbook_step", {"step_id": first_step}), reg)
        assert isinstance(finding, AgentFinding)

    def test_sre_cannot_access_customer_portal(self):
        from server.tools import agent_can_use_tool
        assert not agent_can_use_tool("sre_agent", "customer_portal")


class TestProductManagerAgent:
    def test_act_returns_finding(self):
        agent = ProductManagerAgent()
        state = make_state()
        reg = make_registry()
        finding = agent.act(state, make_directive("track_revenue_impact"), reg)
        assert isinstance(finding, AgentFinding)
        assert finding.agent == "product_manager"

    def test_pm_can_access_jira(self):
        agent = ProductManagerAgent()
        state = make_state()
        reg = make_registry()
        finding = agent.act(state, make_directive("get_sla_status"), reg)
        assert isinstance(finding, AgentFinding)


class TestOversightAgent:
    def test_monitor_returns_list(self):
        oversight = OversightAgent()
        state = make_state(step=3)
        reg = make_registry()
        findings = oversight.monitor(state, reg)
        assert isinstance(findings, list)

    def test_monitor_violation_on_missing_notification_p1_late(self):
        oversight = OversightAgent()
        # Mitigation phase + >50k users + no notification = VIOLATION per monitor()
        state = make_state("INC001", step=12, phase="mitigation", notifications_sent=0)
        reg = make_registry("INC001")  # INC001 has 140k users affected
        findings = oversight.monitor(state, reg)
        types = [f.finding_type for f in findings]
        assert "VIOLATION" in types or "WARNING" in types

    def test_analyse_returns_list(self):
        oversight = OversightAgent()
        state = make_state(step=15, phase="postmortem", done=True)
        findings = oversight.analyse(state)
        assert isinstance(findings, list)

    def test_explain_returns_string(self):
        oversight = OversightAgent()
        state = make_state(step=10)
        result = oversight.explain(state)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_violations_on_clean_episode(self):
        oversight = OversightAgent()
        state = make_state(
            step=5, phase="triage",
            notifications_sent=1,
            first_notification_step=2,
            escalation_done=True,
        )
        reg = make_registry()
        findings = oversight.monitor(state, reg)
        violations = [f for f in findings if f.finding_type == "VIOLATION"]
        assert len(violations) == 0

    def test_oversight_finding_has_required_fields(self):
        oversight = OversightAgent()
        state = make_state("INC001", step=12, notifications_sent=0)
        reg = make_registry("INC001")
        findings = oversight.monitor(state, reg)
        if findings:
            f = findings[0]
            assert isinstance(f, OversightFinding)
            assert f.finding_type in ("VIOLATION", "WARNING")
            assert f.finding_category
            assert f.description
            assert f.step > 0

    def test_get_specialist_agents_returns_all_four(self):
        agents = get_specialist_agents()
        assert "l1_support" in agents
        assert "l2_engineer" in agents
        assert "sre_agent" in agents
        assert "product_manager" in agents


class TestPartialObservability:
    def test_build_agent_observation_l1_excludes_datadog(self):
        state = make_state()
        reg = make_registry()
        obs = build_agent_observation("l1_support", state, reg)
        assert "datadog_alerts" not in obs or obs.get("datadog_alerts") is None

    def test_build_agent_observation_l2_includes_alerts(self):
        state = make_state()
        reg = make_registry()
        obs = build_agent_observation("l2_engineer", state, reg)
        assert "alerts" in obs or "datadog" in str(obs).lower()

    def test_build_agent_observation_pm_excludes_runbooks(self):
        state = make_state()
        reg = make_registry()
        obs = build_agent_observation("product_manager", state, reg)
        # PM doesn't get runbook details
        assert "runbooks" not in obs or obs.get("runbooks") is None
