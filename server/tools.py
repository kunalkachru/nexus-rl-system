"""
Tool simulators for NEXUS Enhanced.
Each tool: __init__(incident: IncidentCase), stateful, returns structured dicts.
Partial observability: each specialist only sees tools within its role scope.
Patronus AI schema drift: SimRunbook and SimCustomerPortal handle v1.0 vs v2.0 schema.
"""

from typing import Dict, Any, Optional, List
from server.data_models import IncidentCase, DatadogAlert, SlackMessage, RunbookStep


# ---------------------------------------------------------------------------
# Role scopes — which tools each agent can query
# ---------------------------------------------------------------------------
ROLE_TOOL_SCOPES = {
    "incident_commander": ["datadog", "slack", "jira", "runbook", "customer_portal"],
    "l1_support": ["slack", "customer_portal"],
    "l2_engineer": ["datadog", "slack", "runbook"],
    "sre_agent": ["datadog", "runbook", "jira"],
    "product_manager": ["jira", "customer_portal", "slack"],
    "oversight_agent": ["datadog", "slack", "jira", "runbook", "customer_portal"],  # full view
}


def agent_can_use_tool(agent: str, tool: str) -> bool:
    return tool in ROLE_TOOL_SCOPES.get(agent, [])


# ---------------------------------------------------------------------------
# SimDatadog
# ---------------------------------------------------------------------------
class SimDatadog:
    """Simulates Datadog metrics queries. Rate limited: max 3 unique metric queries per episode."""

    RATE_LIMIT = 3

    def __init__(self, incident: IncidentCase):
        self.incident = incident
        self._query_counts: Dict[str, int] = {}
        self._total_queries = 0
        self._rate_limit_hit = False

    def query(self, metric: str, service: Optional[str] = None,
              time_range_minutes: int = 60) -> Dict[str, Any]:
        key = f"{service}:{metric}" if service else metric
        self._total_queries += 1

        # Datadog rate limit: 3 unique metric+service combinations
        if key not in self._query_counts:
            if len(self._query_counts) >= self.RATE_LIMIT:
                self._rate_limit_hit = True
                return {
                    "status": "rate_limited",
                    "error": "Datadog API rate limit exceeded. Wait 60s or query fewer unique metrics.",
                    "retry_after_seconds": 60,
                }
            self._query_counts[key] = 0
        self._query_counts[key] += 1

        # Duplicate query penalty signal (used by OversightAgent)
        is_duplicate = self._query_counts[key] > 1

        # Filter alerts matching query
        matching = [
            a for a in self.incident.initial_alerts
            if (service is None or a.service == service) and
               (metric == "all" or a.metric == metric or metric in a.metric)
        ]

        if not matching:
            return {
                "status": "ok",
                "data": [],
                "message": f"No metrics found for service={service} metric={metric}",
                "is_duplicate_query": is_duplicate,
            }

        results = []
        for alert in matching:
            # Agents see value and threshold but NOT is_red_herring
            entry = {
                "service": alert.service,
                "metric": alert.metric,
                "current_value": alert.value,
                "threshold": alert.threshold,
                "status": "CRITICAL" if alert.value > alert.threshold else "OK",
                "time_range_minutes": time_range_minutes,
            }
            results.append(entry)

        return {
            "status": "ok",
            "data": results,
            "is_duplicate_query": is_duplicate,
            "query_count_for_key": self._query_counts[key],
        }

    def get_service_summary(self, service: str) -> Dict[str, Any]:
        """Return all metrics for a specific service — high-level overview."""
        return self.query(metric="all", service=service)

    def get_all_alerts(self) -> Dict[str, Any]:
        """Return all active alerts — broad sweep query."""
        key = "all:all"
        self._total_queries += 1
        if key not in self._query_counts:
            if len(self._query_counts) >= self.RATE_LIMIT:
                self._rate_limit_hit = True
                return {"status": "rate_limited", "error": "Datadog API rate limit exceeded."}
            self._query_counts[key] = 0
        self._query_counts[key] += 1

        results = []
        for alert in self.incident.initial_alerts:
            results.append({
                "service": alert.service,
                "metric": alert.metric,
                "current_value": alert.value,
                "threshold": alert.threshold,
                "status": "CRITICAL" if alert.value > alert.threshold else "OK",
            })
        return {
            "status": "ok",
            "data": results,
            "total_alerts": len(results),
            "critical_count": sum(1 for a in self.incident.initial_alerts if a.value > a.threshold),
            "is_duplicate_query": self._query_counts[key] > 1,
        }

    @property
    def duplicate_queries(self) -> List[str]:
        return [k for k, v in self._query_counts.items() if v > 1]


# ---------------------------------------------------------------------------
# SimSlack
# ---------------------------------------------------------------------------
class SimSlack:
    """Simulates Slack message search and channel queries."""

    def __init__(self, incident: IncidentCase):
        self.incident = incident
        self._channels_queried: List[str] = []
        self._messages_sent: List[Dict] = []

    def search(self, query: str, channel: Optional[str] = None) -> Dict[str, Any]:
        """Search messages by keyword or channel."""
        messages = self.incident.initial_slack_messages
        if channel:
            messages = [m for m in messages if m.channel == channel]
            if channel not in self._channels_queried:
                self._channels_queried.append(channel)

        # Keyword filter
        q_lower = query.lower()
        if query and query != "all":
            messages = [m for m in messages if q_lower in m.content.lower()]

        return {
            "status": "ok",
            "results": [
                {
                    "channel": m.channel,
                    "author": m.author,
                    "timestamp": m.timestamp,
                    "content": m.content,
                    # is_key_signal deliberately hidden from agents
                }
                for m in messages
            ],
            "count": len(messages),
        }

    def get_channel(self, channel: str) -> Dict[str, Any]:
        """Get all messages from a specific channel."""
        return self.search(query="all", channel=channel)

    def post_message(self, channel: str, message: str, author: str = "nexus-agent") -> Dict[str, Any]:
        """Post a message (used for coordination and customer notification)."""
        entry = {"channel": channel, "message": message, "author": author}
        self._messages_sent.append(entry)
        return {"status": "ok", "message_id": f"msg_{len(self._messages_sent)}", "posted": entry}

    def get_deploy_history(self, service: Optional[str] = None,
                           hours: int = 48) -> Dict[str, Any]:
        """Get recent deploy history — key signal for root cause investigation."""
        deploys = [
            m for m in self.incident.initial_slack_messages
            if m.channel == "#deploys" and
               (service is None or service.lower() in m.content.lower())
        ]
        return {
            "status": "ok",
            "deploys": [
                {"timestamp": m.timestamp, "content": m.content, "author": m.author}
                for m in deploys
            ],
            "count": len(deploys),
        }

    @property
    def messages_sent(self) -> List[Dict]:
        return self._messages_sent.copy()


# ---------------------------------------------------------------------------
# SimJira
# ---------------------------------------------------------------------------
class SimJira:
    """
    Simulates Jira incident ticket management.
    Business rules:
    - Tickets with revenue_impact > $100k require VP approval to close
    - Change freeze windows block non-emergency changes (Fridays 6pm-Monday 9am)
    - P1 tickets require post-incident review within 48h
    """

    CHANGE_FREEZE_ACTIVE = False  # Toggle for scenario variant
    VP_APPROVAL_REVENUE_THRESHOLD = 100_000

    def __init__(self, incident: IncidentCase):
        self.incident = incident
        self._tickets: Dict[str, Dict] = {}
        self._ticket_counter = 1
        self._auto_create_incident_ticket()

    def _auto_create_incident_ticket(self):
        """Auto-create main incident ticket on episode start."""
        tid = f"INC-{self.incident.case_id[-3:]}-001"
        self._tickets[tid] = {
            "id": tid,
            "title": f"[{self.incident.severity.value.upper()}] {self.incident.title}",
            "status": "open",
            "priority": self.incident.severity.value,
            "affected_services": self.incident.affected_services,
            "affected_regions": self.incident.affected_regions,
            "created_at": "2026-04-20T14:00:00Z",
            "requires_vp_approval": (
                self.incident.blast_radius.get("revenue_per_minute", 0) * 60
                > self.VP_APPROVAL_REVENUE_THRESHOLD
            ),
            "post_incident_review_required": self.incident.severity == "p1",
        }

    def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        if ticket_id not in self._tickets:
            return {"status": "error", "error": f"Ticket {ticket_id} not found"}
        return {"status": "ok", "ticket": self._tickets[ticket_id]}

    def create_ticket(self, title: str, priority: str, description: str,
                      affected_services: Optional[List[str]] = None) -> Dict[str, Any]:
        tid = f"INC-{self.incident.case_id[-3:]}-{self.incident.case_id[-3:]}0{self._ticket_counter}"
        self._ticket_counter += 1
        ticket = {
            "id": tid,
            "title": title,
            "priority": priority,
            "description": description,
            "status": "open",
            "affected_services": affected_services or [],
        }
        self._tickets[tid] = ticket
        return {"status": "ok", "ticket_id": tid, "ticket": ticket}

    def update_ticket(self, ticket_id: str, status: Optional[str] = None,
                      comment: Optional[str] = None, assignee: Optional[str] = None) -> Dict[str, Any]:
        if ticket_id not in self._tickets:
            return {"status": "error", "error": f"Ticket {ticket_id} not found"}

        ticket = self._tickets[ticket_id]

        # Change freeze check
        if self.CHANGE_FREEZE_ACTIVE and status == "closed":
            return {
                "status": "blocked",
                "reason": "Change freeze active. Emergency override requires director approval.",
                "override_required": True,
            }

        # VP approval check for high-revenue incidents
        if ticket.get("requires_vp_approval") and status == "closed":
            if not ticket.get("vp_approved"):
                return {
                    "status": "pending_approval",
                    "reason": f"Revenue impact exceeds ${self.VP_APPROVAL_REVENUE_THRESHOLD:,}. VP approval required.",
                    "approval_url": "jira.internal/approval/vp",
                }

        if status:
            ticket["status"] = status
        if comment:
            ticket.setdefault("comments", []).append(comment)
        if assignee:
            ticket["assignee"] = assignee

        return {"status": "ok", "ticket_id": ticket_id, "updated": ticket}

    def get_open_incidents(self) -> Dict[str, Any]:
        open_tickets = [t for t in self._tickets.values() if t["status"] == "open"]
        return {"status": "ok", "open_incidents": open_tickets, "count": len(open_tickets)}

    def escalate(self, ticket_id: str, escalation_target: str, reason: str) -> Dict[str, Any]:
        if ticket_id not in self._tickets:
            return {"status": "error", "error": f"Ticket {ticket_id} not found"}
        ticket = self._tickets[ticket_id]
        ticket.setdefault("escalations", []).append({
            "target": escalation_target,
            "reason": reason,
        })
        return {"status": "ok", "escalation": {"target": escalation_target, "ticket_id": ticket_id}}


# ---------------------------------------------------------------------------
# SimRunbook
# ---------------------------------------------------------------------------
class SimRunbook:
    """
    Simulates Runbook API.
    Patronus AI schema drift in INC007 at step 18-22:
    - v1.0: {step_id, title, description, expected_outcome, rollback_available, ...}
    - v2.0: {runbook_ref, name, details, expected_output, success_criteria, can_rollback, ...}
    """

    def __init__(self, incident: IncidentCase, schema_version: str = "v1.0"):
        self.incident = incident
        self.schema_version = schema_version
        self._steps_executed: List[str] = []

    def set_schema_version(self, version: str):
        """Called by environment when schema drift triggers."""
        self.schema_version = version

    def _format_step(self, step: RunbookStep) -> Dict[str, Any]:
        if self.schema_version == "v1.0":
            return {
                "step_id": step.step_id,
                "title": step.title,
                "description": step.description,
                "expected_outcome": step.expected_outcome,
                "rollback_available": step.rollback_available,
                "prerequisite_step_id": step.prerequisite_step_id,
            }
        else:  # v2.0 — Patronus schema drift
            return {
                "runbook_ref": step.step_id,     # field renamed
                "name": step.title,              # field renamed
                "details": step.description,     # field renamed
                "expected_output": step.expected_outcome.split("—")[0].strip() if "—" in step.expected_outcome else step.expected_outcome,
                "success_criteria": step.expected_outcome.split("—")[1].strip() if "—" in step.expected_outcome else "Confirmed by monitoring",
                "can_rollback": step.rollback_available,  # field renamed
                "requires_prerequisite": step.prerequisite_step_id,  # field renamed
            }

    def list_runbooks(self) -> Dict[str, Any]:
        """List all available runbook steps."""
        return {
            "status": "ok",
            "schema_version": self.schema_version,
            "runbooks": [self._format_step(s) for s in self.incident.available_runbooks],
            "count": len(self.incident.available_runbooks),
        }

    def get_runbook(self, step_id: str) -> Dict[str, Any]:
        """Get a specific runbook step. Accepts both v1.0 step_id and v2.0 runbook_ref."""
        step = next((s for s in self.incident.available_runbooks if s.step_id == step_id), None)
        if not step:
            return {
                "status": "error",
                "error": f"Runbook step '{step_id}' not found",
                "schema_version": self.schema_version,
                "available_refs": [s.step_id for s in self.incident.available_runbooks],
            }
        return {
            "status": "ok",
            "schema_version": self.schema_version,
            "step": self._format_step(step),
        }

    def execute_step(self, step_id: str, confirm: bool = False) -> Dict[str, Any]:
        """
        Execute a runbook step. Returns simulated outcome.
        Correct steps return positive outcomes; wrong steps return partial/misleading results.
        """
        step = next((s for s in self.incident.available_runbooks if s.step_id == step_id), None)
        if not step:
            return {"status": "error", "error": f"Runbook step '{step_id}' not found"}

        # Prerequisite check
        if step.prerequisite_step_id and step.prerequisite_step_id not in self._steps_executed:
            return {
                "status": "blocked",
                "error": f"Prerequisite step '{step.prerequisite_step_id}' must be executed first",
                "prerequisite": step.prerequisite_step_id,
            }

        self._steps_executed.append(step_id)

        if step.is_correct_step:
            return {
                "status": "success",
                "step_id": step_id,
                "schema_version": self.schema_version,
                "outcome": step.expected_outcome,
                "rollback_available": step.rollback_available,
                "executed": True,
            }
        else:
            return {
                "status": "executed_with_warning",
                "step_id": step_id,
                "schema_version": self.schema_version,
                "outcome": step.expected_outcome,
                "warning": "Step executed but may not resolve root cause. Monitor closely.",
                "rollback_available": step.rollback_available,
                "executed": True,
            }

    @property
    def steps_executed(self) -> List[str]:
        return self._steps_executed.copy()

    @property
    def correct_steps_executed(self) -> int:
        correct_ids = {s.step_id for s in self.incident.available_runbooks if s.is_correct_step}
        return sum(1 for s in self._steps_executed if s in correct_ids)


# ---------------------------------------------------------------------------
# SimCustomerPortal
# ---------------------------------------------------------------------------
class SimCustomerPortal:
    """
    Simulates Customer Portal API.
    Patronus AI schema drift in INC007 at step 18-22:
    - v1.0 notification: {customers, message, severity}
    - v2.0 notification: {recipients, content, impact_level, gdpr_compliant: true required}
    Notifications without gdpr_compliant=true in v2.0 are rejected.
    """

    def __init__(self, incident: IncidentCase, schema_version: str = "v1.0"):
        self.incident = incident
        self.schema_version = schema_version
        self._notifications_sent: List[Dict] = []
        self._sla_breaches_reported: List[str] = []

    def set_schema_version(self, version: str):
        """Called by environment when schema drift triggers."""
        self.schema_version = version

    def get_customer_reports(self) -> Dict[str, Any]:
        """Return current customer-reported issues."""
        return {
            "status": "ok",
            "reports": self.incident.customer_reports,
            "count": len(self.incident.customer_reports),
            "affected_users": self.incident.blast_radius.get("users_affected", 0),
        }

    def send_notification(self, **kwargs) -> Dict[str, Any]:
        """
        Send proactive customer notification.
        v1.0 schema: send_notification(customers, message, severity)
        v2.0 schema: send_notification(recipients, content, impact_level, gdpr_compliant)
        """
        if self.schema_version == "v1.0":
            customers = kwargs.get("customers")
            message = kwargs.get("message")
            severity = kwargs.get("severity", "medium")

            if not customers or not message:
                return {
                    "status": "error",
                    "error": "Missing required fields: customers, message",
                    "schema_version": self.schema_version,
                }

            entry = {
                "customers": customers,
                "message": message,
                "severity": severity,
                "schema_version": "v1.0",
            }
        else:  # v2.0
            recipients = kwargs.get("recipients")
            content = kwargs.get("content")
            impact_level = kwargs.get("impact_level")
            gdpr_compliant = kwargs.get("gdpr_compliant")

            if not recipients or not content or not impact_level:
                return {
                    "status": "error",
                    "error": "Missing required fields: recipients, content, impact_level",
                    "schema_version": self.schema_version,
                }

            # Patronus AI: GDPR compliance required in v2.0
            if gdpr_compliant is not True:
                return {
                    "status": "rejected",
                    "error": "gdpr_compliant must be set to true. Notification blocked per GDPR policy v2.0.",
                    "schema_version": self.schema_version,
                    "action_required": "Add gdpr_compliant=true to notification payload",
                }

            entry = {
                "recipients": recipients,
                "content": content,
                "impact_level": impact_level,
                "gdpr_compliant": True,
                "schema_version": "v2.0",
            }

        self._notifications_sent.append(entry)
        return {
            "status": "ok",
            "notification_id": f"notif_{len(self._notifications_sent)}",
            "sent_to": entry.get("customers", entry.get("recipients")),
            "schema_version": self.schema_version,
            "accepted": True,
        }

    def get_sla_status(self) -> Dict[str, Any]:
        """Return current SLA status for affected services."""
        slas_breached = self.incident.blast_radius.get("slas_breached", [])
        return {
            "status": "ok",
            "slas_breached": slas_breached,
            "breach_count": len(slas_breached),
            "revenue_impact_per_minute": self.incident.blast_radius.get("revenue_per_minute", 0),
        }

    def report_sla_breach(self, sla_id: str, details: str) -> Dict[str, Any]:
        self._sla_breaches_reported.append(sla_id)
        return {"status": "ok", "reported": sla_id, "acknowledged": True}

    @property
    def notifications_sent(self) -> int:
        return len(self._notifications_sent)

    @property
    def valid_notifications(self) -> int:
        """Count only accepted notifications (not rejected gdpr ones)."""
        return len(self._notifications_sent)  # Only accepted ones stored


# ---------------------------------------------------------------------------
# ToolRegistry — dispatches tool calls to correct simulator
# ---------------------------------------------------------------------------
class ToolRegistry:
    """Central registry. Enforces role-based tool access."""

    def __init__(self, incident: IncidentCase):
        self.incident = incident
        self.datadog = SimDatadog(incident)
        self.slack = SimSlack(incident)
        self.jira = SimJira(incident)
        self.runbook = SimRunbook(incident, schema_version=incident.schema_version)
        self.customer_portal = SimCustomerPortal(incident, schema_version=incident.schema_version)

    def apply_schema_drift(self, version: str):
        """Apply Patronus AI schema drift — update all relevant tools."""
        self.runbook.set_schema_version(version)
        self.customer_portal.set_schema_version(version)

    def call(self, tool: str, action: str, agent: str,
             params: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch tool call with role enforcement."""
        known_tools = {"datadog", "slack", "jira", "runbook", "customer_portal"}
        if tool not in known_tools:
            return {"status": "error", "error": f"Unknown tool: {tool}"}

        # Role enforcement
        if not agent_can_use_tool(agent, tool):
            return {
                "status": "unauthorized",
                "error": f"Agent '{agent}' does not have access to tool '{tool}'",
                "allowed_tools": ROLE_TOOL_SCOPES.get(agent, []),
            }

        if tool == "datadog":
            action_map = {
                "query": lambda: self.datadog.query(
                    metric=params.get("metric", "all"),
                    service=params.get("service"),
                    time_range_minutes=params.get("time_range_minutes", 60),
                ),
                "get_service_summary": lambda: self.datadog.get_service_summary(params["service"]),
                "get_all_alerts": lambda: self.datadog.get_all_alerts(),
            }
        elif tool == "slack":
            action_map = {
                "search": lambda: self.slack.search(
                    query=params.get("query", "all"),
                    channel=params.get("channel"),
                ),
                "get_channel": lambda: self.slack.get_channel(params["channel"]),
                "post_message": lambda: self.slack.post_message(
                    channel=params["channel"],
                    message=params["message"],
                    author=agent,
                ),
                "get_deploy_history": lambda: self.slack.get_deploy_history(
                    service=params.get("service"),
                    hours=params.get("hours", 48),
                ),
            }
        elif tool == "jira":
            action_map = {
                "get_ticket": lambda: self.jira.get_ticket(params["ticket_id"]),
                "create_ticket": lambda: self.jira.create_ticket(
                    title=params["title"],
                    priority=params["priority"],
                    description=params["description"],
                    affected_services=params.get("affected_services"),
                ),
                "update_ticket": lambda: self.jira.update_ticket(
                    ticket_id=params["ticket_id"],
                    status=params.get("status"),
                    comment=params.get("comment"),
                    assignee=params.get("assignee"),
                ),
                "get_open_incidents": lambda: self.jira.get_open_incidents(),
                "escalate": lambda: self.jira.escalate(
                    ticket_id=params["ticket_id"],
                    escalation_target=params["escalation_target"],
                    reason=params["reason"],
                ),
            }
        elif tool == "runbook":
            action_map = {
                "list_runbooks": lambda: self.runbook.list_runbooks(),
                "get_runbook": lambda: self.runbook.get_runbook(params["step_id"]),
                "execute_step": lambda: self.runbook.execute_step(
                    step_id=params["step_id"],
                    confirm=params.get("confirm", False),
                ),
            }
        elif tool == "customer_portal":
            action_map = {
                "get_customer_reports": lambda: self.customer_portal.get_customer_reports(),
                "send_notification": lambda: self.customer_portal.send_notification(**params),
                "get_sla_status": lambda: self.customer_portal.get_sla_status(),
                "report_sla_breach": lambda: self.customer_portal.report_sla_breach(
                    sla_id=params["sla_id"],
                    details=params.get("details", ""),
                ),
            }
        else:
            return {"status": "error", "error": f"Unknown tool: {tool}"}

        if action not in action_map:
            return {
                "status": "error",
                "error": f"Unknown action '{action}' for tool '{tool}'",
                "valid_actions": list(action_map.keys()),
            }

        try:
            return action_map[action]()
        except KeyError as e:
            return {"status": "error", "error": f"Missing required parameter: {e}"}
        except Exception as e:
            return {"status": "error", "error": f"Tool execution failed: {str(e)}"}

    @property
    def total_tool_calls(self) -> int:
        return self.datadog._total_queries

    @property
    def duplicate_datadog_queries(self) -> List[str]:
        return self.datadog.duplicate_queries

    @property
    def notifications_sent(self) -> int:
        return self.customer_portal.notifications_sent

    @property
    def runbook_correct_steps(self) -> int:
        return self.runbook.correct_steps_executed

    @property
    def slack_messages_sent(self) -> int:
        return len(self.slack.messages_sent)
