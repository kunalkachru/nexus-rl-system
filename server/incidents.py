from typing import Dict, List
from server.data_models import (
    IncidentCase, IncidentType, Severity,
    DatadogAlert, SlackMessage, RunbookStep,
)

# ---------------------------------------------------------------------------
# INC001 — Payment Service Timeout Storm (Easy)
# ---------------------------------------------------------------------------
INC001 = IncidentCase(
    case_id="INC001",
    title="Payment Service Timeout Storm",
    incident_type=IncidentType.SERVICE_DOWN,
    severity=Severity.P1,
    difficulty="easy",

    initial_alerts=[
        DatadogAlert("payment-service", "http_5xx_rate", 0.94, 0.05, is_red_herring=False),
        DatadogAlert("checkout-frontend", "latency_p99_ms", 12400, 2000, is_red_herring=False),
        DatadogAlert("payment-service", "cpu_utilization", 0.12, 0.80, is_red_herring=True),
        DatadogAlert("postgres-primary", "query_latency_ms", 2.1, 100.0, is_red_herring=True),
    ],
    initial_slack_messages=[
        SlackMessage("#alerts", "PagerDuty", "2026-04-20T14:00:00Z",
                     "ALERT: payment-service HTTP 500 rate 94%", is_key_signal=False),
        SlackMessage("#deploys", "deploy-bot", "2026-04-17T09:00:00Z",
                     "stripe-client v2022-08 deployed to prod", is_key_signal=True),
        SlackMessage("#general", "eng-bot", "2026-04-19T11:00:00Z",
                     "Stripe announced API v2023-11 as mandatory from April 20", is_key_signal=True),
    ],
    customer_reports=[
        "Cannot complete purchase — getting 'Payment Failed' error",
        "Checkout broken for last 20 minutes",
        "My team can't process any orders right now",
    ],
    affected_services=["payment-service", "checkout-frontend"],
    affected_regions=["us-east-1"],

    root_cause="Stripe API v2023-11 requires Stripe-Version header; client sends v2022-08 format causing 400 rejections",
    root_cause_service="payment-service",
    correct_mitigation_steps=["check_logs", "identify_400_pattern", "update_stripe_client", "verify_recovery"],
    correct_escalation_path=["l2_engineer", "incident_commander"],

    blast_radius={
        "users_affected": 140000,
        "revenue_per_minute": 8400,
        "slas_breached": ["payment-uptime-99.9"],
    },

    cascade_tree={},
    red_herrings=["payment-service-cpu", "postgres-primary-latency"],
    masked_signals=["Stripe changelog email in #vendor-updates 3 days ago"],

    available_runbooks=[
        RunbookStep("rb_check_logs", "Check application logs",
                    "Query recent error logs for payment-service",
                    "Returns last 100 error log lines showing 400 status codes",
                    True, None, True),
        RunbookStep("rb_check_stripe_header", "Check Stripe API version header",
                    "Validate outgoing Stripe-Version header in requests",
                    "Returns current header value — expect mismatch",
                    False, "rb_check_logs", True),
        RunbookStep("rb_update_stripe_client", "Update Stripe client version",
                    "Deploy Stripe client config with Stripe-Version: 2023-11",
                    "HTTP 500 rate drops to <1% within 90 seconds",
                    True, "rb_check_stripe_header", True),
        RunbookStep("rb_restart_payment", "Restart payment service pods",
                    "Rolling restart of all payment-service pods",
                    "Brief traffic drop then recovery — does NOT fix root cause",
                    True, None, False),
    ],

    competing_hypotheses=[],
    correct_hypothesis_keywords=["stripe", "header", "version", "2023-11", "api", "400"],
    expert_review_criteria_set="speed",

    schema_drift_step=None,
    schema_version="v1.0",
    optimal_mttr_minutes=18,
    baseline_mttr_minutes=45,
    max_steps=20,
    revenue_per_minute=8400,
)

# ---------------------------------------------------------------------------
# INC002 — Database Connection Pool Exhaustion (Easy)
# ---------------------------------------------------------------------------
INC002 = IncidentCase(
    case_id="INC002",
    title="Database Connection Pool Exhaustion",
    incident_type=IncidentType.PERF_DEGRADATION,
    severity=Severity.P2,
    difficulty="easy",

    initial_alerts=[
        DatadogAlert("user-service", "db_connection_wait_ms", 4800, 500, is_red_herring=False),
        DatadogAlert("postgres-primary", "active_connections", 498, 500, is_red_herring=False),
        DatadogAlert("user-service", "http_latency_p99_ms", 6200, 1000, is_red_herring=False),
        DatadogAlert("user-service", "disk_iops", 42, 1000, is_red_herring=True),
        DatadogAlert("cache-cluster", "miss_rate", 0.04, 0.20, is_red_herring=True),
    ],
    initial_slack_messages=[
        SlackMessage("#alerts", "PagerDuty", "2026-04-20T10:00:00Z",
                     "ALERT: postgres active_connections at 99.6% of limit", is_key_signal=False),
        SlackMessage("#deploys", "deploy-bot", "2026-04-20T08:30:00Z",
                     "user-service v3.4.1 deployed — new async batch job enabled", is_key_signal=True),
        SlackMessage("#dev", "alice", "2026-04-19T17:00:00Z",
                     "heads up: batch job doesn't release connections on timeout", is_key_signal=True),
    ],
    customer_reports=[
        "Login is extremely slow — taking 30+ seconds",
        "Profile page timing out",
    ],
    affected_services=["user-service", "postgres-primary"],
    affected_regions=["us-east-1"],

    root_cause="New async batch job in user-service v3.4.1 holds DB connections on timeout instead of releasing; pool exhausted",
    root_cause_service="user-service",
    correct_mitigation_steps=["check_db_metrics", "identify_connection_leak", "kill_batch_job", "increase_pool_timeout", "verify_connection_release"],
    correct_escalation_path=["l2_engineer", "incident_commander"],

    blast_radius={
        "users_affected": 85000,
        "revenue_per_minute": 2100,
        "slas_breached": ["user-service-latency-p99"],
    },

    cascade_tree={
        "user-service": ["checkout-service", "notification-service"],
    },
    red_herrings=["disk-iops", "cache-miss-rate"],
    masked_signals=["alice's Slack warning about connection leak 17 hours ago"],

    available_runbooks=[
        RunbookStep("rb_check_pg_connections", "Check PostgreSQL active connections",
                    "Query pg_stat_activity for connection breakdown by application",
                    "Returns connection count per application — batch job visible",
                    True, None, True),
        RunbookStep("rb_kill_batch_job", "Terminate runaway batch job",
                    "Send SIGTERM to batch job process and release held connections",
                    "Active connections drop immediately; latency recovers",
                    True, "rb_check_pg_connections", True),
        RunbookStep("rb_fix_connection_timeout", "Fix connection release on timeout",
                    "Apply connection.close() in finally block in batch job",
                    "Batch job safely releases connections on timeout",
                    True, "rb_kill_batch_job", True),
        RunbookStep("rb_restart_postgres", "Restart PostgreSQL",
                    "Full PostgreSQL restart — kills all connections",
                    "All services lose connections momentarily — data loss risk",
                    False, None, False),
    ],

    competing_hypotheses=[],
    correct_hypothesis_keywords=["connection", "pool", "batch", "leak", "exhaustion", "timeout"],
    expert_review_criteria_set="communication",

    schema_drift_step=None,
    schema_version="v1.0",
    optimal_mttr_minutes=22,
    baseline_mttr_minutes=55,
    max_steps=22,
    revenue_per_minute=2100,
)

# ---------------------------------------------------------------------------
# INC003 — Memory Leak Under Load (Medium) — DEMO INCIDENT
# ---------------------------------------------------------------------------
INC003 = IncidentCase(
    case_id="INC003",
    title="Memory Leak Under Load",
    incident_type=IncidentType.PERF_DEGRADATION,
    severity=Severity.P2,
    difficulty="medium",

    initial_alerts=[
        DatadogAlert("recommendation-service", "memory_utilization", 0.96, 0.85, is_red_herring=False),
        DatadogAlert("recommendation-service", "gc_pause_ms", 4200, 500, is_red_herring=False),
        DatadogAlert("api-gateway", "latency_p99_ms", 8100, 2000, is_red_herring=False),
        DatadogAlert("search-service", "error_rate", 0.08, 0.05, is_red_herring=True),   # RED HERRING
        DatadogAlert("ad-service", "cpu_utilization", 0.78, 0.90, is_red_herring=True),  # RED HERRING
        DatadogAlert("recommendation-service", "heap_used_mb", 14200, 8192, is_red_herring=False),
    ],
    initial_slack_messages=[
        SlackMessage("#alerts", "PagerDuty", "2026-04-20T16:00:00Z",
                     "ALERT: recommendation-service memory 96% — OOMKill imminent", is_key_signal=False),
        SlackMessage("#deploys", "deploy-bot", "2026-04-20T14:30:00Z",
                     "recommendation-service v2.8.0 deployed — ML model updated to v4", is_key_signal=True),
        SlackMessage("#dev", "ml-team-bot", "2026-04-20T15:45:00Z",
                     "search-service degradation unrelated — separate issue being tracked", is_key_signal=True),
        SlackMessage("#alerts", "datadog-bot", "2026-04-20T15:50:00Z",
                     "ad-service CPU spike correlates with recommendation load spike — expected", is_key_signal=False),
    ],
    customer_reports=[
        "Product recommendations not loading",
        "Homepage extremely slow to load",
        "App crashing every few minutes and recovering",
    ],
    affected_services=["recommendation-service", "api-gateway"],
    affected_regions=["us-east-1", "eu-west-1"],

    root_cause="ML model v4 in recommendation-service caches feature vectors without eviction; memory grows until OOMKill then cycle repeats",
    root_cause_service="recommendation-service",
    correct_mitigation_steps=["check_heap_profile", "identify_cache_growth", "configure_cache_eviction", "restart_service_controlled", "verify_memory_stable"],
    correct_escalation_path=["l2_engineer", "ml_team", "incident_commander"],

    blast_radius={
        "users_affected": 320000,
        "revenue_per_minute": 15600,
        "slas_breached": ["recommendation-availability-99.5", "api-gateway-latency-p99"],
    },

    cascade_tree={
        "recommendation-service": ["api-gateway", "homepage-service"],
        "api-gateway": ["checkout-service"],
    },
    red_herrings=["search-service-errors", "ad-service-cpu"],
    masked_signals=[
        "ML model v4 changelog: feature vector cache size increased 10x for accuracy",
        "Heap profiler output from staging showing unbounded growth",
    ],

    available_runbooks=[
        RunbookStep("rb_heap_profile", "Capture heap profile",
                    "Run heap profiler against recommendation-service pod",
                    "Returns top memory consumers — cache object visible at top",
                    True, None, True),
        RunbookStep("rb_check_cache_config", "Check ML model cache configuration",
                    "Inspect FeatureVectorCache max_size and eviction policy",
                    "Returns cache config — max_size=unlimited, eviction=none",
                    True, "rb_heap_profile", True),
        RunbookStep("rb_set_cache_eviction", "Configure LRU eviction on cache",
                    "Set FeatureVectorCache max_size=4096, eviction=LRU",
                    "Memory growth stops; heap stabilises below 8GB",
                    True, "rb_check_cache_config", True),
        RunbookStep("rb_controlled_restart", "Controlled rolling restart",
                    "Rolling restart with new cache config — one pod at a time",
                    "Service recovers without full downtime; memory stays stable",
                    True, "rb_set_cache_eviction", True),
        RunbookStep("rb_restart_immediately", "Emergency restart all pods",
                    "Kill all recommendation-service pods immediately",
                    "Service recovers but memory leak recurs — does not fix root cause",
                    True, None, False),
    ],

    competing_hypotheses=[
        "ML model v4 feature vector cache has no eviction — memory grows unbounded",
        "Network partition between recommendation-service and cache cluster causing local cache duplication",
        "Search-service errors causing recommendation fallback path to allocate extra memory",
    ],
    correct_hypothesis_keywords=["cache", "eviction", "ml model", "feature vector", "heap", "memory leak"],
    expert_review_criteria_set="technical",

    schema_drift_step=None,
    schema_version="v1.0",
    optimal_mttr_minutes=28,
    baseline_mttr_minutes=75,
    max_steps=28,
    revenue_per_minute=15600,
)

# ---------------------------------------------------------------------------
# INC004 — Third-Party API Failure Masked by Retry Logic (Hard)
# ---------------------------------------------------------------------------
INC004 = IncidentCase(
    case_id="INC004",
    title="Third-Party API Failure Masked by Retry Logic",
    incident_type=IncidentType.CASCADE,
    severity=Severity.P1,
    difficulty="hard",

    initial_alerts=[
        DatadogAlert("order-service", "http_5xx_rate", 0.23, 0.05, is_red_herring=False),
        DatadogAlert("order-service", "latency_p99_ms", 28000, 5000, is_red_herring=False),
        DatadogAlert("order-service", "retry_rate", 0.91, 0.10, is_red_herring=False),
        DatadogAlert("shipping-api-proxy", "upstream_timeout_rate", 0.97, 0.05, is_red_herring=False),
        DatadogAlert("order-service", "thread_pool_saturation", 0.88, 0.80, is_red_herring=True),
        DatadogAlert("inventory-service", "latency_p99_ms", 3200, 2000, is_red_herring=True),
    ],
    initial_slack_messages=[
        SlackMessage("#alerts", "PagerDuty", "2026-04-20T09:00:00Z",
                     "ALERT: order-service 5xx rate 23% — SLA breach imminent", is_key_signal=False),
        SlackMessage("#vendor", "vendor-monitor", "2026-04-20T08:45:00Z",
                     "FedEx Shipping API status: degraded — investigating", is_key_signal=True),
        SlackMessage("#dev", "retry-config", "2026-04-20T07:00:00Z",
                     "retry backoff updated to exponential with 30s max — deployed last night", is_key_signal=True),
        SlackMessage("#alerts", "datadog-bot", "2026-04-20T09:05:00Z",
                     "inventory-service latency spike correlated with order volume — expected", is_key_signal=False),
    ],
    customer_reports=[
        "Orders stuck in 'Processing' for 30+ minutes",
        "Cannot track shipment — getting timeout errors",
        "Placed 3 orders — all showing processing, none confirmed",
    ],
    affected_services=["order-service", "shipping-api-proxy"],
    affected_regions=["us-east-1", "us-west-2"],

    root_cause="FedEx Shipping API experiencing global degradation; order-service retry logic masks failure but saturates thread pool; orders queue but cannot complete",
    root_cause_service="shipping-api-proxy",
    correct_mitigation_steps=["check_upstream_status", "enable_circuit_breaker", "queue_orders_for_retry", "notify_customers_proactively", "monitor_fedex_recovery"],
    correct_escalation_path=["sre_agent", "pm_agent", "incident_commander"],

    blast_radius={
        "users_affected": 67000,
        "revenue_per_minute": 41000,
        "slas_breached": ["order-processing-sla-15min", "shipment-confirmation-sla"],
    },

    cascade_tree={
        "shipping-api-proxy": ["order-service"],
        "order-service": ["checkout-service", "notification-service", "inventory-service"],
    },
    red_herrings=["thread-pool-saturation", "inventory-latency"],
    masked_signals=[
        "FedEx status page shows incident started 2h before our alerts due to retry masking",
        "Circuit breaker disabled in last night's config change",
    ],

    available_runbooks=[
        RunbookStep("rb_check_vendor_status", "Check FedEx API status page",
                    "Query vendor status API and internal proxy logs",
                    "Confirms FedEx degraded — not internal issue",
                    True, None, True),
        RunbookStep("rb_enable_circuit_breaker", "Enable circuit breaker for shipping proxy",
                    "Toggle circuit_breaker=true in shipping-api-proxy config",
                    "Retry storm stops; thread pool recovers; orders queue cleanly",
                    True, "rb_check_vendor_status", True),
        RunbookStep("rb_queue_orders", "Move pending orders to retry queue",
                    "Migrate stuck orders to async retry queue with 5min intervals",
                    "Orders auto-complete when FedEx recovers — no data loss",
                    True, "rb_enable_circuit_breaker", True),
        RunbookStep("rb_cancel_pending_orders", "Cancel all pending orders",
                    "Cancel all orders stuck in processing",
                    "Removes backlog but angers customers — data loss",
                    False, None, False),
    ],

    competing_hypotheses=[
        "External FedEx API failure masked by retry logic saturating our thread pool",
        "Internal shipping proxy misconfiguration causing timeouts",
        "Database deadlock in order-service causing cascade",
    ],
    correct_hypothesis_keywords=["fedex", "vendor", "third-party", "circuit breaker", "retry", "upstream", "external"],
    expert_review_criteria_set="cost",

    schema_drift_step=None,
    schema_version="v1.0",
    optimal_mttr_minutes=35,
    baseline_mttr_minutes=90,
    max_steps=30,
    revenue_per_minute=41000,
)

# ---------------------------------------------------------------------------
# INC005 — Config Deployment Error with Conflicting Signals (Hard)
# ---------------------------------------------------------------------------
INC005 = IncidentCase(
    case_id="INC005",
    title="Config Deployment Error with Conflicting Signals",
    incident_type=IncidentType.CASCADE,
    severity=Severity.P1,
    difficulty="hard",

    initial_alerts=[
        DatadogAlert("auth-service", "jwt_validation_failure_rate", 0.67, 0.01, is_red_herring=False),
        DatadogAlert("api-gateway", "http_401_rate", 0.54, 0.01, is_red_herring=False),
        DatadogAlert("auth-service", "cpu_utilization", 0.73, 0.80, is_red_herring=True),
        DatadogAlert("config-service", "config_load_errors", 12, 0, is_red_herring=False),
        DatadogAlert("user-service", "login_success_rate", 0.31, 0.95, is_red_herring=False),
        DatadogAlert("session-cache", "hit_rate", 0.99, 0.80, is_red_herring=True),  # Misleading
    ],
    initial_slack_messages=[
        SlackMessage("#alerts", "PagerDuty", "2026-04-20T18:00:00Z",
                     "CRITICAL: auth-service JWT validation failures at 67%", is_key_signal=False),
        SlackMessage("#deploys", "deploy-bot", "2026-04-20T17:45:00Z",
                     "config-service v1.9.0 deployed — JWT signing key rotation", is_key_signal=True),
        SlackMessage("#security", "sec-bot", "2026-04-20T17:50:00Z",
                     "Planned key rotation complete — new keys active", is_key_signal=True),
        SlackMessage("#dev", "bob", "2026-04-20T17:55:00Z",
                     "seeing some 401s but session cache looks fine — probably transient", is_key_signal=False),
    ],
    customer_reports=[
        "Being logged out randomly and can't log back in",
        "Two-factor auth failing with 'invalid token'",
        "My API keys stopped working suddenly",
    ],
    affected_services=["auth-service", "api-gateway", "user-service"],
    affected_regions=["us-east-1", "eu-west-1", "ap-southeast-1"],

    root_cause="JWT signing key rotation deployed new key to auth-service but old key still used by api-gateway; tokens signed with new key fail validation at gateway",
    root_cause_service="config-service",
    correct_mitigation_steps=["check_config_deployment", "compare_jwt_keys_across_services", "roll_back_api_gateway_config", "verify_auth_recovery", "plan_proper_key_rotation"],
    correct_escalation_path=["l2_engineer", "security_team", "incident_commander"],

    blast_radius={
        "users_affected": 890000,
        "revenue_per_minute": 78000,
        "slas_breached": ["auth-availability-99.99", "api-gateway-auth-sla"],
    },

    cascade_tree={
        "config-service": ["auth-service", "api-gateway"],
        "auth-service": ["user-service", "checkout-service", "admin-portal"],
        "api-gateway": ["all downstream services"],
    },
    red_herrings=["auth-service-cpu", "session-cache-hit-rate"],
    masked_signals=[
        "api-gateway still using old JWT_SIGNING_KEY env var — not updated during rotation",
        "Key rotation runbook requires synchronized update of all consumers — step skipped",
    ],

    available_runbooks=[
        RunbookStep("rb_compare_jwt_config", "Compare JWT config across services",
                    "Read JWT_SIGNING_KEY from auth-service and api-gateway configs",
                    "Returns key fingerprints — mismatch visible",
                    True, None, True),
        RunbookStep("rb_rollback_gateway_config", "Rollback api-gateway JWT config",
                    "Revert api-gateway to previous JWT_SIGNING_KEY value",
                    "401 rate drops immediately; tokens validate correctly",
                    True, "rb_compare_jwt_config", True),
        RunbookStep("rb_coordinate_key_rotation", "Coordinate full key rotation",
                    "Update all services to new key simultaneously with zero-downtime strategy",
                    "All services using new key — clean rotation",
                    True, "rb_rollback_gateway_config", True),
        RunbookStep("rb_rollback_auth_service", "Rollback auth-service to old key",
                    "Revert auth-service to old JWT_SIGNING_KEY",
                    "Rollback both sides — returns to pre-rotation state",
                    True, None, False),
    ],

    competing_hypotheses=[
        "JWT key rotation deployed to auth-service but not api-gateway — key mismatch",
        "Auth service cryptography library bug causing random validation failures",
        "Session cache serving stale tokens from before security incident",
    ],
    correct_hypothesis_keywords=["jwt", "key", "rotation", "mismatch", "config", "gateway", "signing"],
    expert_review_criteria_set="technical",

    schema_drift_step=None,
    schema_version="v1.0",
    optimal_mttr_minutes=25,
    baseline_mttr_minutes=70,
    max_steps=30,
    revenue_per_minute=78000,
)

# ---------------------------------------------------------------------------
# INC006 — Multi-Region Outage Requiring Coalition (Very Hard)
# ---------------------------------------------------------------------------
INC006 = IncidentCase(
    case_id="INC006",
    title="Multi-Region Cascade: Global CDN Misrouting",
    incident_type=IncidentType.CASCADE,
    severity=Severity.P1,
    difficulty="very_hard",

    initial_alerts=[
        DatadogAlert("global-load-balancer", "routing_error_rate", 0.43, 0.01, is_red_herring=False),
        DatadogAlert("cdn-us-east", "origin_pull_failure_rate", 0.89, 0.05, is_red_herring=False),
        DatadogAlert("cdn-eu-west", "origin_pull_failure_rate", 0.76, 0.05, is_red_herring=False),
        DatadogAlert("origin-us-east", "health_check_failures", 0, 0.05, is_red_herring=False),
        DatadogAlert("origin-eu-west", "health_check_failures", 0, 0.05, is_red_herring=False),
        DatadogAlert("database-us-east", "replication_lag_ms", 12000, 1000, is_red_herring=True),
        DatadogAlert("microservice-mesh", "inter_service_latency_p99_ms", 8900, 1000, is_red_herring=True),
    ],
    initial_slack_messages=[
        SlackMessage("#alerts", "PagerDuty", "2026-04-20T20:00:00Z",
                     "P1: Multi-region routing failures — us-east and eu-west CDN impacted", is_key_signal=False),
        SlackMessage("#infra", "cdn-team", "2026-04-20T19:50:00Z",
                     "CDN routing rule update deployed globally — reduced edge node count for cost", is_key_signal=True),
        SlackMessage("#sre", "bob", "2026-04-20T20:05:00Z",
                     "Origins look healthy from internal checks — CDN is routing to wrong origin pools", is_key_signal=True),
        SlackMessage("#database", "alice", "2026-04-20T20:08:00Z",
                     "DB replication lag from CDN hammering wrong read replicas", is_key_signal=False),
    ],
    customer_reports=[
        "Site completely down in Europe",
        "US users getting 502 errors",
        "App works sometimes then fails — seems geographic",
    ],
    affected_services=["global-load-balancer", "cdn-us-east", "cdn-eu-west", "origin-us-east", "origin-eu-west"],
    affected_regions=["us-east-1", "eu-west-1", "ap-southeast-1"],

    root_cause="CDN routing rule update reduced origin pool mapping incorrectly; CDN edge nodes routing to wrong regional origins; origins healthy but unreachable from wrong region pools",
    root_cause_service="global-load-balancer",
    correct_mitigation_steps=["audit_cdn_routing_rules", "rollback_cdn_config", "verify_origin_pool_mapping", "confirm_multi_region_recovery", "post_incident_review"],
    correct_escalation_path=["sre_agent", "l2_engineer", "pm_agent", "incident_commander"],

    blast_radius={
        "users_affected": 4200000,
        "revenue_per_minute": 340000,
        "slas_breached": ["global-availability-99.99", "eu-regional-sla", "us-regional-sla"],
    },

    cascade_tree={
        "global-load-balancer": ["cdn-us-east", "cdn-eu-west"],
        "cdn-us-east": ["origin-us-east", "database-us-east"],
        "cdn-eu-west": ["origin-eu-west"],
        "origin-us-east": ["microservice-mesh"],
    },
    red_herrings=["database-replication-lag", "inter-service-latency"],
    masked_signals=[
        "CDN routing rule schema change: pool_id is now region_pool_id with different format",
        "Cost optimization PR that reduced origin nodes changed pool assignments",
    ],

    available_runbooks=[
        RunbookStep("rb_audit_cdn_routing", "Audit CDN routing rules",
                    "Compare current routing rules with last known good config",
                    "Shows diff — pool_id mapping changed incorrectly",
                    True, None, True),
        RunbookStep("rb_rollback_cdn_config", "Rollback CDN routing configuration",
                    "Apply previous CDN routing config across all edge nodes",
                    "Routing recovers globally within 3 minutes — CDN propagation",
                    True, "rb_audit_cdn_routing", True),
        RunbookStep("rb_verify_origin_pools", "Verify origin pool mapping",
                    "Confirm each CDN region correctly maps to its origin pool",
                    "All regions confirmed healthy — incident resolved",
                    True, "rb_rollback_cdn_config", True),
        RunbookStep("rb_increase_origin_nodes", "Scale up origin node count",
                    "Add origin nodes to handle increased load",
                    "Does not fix routing — just adds capacity to wrong pools",
                    True, None, False),
    ],

    competing_hypotheses=[
        "CDN routing rule update incorrectly remapped origin pools causing misrouting",
        "DDoS attack from multiple regions overwhelming edge nodes",
        "BGP routing change from ISP causing inter-region connectivity loss",
        "SSL certificate expiry causing CDN-to-origin connection failures",
    ],
    correct_hypothesis_keywords=["cdn", "routing", "pool", "mapping", "config", "rollback", "origin"],
    expert_review_criteria_set="cost",

    schema_drift_step=None,
    schema_version="v1.0",
    optimal_mttr_minutes=42,
    baseline_mttr_minutes=120,
    max_steps=35,
    revenue_per_minute=340000,
)

# ---------------------------------------------------------------------------
# INC007 — CrowdStrike-Scale Global Infrastructure Failure (Nightmare)
# ---------------------------------------------------------------------------
INC007 = IncidentCase(
    case_id="INC007",
    title="CrowdStrike-Scale Global Infrastructure Failure",
    incident_type=IncidentType.CASCADE,
    severity=Severity.P1,
    difficulty="nightmare",

    initial_alerts=[
        DatadogAlert("kernel-module-loader", "load_failure_rate", 1.0, 0.01, is_red_herring=False),
        DatadogAlert("windows-fleet-us-east", "host_availability", 0.12, 0.999, is_red_herring=False),
        DatadogAlert("windows-fleet-eu-west", "host_availability", 0.09, 0.999, is_red_herring=False),
        DatadogAlert("windows-fleet-ap-southeast", "host_availability", 0.07, 0.999, is_red_herring=False),
        DatadogAlert("security-sensor-global", "agent_heartbeat_rate", 0.03, 0.95, is_red_herring=False),
        DatadogAlert("linux-fleet-us-east", "host_availability", 0.99, 0.999, is_red_herring=True),  # Linux unaffected
        DatadogAlert("macos-fleet", "host_availability", 0.98, 0.999, is_red_herring=True),          # Mac unaffected
        DatadogAlert("network-backbone", "packet_loss_rate", 0.02, 0.01, is_red_herring=True),       # Secondary effect
    ],
    initial_slack_messages=[
        SlackMessage("#critical", "PagerDuty", "2026-04-20T22:00:00Z",
                     "NIGHTMARE: Global Windows fleet going dark — millions of hosts", is_key_signal=False),
        SlackMessage("#security", "sec-sensor-team", "2026-04-20T21:55:00Z",
                     "Security sensor auto-update channel-291 pushed 30min ago — content file 0-byte", is_key_signal=True),
        SlackMessage("#infra", "windows-team", "2026-04-20T22:02:00Z",
                     "BSoD loop on all Windows hosts that received security sensor update", is_key_signal=True),
        SlackMessage("#vendor", "vendor-mon", "2026-04-20T22:01:00Z",
                     "Security vendor status: monitoring — no acknowledgement yet", is_key_signal=False),
        SlackMessage("#exec", "cto", "2026-04-20T22:05:00Z",
                     "Board is asking for update. Revenue projections: $5M/minute. What's the ETA?", is_key_signal=False),
    ],
    customer_reports=[
        "Entire Windows infrastructure down — BSoD on every machine",
        "Cannot access any services — complete outage",
        "Hospital systems offline — patient safety risk",
        "Airport check-in systems down — flight delays",
        "ATMs non-functional — financial impact",
    ],
    affected_services=[
        "windows-fleet-us-east", "windows-fleet-eu-west", "windows-fleet-ap-southeast",
        "security-sensor-global", "kernel-module-loader",
        "all-windows-dependent-services",
    ],
    affected_regions=["us-east-1", "us-west-2", "eu-west-1", "eu-central-1", "ap-southeast-1", "ap-northeast-1"],

    root_cause="Security sensor vendor pushed faulty channel file 291 (0 bytes, malformed) to Windows fleet via auto-update; kernel-level driver reads file on boot causing null pointer exception and BSoD loop; manual boot into Safe Mode + file deletion required per host",
    root_cause_service="security-sensor-global",
    correct_mitigation_steps=[
        "halt_auto_update_channel_291",
        "identify_affected_hosts",
        "safe_mode_boot_procedure",
        "delete_channel_291_file",
        "verify_host_recovery",
        "coordinate_manual_recovery_at_scale",
        "communicate_with_vendor",
        "customer_notification_mass",
    ],
    correct_escalation_path=["l2_engineer", "sre_agent", "pm_agent", "executive_escalation", "vendor_contact", "incident_commander"],

    blast_radius={
        "users_affected": 8500000,
        "revenue_per_minute": 5000000,
        "slas_breached": ["all-slas-breached"],
    },

    cascade_tree={
        "security-sensor-global": ["windows-fleet-us-east", "windows-fleet-eu-west", "windows-fleet-ap-southeast"],
        "windows-fleet-us-east": ["payment-service", "auth-service", "order-service", "data-pipelines"],
        "windows-fleet-eu-west": ["eu-payment", "eu-auth", "eu-order"],
        "windows-fleet-ap-southeast": ["apac-payment", "apac-auth"],
    },
    red_herrings=["linux-fleet-availability", "macos-fleet-availability", "network-packet-loss"],
    masked_signals=[
        "Channel file 291 is 0 bytes — not a code bug, a file content bug",
        "Only Windows hosts with auto-update enabled affected",
        "Manual Safe Mode recovery is only fix — no automated remediation possible",
        "Vendor must push corrected channel file before hosts can auto-recover",
    ],

    available_runbooks=[
        RunbookStep("rb_halt_auto_update", "Halt security sensor auto-update",
                    "Disable channel-291 auto-update propagation immediately",
                    "No additional hosts receive faulty file — blast radius contained",
                    True, None, True),
        RunbookStep("rb_safe_mode_recovery", "Safe Mode recovery procedure",
                    "Boot affected Windows host into Safe Mode, delete C:\\Windows\\System32\\drivers\\CrowdStrike\\C-00000291*.sys",
                    "Host boots normally — recovery confirmed",
                    True, "rb_halt_auto_update", True),
        RunbookStep("rb_scale_recovery_ops", "Coordinate large-scale manual recovery",
                    "Deploy recovery runbook to all SREs and on-call staff with host assignment matrix",
                    "Recovery ops running in parallel across all regions",
                    True, "rb_safe_mode_recovery", True),
        RunbookStep("rb_vendor_contact", "Contact security vendor for patch",
                    "Escalate to vendor for corrected channel file and automated recovery tool",
                    "Vendor provides corrected file and recovery automation",
                    True, "rb_halt_auto_update", True),
        RunbookStep("rb_mass_reimaging", "Reimage all affected hosts",
                    "Full OS reimaging of all Windows hosts",
                    "Takes 6+ hours per host — not feasible at scale",
                    False, None, False),
    ],

    competing_hypotheses=[
        "Security sensor faulty channel file (0-byte) causing kernel null pointer exception on boot",
        "Ransomware attack targeting Windows fleet simultaneously across regions",
        "Botched Windows Update causing kernel panic across fleet",
        "Network-level attack corrupting boot sector on Windows hosts",
    ],
    correct_hypothesis_keywords=["channel", "291", "security sensor", "kernel", "bsod", "faulty file", "0 byte", "safe mode", "auto-update"],
    expert_review_criteria_set="communication",

    # Patronus AI schema drift at step 18-22
    schema_drift_step=18,
    schema_version="v1.0",

    optimal_mttr_minutes=90,
    baseline_mttr_minutes=300,
    max_steps=45,
    revenue_per_minute=5000000,
)

# ---------------------------------------------------------------------------
# INC008 — Executive EA: Conflicting Personal vs Work Commitments (Easy, Theme 3.2)
# ---------------------------------------------------------------------------
INC008 = IncidentCase(
    case_id="INC008",
    title="Executive EA Crisis: Board Prep vs First School Concert",
    incident_type=IncidentType.PERSONAL_ASSISTANT,
    severity=Severity.P3,
    difficulty="easy",

    initial_alerts=[
        DatadogAlert("calendar-assistant", "double_booking_conflicts", 2, 1, is_red_herring=False),
        DatadogAlert("exec-mobile", "push_notification_failures", 4, 1, is_red_herring=True),
        DatadogAlert("travel-api", "flight_delay_probability", 0.12, 0.50, is_red_herring=True),
    ],
    initial_slack_messages=[
        SlackMessage("#exec-ea", "pat.lee@acme.com", "2026-04-22T16:05:00Z",
                     "Conflict: Board committee dry-run moved to 19:30 tonight; school concert is 19:00 — both marked accepted on exec calendar",
                     is_key_signal=True),
        SlackMessage("#exec-ea", "scheduling-bot", "2026-04-22T15:58:00Z",
                     "Smart Scheduler auto-accepted both invites (confidence 0.94) — no human confirmation",
                     is_key_signal=True),
        SlackMessage("#family", "spouse-mobile", "2026-04-22T16:10:00Z",
                     "Please tell me you can still make it — first solo tonight",
                     is_key_signal=True),
    ],
    customer_reports=[
        "Board chair expects refreshed risk slides before 20:00",
        "School director notes soloists must arrive by 18:45 for sound check",
    ],
    affected_services=["calendar-assistant", "exec-mobile"],
    affected_regions=["us-east-1"],

    root_cause="Smart scheduling assistant auto-accepted overlapping invites without executive confirmation, creating an impossible double-booking",
    root_cause_service="calendar-assistant",
    correct_mitigation_steps=["acknowledge_conflict", "notify_board_chair", "delegate_slide_review", "release_one_commitment", "confirm_family_ack"],
    correct_escalation_path=["l1_support", "incident_commander"],

    blast_radius={
        "users_affected": 12,
        "revenue_per_minute": 0,
        "slas_breached": ["exec-availability-slo"],
    },

    cascade_tree={},
    red_herrings=["travel-api-flight-delay", "exec-mobile-push"],
    masked_signals=["Auto-accept policy enabled last sprint for 'trusted internal meetings'"],

    available_runbooks=[
        RunbookStep("rb_ack_conflict", "Acknowledge calendar conflict",
                    "Document both commitments and blast radius (family + board)",
                    "Conflict logged with timestamps",
                    True, None, True),
        RunbookStep("rb_notify_board", "Notify board chair of delay risk",
                    "Proactive Slack + status page update for committee dry-run",
                    "Chair acknowledges revised timeline",
                    True, "rb_ack_conflict", True),
        RunbookStep("rb_delegate_slides", "Delegate slide refresh to Chief of Staff",
                    "Hand off deck merge and risk appendix updates",
                    "CoS confirms pickup within 45 minutes",
                    True, "rb_notify_board", True),
        RunbookStep("rb_release_slot", "Release one calendar commitment",
                    "Decline or reschedule the lower-priority block with stakeholder messaging",
                    "Only one hard commitment remains on calendar",
                    True, "rb_delegate_slides", True),
        RunbookStep("rb_family_ack", "Confirm family / school expectations",
                    "Send clear arrival plan or coverage to spouse and school thread",
                    "Family thread shows acknowledgment",
                    True, "rb_release_slot", True),
    ],

    competing_hypotheses=[],
    correct_hypothesis_keywords=["calendar", "auto-accept", "double", "overlap", "smart scheduler", "conflict"],
    expert_review_criteria_set="communication",

    schema_drift_step=None,
    schema_version="v1.0",
    optimal_mttr_minutes=25,
    baseline_mttr_minutes=55,
    max_steps=18,
    revenue_per_minute=0,
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
INCIDENT_LIBRARY: Dict[str, IncidentCase] = {
    "INC001": INC001,
    "INC002": INC002,
    "INC003": INC003,
    "INC004": INC004,
    "INC005": INC005,
    "INC006": INC006,
    "INC007": INC007,
    "INC008": INC008,
}

DIFFICULTY_ORDER = ["easy", "medium", "hard", "very_hard", "nightmare"]


def get_incident(case_id: str) -> IncidentCase:
    if case_id not in INCIDENT_LIBRARY:
        raise ValueError(f"Unknown incident: {case_id}. Valid: {list(INCIDENT_LIBRARY.keys())}")
    return INCIDENT_LIBRARY[case_id]


def get_incidents_by_difficulty(difficulty: str) -> List[IncidentCase]:
    return [inc for inc in INCIDENT_LIBRARY.values() if inc.difficulty == difficulty]


def get_all_incidents() -> List[IncidentCase]:
    return list(INCIDENT_LIBRARY.values())
