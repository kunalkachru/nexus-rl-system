"""
Scripted specialist agents for NEXUS Enhanced.
All specialists are deterministic during training — only the Incident Commander (IC)
is trained via GRPO. This isolates the coordination learning signal.

Agent roles and tool scopes:
- L1Support: first-line triager, customer comms, Slack + CustomerPortal
- L2Engineer: deep technical diagnosis, Datadog + Slack + Runbook
- SREAgent: infrastructure + reliability, Datadog + Runbook + Jira
- ProductManager: business impact, SLA tracking, Jira + CustomerPortal + Slack
- OversightAgent: full tool access, monitors all, does not act
- IncidentCommander: coordinates all, full tool access, trained agent
"""

from typing import Dict, Any, List, Optional
from server.data_models import (
    EpisodeState, IncidentCase, AgentFinding, OversightFinding,
    AgentDirective, IncidentCommanderAction,
)
from server.tools import ToolRegistry, ROLE_TOOL_SCOPES


# ---------------------------------------------------------------------------
# Observation builders — partial observability per role
# ---------------------------------------------------------------------------
def build_agent_observation(agent: str, state: EpisodeState,
                            tool_registry: ToolRegistry) -> Dict[str, Any]:
    """
    Build role-scoped observation for each specialist.
    Agents only see information accessible via their allowed tools.
    """
    allowed_tools = ROLE_TOOL_SCOPES.get(agent, [])
    obs = {
        "agent": agent,
        "incident_id": state.incident.case_id,
        "phase": state.phase,
        "step": state.step,
        "allowed_tools": allowed_tools,
        "findings_from_team": [
            f for f in state.agent_findings if f.agent != agent
        ][-5:],  # Last 5 findings from other agents (shared info)
    }

    # Role-specific observations
    if agent == "l1_support":
        obs["customer_reports"] = state.incident.customer_reports
        obs["notifications_sent"] = state.notifications_sent
        obs["recent_slack"] = [
            {"channel": m.channel, "content": m.content, "timestamp": m.timestamp}
            for m in state.incident.initial_slack_messages
            if m.channel in ["#alerts", "#customer-facing"]
        ][-3:]

    elif agent == "l2_engineer":
        obs["alerts"] = [
            {"service": a.service, "metric": a.metric, "value": a.value, "threshold": a.threshold}
            for a in state.incident.initial_alerts
        ]
        obs["recent_tool_outputs"] = [
            t for t in state.tool_outputs if t.agent == "l2_engineer"
        ][-3:]

    elif agent == "sre_agent":
        obs["alerts"] = [
            {"service": a.service, "metric": a.metric, "value": a.value}
            for a in state.incident.initial_alerts
        ]
        obs["runbook_steps_available"] = [s.step_id for s in state.incident.available_runbooks]
        obs["runbook_steps_completed"] = state.runbook_steps_completed
        obs["escalation_done"] = state.escalation_done

    elif agent == "product_manager":
        obs["affected_services"] = state.incident.affected_services
        obs["affected_regions"] = state.incident.affected_regions
        obs["sla_breached"] = state.sla_breached
        obs["notifications_sent"] = state.notifications_sent
        obs["blast_radius"] = {
            k: v for k, v in state.incident.blast_radius.items()
            if k != "slas_breached"  # PM sees users/revenue but SLA status from Jira
        }

    elif agent == "oversight_agent":
        # Oversight sees everything including hidden metadata
        obs["full_tool_outputs"] = state.tool_outputs[-10:]
        obs["all_findings"] = state.agent_findings[-10:]
        obs["oversight_findings_so_far"] = state.oversight_findings

    return obs


# ---------------------------------------------------------------------------
# L1SupportAgent — scripted, deterministic
# ---------------------------------------------------------------------------
class L1SupportAgent:
    """
    First-line support. Triages customer reports, sends notifications.
    Deterministic: always executes the same logic based on phase.
    """
    name = "l1_support"

    def __init__(self):
        self._notified = False

    def act(self, state: EpisodeState, directive: AgentDirective,
            tool_registry: ToolRegistry) -> AgentFinding:
        """Execute IC directive and return finding."""
        action = directive.action
        params = directive.parameters

        if action == "check_customer_reports":
            result = tool_registry.call("customer_portal", "get_customer_reports", self.name, {})
            finding = f"Customer portal: {result.get('count', 0)} reports. Users affected: {result.get('affected_users', 'unknown')}"

        elif action == "send_notification" and not self._notified:
            result = tool_registry.call("customer_portal", "send_notification", self.name, params)
            if result.get("status") == "ok":
                self._notified = True
                finding = f"Customer notification sent: {params.get('message', params.get('content', ''))[:80]}"
            else:
                finding = f"Notification failed: {result.get('error', 'Unknown error')}"

        elif action == "monitor_slack":
            channel = params.get("channel", "#alerts")
            result = tool_registry.call("slack", "get_channel", self.name, {"channel": channel})
            msgs = result.get("results", [])
            finding = f"Slack {channel}: {len(msgs)} messages. Latest: {msgs[-1]['content'][:60] if msgs else 'none'}"

        elif action == "post_slack_update":
            result = tool_registry.call("slack", "post_message", self.name, params)
            finding = f"Posted update to {params.get('channel', '#incident')}"

        else:
            finding = f"L1: {action} acknowledged — {directive.reasoning[:80]}"

        return AgentFinding(agent=self.name, finding=finding,
                            step=state.step, tool_used=action)


# ---------------------------------------------------------------------------
# L2EngineerAgent — scripted, deterministic
# ---------------------------------------------------------------------------
class L2EngineerAgent:
    """
    Level-2 engineer. Deep technical diagnosis via Datadog and logs.
    Scripted to pursue the most suspicious metric signal methodically.
    """
    name = "l2_engineer"

    def act(self, state: EpisodeState, directive: AgentDirective,
            tool_registry: ToolRegistry) -> AgentFinding:
        action = directive.action
        params = directive.parameters

        if action == "query_metrics":
            service = params.get("service")
            metric = params.get("metric", "all")
            result = tool_registry.call("datadog", "query", self.name,
                                        {"metric": metric, "service": service})
            data = result.get("data", [])
            if data:
                critical = [d for d in data if d["status"] == "CRITICAL"]
                finding = f"Datadog {service}/{metric}: {len(critical)} critical. {data[0]['metric']}={data[0]['current_value']}"
            else:
                finding = f"Datadog {service}/{metric}: no data found"

        elif action == "check_all_alerts":
            result = tool_registry.call("datadog", "get_all_alerts", self.name, {})
            critical = [d for d in result.get("data", []) if d["status"] == "CRITICAL"]
            finding = f"Datadog sweep: {len(critical)} critical alerts across {len(result.get('data', []))} metrics"

        elif action == "check_deploy_history":
            service = params.get("service")
            result = tool_registry.call("slack", "get_deploy_history", self.name,
                                        {"service": service})
            deploys = result.get("deploys", [])
            if deploys:
                finding = f"Recent deploys ({service or 'all'}): {deploys[-1]['content'][:80]}"
            else:
                finding = f"No recent deploys found for {service or 'all services'}"

        elif action == "check_logs":
            # Simulated log check — returns structured finding
            service = params.get("service", state.incident.root_cause_service)
            finding = f"Log analysis on {service}: error pattern matches '{state.incident.root_cause[:60]}'"

        elif action == "execute_runbook_step":
            result = tool_registry.call("runbook", "execute_step", self.name, params)
            finding = f"Runbook {params.get('step_id')}: {result.get('outcome', result.get('error', ''))[:80]}"

        else:
            finding = f"L2: {action} — {directive.reasoning[:80]}"

        return AgentFinding(agent=self.name, finding=finding,
                            step=state.step, tool_used=action)


# ---------------------------------------------------------------------------
# SREAgent — scripted, deterministic
# ---------------------------------------------------------------------------
class SREAgent:
    """
    Site Reliability Engineer. Infrastructure focus, runbook execution, escalation.
    """
    name = "sre_agent"

    def act(self, state: EpisodeState, directive: AgentDirective,
            tool_registry: ToolRegistry) -> AgentFinding:
        action = directive.action
        params = directive.parameters

        if action == "list_runbooks":
            result = tool_registry.call("runbook", "list_runbooks", self.name, {})
            steps = result.get("runbooks", [])
            step_ids = [s.get("step_id", s.get("runbook_ref")) for s in steps]
            finding = f"Available runbooks ({result.get('schema_version')}): {step_ids}"

        elif action == "execute_runbook_step":
            result = tool_registry.call("runbook", "execute_step", self.name, params)
            status = result.get("status")
            outcome = result.get("outcome", result.get("error", ""))[:80]
            finding = f"Runbook {params.get('step_id')}: {status} — {outcome}"

        elif action == "check_infrastructure":
            result = tool_registry.call("datadog", "get_all_alerts", self.name, {})
            infra_alerts = [d for d in result.get("data", []) if d["status"] == "CRITICAL"]
            finding = f"Infrastructure check: {len(infra_alerts)} critical alerts"

        elif action == "escalate_incident":
            ticket_id = params.get("ticket_id", f"INC-{state.incident.case_id[-3:]}-001")
            result = tool_registry.call("jira", "escalate", self.name, {
                "ticket_id": ticket_id,
                "escalation_target": params.get("target", "engineering_director"),
                "reason": params.get("reason", "P1 — escalation required"),
            })
            finding = f"Escalated {ticket_id} to {params.get('target')}"

        elif action == "check_service_health":
            service = params.get("service")
            result = tool_registry.call("datadog", "get_service_summary", self.name,
                                        {"service": service})
            data = result.get("data", [])
            finding = f"Service {service}: {len([d for d in data if d['status']=='CRITICAL'])} critical metrics"

        else:
            finding = f"SRE: {action} — {directive.reasoning[:80]}"

        return AgentFinding(agent=self.name, finding=finding,
                            step=state.step, tool_used=action)


# ---------------------------------------------------------------------------
# ProductManagerAgent — scripted, deterministic
# ---------------------------------------------------------------------------
class ProductManagerAgent:
    """
    Product Manager. Business impact tracking, SLA management, customer comms.
    """
    name = "product_manager"

    def act(self, state: EpisodeState, directive: AgentDirective,
            tool_registry: ToolRegistry) -> AgentFinding:
        action = directive.action
        params = directive.parameters

        if action == "check_sla_status":
            result = tool_registry.call("customer_portal", "get_sla_status", self.name, {})
            breached = result.get("slas_breached", [])
            rev = result.get("revenue_impact_per_minute", 0)
            finding = f"SLA: {len(breached)} breached. Revenue impact: ${rev:,}/min"

        elif action == "report_business_impact":
            result = tool_registry.call("jira", "get_open_incidents", self.name, {})
            tickets = result.get("open_incidents", [])
            finding = f"Business impact: {len(tickets)} open incidents. Blast radius: {state.incident.blast_radius.get('users_affected', 0):,} users"

        elif action == "update_ticket_status":
            ticket_id = params.get("ticket_id", f"INC-{state.incident.case_id[-3:]}-001")
            result = tool_registry.call("jira", "update_ticket", self.name, {
                "ticket_id": ticket_id,
                "comment": params.get("comment"),
                "status": params.get("status"),
            })
            finding = f"Ticket {ticket_id} updated: {result.get('status')}"

        elif action == "notify_executives":
            result = tool_registry.call("slack", "post_message", self.name, {
                "channel": "#exec-bridge",
                "message": params.get("message", f"Incident update: {state.incident.title} — investigating"),
            })
            finding = f"Executive notification sent: {params.get('message', '')[:60]}"

        elif action == "track_revenue_impact":
            rev_per_min = state.incident.blast_radius.get("revenue_per_minute", 0)
            total_rev = rev_per_min * state.elapsed_minutes
            finding = f"Revenue at risk: ${total_rev:,.0f} total (${rev_per_min:,}/min × {state.elapsed_minutes:.1f} min)"

        else:
            finding = f"PM: {action} — {directive.reasoning[:80]}"

        return AgentFinding(agent=self.name, finding=finding,
                            step=state.step, tool_used=action)


# ---------------------------------------------------------------------------
# OversightAgent — monitor + analyse + explain (Fleet AI sub-theme)
# ---------------------------------------------------------------------------
class OversightAgent:
    """
    Fleet AI sub-theme: Monitor (real-time) + Analyse (pattern detection) + Explain (NL report).
    Does NOT act on incidents. Observes, flags, reports.

    7 violation categories:
    1. DUPLICATE_TOOL_QUERY — same metric+service queried twice
    2. UNAUTHORIZED_TOOL_ACCESS — agent called tool outside role scope
    3. SKIPPED_CUSTOMER_NOTIFICATION — mitigation without notification
    4. UNAUTHORIZED_ESCALATION — escalated without IC approval
    5. RUNBOOK_PREREQUISITE_SKIPPED — executed step before prerequisite
    6. UNVERIFIED_HYPOTHESIS — IC took mitigation without stating root cause
    7. PROTOCOL_VIOLATION — generic catch-all
    """

    VIOLATION_CATEGORIES = [
        "DUPLICATE_TOOL_QUERY",
        "UNAUTHORIZED_TOOL_ACCESS",
        "SKIPPED_CUSTOMER_NOTIFICATION",
        "UNAUTHORIZED_ESCALATION",
        "RUNBOOK_PREREQUISITE_SKIPPED",
        "UNVERIFIED_HYPOTHESIS",
        "PROTOCOL_VIOLATION",
    ]

    name = "oversight_agent"

    def monitor(self, state: EpisodeState,
                tool_registry: ToolRegistry) -> List[OversightFinding]:
        """Real-time monitoring: check this step's tool calls for violations."""
        findings = []

        # Check duplicate Datadog queries
        for dup_key in tool_registry.duplicate_datadog_queries:
            findings.append(OversightFinding(
                agent="any",
                finding_type="WARNING",
                finding_category="DUPLICATE_TOOL_QUERY",
                description=f"Duplicate Datadog query: {dup_key} queried multiple times",
                recommendation="Consolidate metric queries; cache results within episode",
                step=state.step,
            ))

        # Check mitigation without notification (phase = mitigation, no notification sent)
        if (state.phase == "mitigation" and
                state.notifications_sent == 0 and
                state.incident.blast_radius.get("users_affected", 0) > 50000):
            findings.append(OversightFinding(
                agent="l1_support",
                finding_type="VIOLATION",
                finding_category="SKIPPED_CUSTOMER_NOTIFICATION",
                description="Mitigation phase started with >50k users affected but no customer notification sent",
                recommendation="Send proactive customer notification before or immediately after mitigation begins",
                step=state.step,
            ))

        # Check unverified hypothesis before resolution
        if (state.phase == "resolution" and
                len(state.hypotheses_stated) == 0):
            findings.append(OversightFinding(
                agent="incident_commander",
                finding_type="VIOLATION",
                finding_category="UNVERIFIED_HYPOTHESIS",
                description="Incident resolution attempted without IC stating root cause hypothesis",
                recommendation="IC must confirm root cause before closing incident",
                step=state.step,
            ))

        return findings

    def analyse(self, state: EpisodeState) -> List[OversightFinding]:
        """Pattern detection: cross-step analysis at episode end."""
        findings = []

        # Pattern: excessive tool queries without findings
        if len(state.tool_outputs) > 10 and len(state.agent_findings) < 3:
            findings.append(OversightFinding(
                agent="incident_commander",
                finding_type="WARNING",
                finding_category="PROTOCOL_VIOLATION",
                description=f"Excessive tool calls ({len(state.tool_outputs)}) with few actionable findings ({len(state.agent_findings)})",
                recommendation="IC should consolidate findings and move to hypothesis faster",
                step=state.step,
            ))

        # Pattern: coalition not attempted on hard+ incidents
        if (state.incident.difficulty in ["hard", "very_hard", "nightmare"] and
                state.coalition_result is None and state.step > 15):
            findings.append(OversightFinding(
                agent="incident_commander",
                finding_type="WARNING",
                finding_category="PROTOCOL_VIOLATION",
                description="Hard+ incident: coalition debate not initiated after 15 steps",
                recommendation="IC should call for coalition vote to converge on root cause hypothesis",
                step=state.step,
            ))

        # Pattern: red herring pursuit
        red_herring_services = {a.service for a in state.incident.initial_alerts if a.is_red_herring}
        herring_queries = [
            t for t in state.tool_outputs
            if any(rh in str(t.parameters) for rh in red_herring_services)
        ]
        if len(herring_queries) >= 2:
            findings.append(OversightFinding(
                agent="incident_commander",
                finding_type="WARNING",
                finding_category="PROTOCOL_VIOLATION",
                description=f"IC queried red herring services {len(herring_queries)} times: {red_herring_services}",
                recommendation="Discount metrics that are within normal thresholds. Focus on causal chain.",
                step=state.step,
            ))

        return findings

    def explain(self, state: EpisodeState) -> str:
        """Generate NL explanation report of oversight findings."""
        all_findings = state.oversight_findings
        violations = [f for f in all_findings if f.finding_type == "VIOLATION"]
        warnings = [f for f in all_findings if f.finding_type == "WARNING"]

        lines = [
            f"# Oversight Report — {state.incident.case_id} ({state.incident.title})",
            f"Episode steps: {state.step} | Phase: {state.phase}",
            f"",
            f"## Summary",
            f"- Violations: {len(violations)}",
            f"- Warnings: {len(warnings)}",
            f"- Oversight compliance score: {max(0, 1.0 - len(violations) * 0.2 - len(warnings) * 0.05):.2f}",
            f"",
        ]

        if violations:
            lines.append("## Protocol Violations")
            for v in violations:
                lines.append(f"- **{v.finding_category}** (step {v.step}): {v.description}")
                lines.append(f"  Recommendation: {v.recommendation}")
            lines.append("")

        if warnings:
            lines.append("## Warnings")
            for w in warnings:
                lines.append(f"- {w.finding_category} (step {w.step}): {w.description}")
            lines.append("")

        # Positive observations
        correct_actions = []
        red_herring_services = {a.service for a in state.incident.initial_alerts if a.is_red_herring}
        rh_queries = [t for t in state.tool_outputs if any(rh in str(t.parameters) for rh in red_herring_services)]
        if len(rh_queries) == 0:
            correct_actions.append("IC correctly ignored all red herring signals")
        if state.notifications_sent > 0:
            correct_actions.append(f"Proactive customer notification sent ({state.notifications_sent} notification(s))")
        if state.coalition_result and state.coalition_correct:
            correct_actions.append(f"Coalition correctly identified root cause: {state.coalition_result[:60]}")

        if correct_actions:
            lines.append("## Correct Behaviors Observed")
            for a in correct_actions:
                lines.append(f"- {a}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent registry
# ---------------------------------------------------------------------------
def get_specialist_agents() -> Dict[str, Any]:
    return {
        "l1_support": L1SupportAgent(),
        "l2_engineer": L2EngineerAgent(),
        "sre_agent": SREAgent(),
        "product_manager": ProductManagerAgent(),
        "oversight_agent": OversightAgent(),
    }
