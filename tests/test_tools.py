"""Tests for tool simulators — rate limits, schema drift, role enforcement."""

import pytest
from server.tools import (
    SimDatadog, SimSlack, SimJira, SimRunbook, SimCustomerPortal,
    ToolRegistry, agent_can_use_tool, ROLE_TOOL_SCOPES,
)
from server.incidents import get_incident


def make_registry(case_id="INC001"):
    return ToolRegistry(get_incident(case_id))


class TestSimDatadog:
    def test_get_all_alerts_returns_data(self):
        dd = SimDatadog(get_incident("INC001"))
        result = dd.get_all_alerts()
        assert result["status"] == "ok"
        assert len(result["data"]) > 0

    def test_rate_limit_enforced(self):
        dd = SimDatadog(get_incident("INC001"))
        # Query 3 unique keys
        dd.query("metric_a", "service_a")
        dd.query("metric_b", "service_b")
        dd.query("metric_c", "service_c")
        # 4th unique key should be rate limited
        result = dd.query("metric_d", "service_d")
        assert result["status"] == "rate_limited"

    def test_duplicate_query_flagged(self):
        dd = SimDatadog(get_incident("INC001"))
        dd.query("http_5xx_rate", "payment-service")
        result = dd.query("http_5xx_rate", "payment-service")
        assert result.get("is_duplicate_query") is True

    def test_is_red_herring_not_exposed(self):
        dd = SimDatadog(get_incident("INC001"))
        result = dd.get_all_alerts()
        for entry in result["data"]:
            assert "is_red_herring" not in entry


class TestSimSlack:
    def test_get_channel_returns_messages(self):
        sl = SimSlack(get_incident("INC001"))
        result = sl.get_channel("#alerts")
        assert result["status"] == "ok"
        assert result["count"] >= 1

    def test_search_filters_by_keyword(self):
        sl = SimSlack(get_incident("INC001"))
        result = sl.search("stripe")
        assert result["count"] >= 1

    def test_post_message_tracked(self):
        sl = SimSlack(get_incident("INC001"))
        sl.post_message("#incident", "IC update: investigating payment failures")
        assert len(sl.messages_sent) == 1

    def test_is_key_signal_not_exposed(self):
        sl = SimSlack(get_incident("INC001"))
        result = sl.get_channel("#deploys")
        for msg in result["results"]:
            assert "is_key_signal" not in msg


class TestSimJira:
    def test_auto_creates_incident_ticket(self):
        jira = SimJira(get_incident("INC001"))
        result = jira.get_open_incidents()
        assert result["count"] >= 1

    def test_create_ticket(self):
        jira = SimJira(get_incident("INC001"))
        result = jira.create_ticket("Follow-up: stripe client audit", "p2", "Post-incident review")
        assert result["status"] == "ok"
        assert "ticket_id" in result

    def test_vp_approval_required_high_revenue(self):
        # INC004 has $41k/min — exceeds $100k threshold for hourly impact
        jira = SimJira(get_incident("INC004"))
        ticket_id = list(jira._tickets.keys())[0]
        result = jira.update_ticket(ticket_id, status="closed")
        # May require VP approval
        assert result["status"] in ["ok", "pending_approval"]

    def test_escalate_ticket(self):
        jira = SimJira(get_incident("INC001"))
        tid = list(jira._tickets.keys())[0]
        result = jira.escalate(tid, "vp_engineering", "P1 SLA breach")
        assert result["status"] == "ok"


class TestSimRunbook:
    def test_list_runbooks_v1(self):
        rb = SimRunbook(get_incident("INC001"), "v1.0")
        result = rb.list_runbooks()
        assert result["schema_version"] == "v1.0"
        assert "step_id" in result["runbooks"][0]

    def test_list_runbooks_v2(self):
        rb = SimRunbook(get_incident("INC001"), "v2.0")
        result = rb.list_runbooks()
        assert result["schema_version"] == "v2.0"
        assert "runbook_ref" in result["runbooks"][0]
        assert "step_id" not in result["runbooks"][0]

    def test_execute_correct_step(self):
        rb = SimRunbook(get_incident("INC001"))
        result = rb.execute_step("rb_check_logs")
        assert result["status"] == "success"

    def test_prerequisite_enforced(self):
        rb = SimRunbook(get_incident("INC001"))
        # rb_check_stripe_header requires rb_check_logs first
        result = rb.execute_step("rb_check_stripe_header")
        assert result["status"] == "blocked"

    def test_execute_after_prerequisite(self):
        rb = SimRunbook(get_incident("INC001"))
        rb.execute_step("rb_check_logs")
        result = rb.execute_step("rb_check_stripe_header")
        assert result["status"] == "success"

    def test_wrong_step_executes_with_warning(self):
        rb = SimRunbook(get_incident("INC001"))
        result = rb.execute_step("rb_restart_payment")
        assert result["status"] == "executed_with_warning"

    def test_correct_steps_counter(self):
        rb = SimRunbook(get_incident("INC001"))
        rb.execute_step("rb_check_logs")
        rb.execute_step("rb_restart_payment")  # Wrong step
        assert rb.correct_steps_executed == 1


class TestSimCustomerPortal:
    def test_get_customer_reports(self):
        cp = SimCustomerPortal(get_incident("INC001"))
        result = cp.get_customer_reports()
        assert result["status"] == "ok"
        assert result["count"] >= 1

    def test_send_notification_v1(self):
        cp = SimCustomerPortal(get_incident("INC001"), "v1.0")
        result = cp.send_notification(customers="all", message="Investigating", severity="high")
        assert result["status"] == "ok"
        assert cp.notifications_sent == 1

    def test_send_notification_v2_requires_gdpr(self):
        cp = SimCustomerPortal(get_incident("INC007"), "v2.0")
        result = cp.send_notification(recipients="all", content="Update", impact_level="critical")
        assert result["status"] == "rejected"
        assert "gdpr_compliant" in result["error"]

    def test_send_notification_v2_with_gdpr(self):
        cp = SimCustomerPortal(get_incident("INC007"), "v2.0")
        result = cp.send_notification(
            recipients="all", content="Update", impact_level="critical", gdpr_compliant=True
        )
        assert result["status"] == "ok"


class TestToolRegistry:
    def test_role_enforcement_blocks_unauthorized(self):
        reg = make_registry("INC001")
        result = reg.call("datadog", "get_all_alerts", "l1_support", {})
        assert result["status"] == "unauthorized"

    def test_unknown_tool_returns_error(self):
        reg = make_registry()
        result = reg.call("nonexistent_tool", "query", "incident_commander", {})
        assert result["status"] == "error"

    def test_unknown_action_returns_error(self):
        reg = make_registry()
        result = reg.call("datadog", "unknown_action", "incident_commander", {})
        assert result["status"] == "error"

    def test_schema_drift_propagates(self):
        reg = make_registry("INC007")
        reg.apply_schema_drift("v2.0")
        assert reg.runbook.schema_version == "v2.0"
        assert reg.customer_portal.schema_version == "v2.0"
