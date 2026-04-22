"""
Reward model for NEXUS Enhanced.

episode_reward = (
    0.30 * mttr_score             # faster = higher
  + 0.25 * diagnosis_score        # root cause accuracy with evidence
  + 0.20 * customer_score         # proactive notification + SLA preservation
  + 0.15 * coordination_score     # agent comms quality, no duplicate actions
  + 0.05 * oversight_score        # protocol compliance
  + depth_bonus                   # Mercor: UNCAPPED reasoning depth bonus
)

Expert criteria (Snorkel AI): multipliers rotate per episode % 4.
Anti-shortcut: root cause requires evidence; customer impact requires proactive action;
coordination penalises redundant tool queries.
"""

import math
from typing import List
from server.data_models import EpisodeState, RewardBreakdown

# ---------------------------------------------------------------------------
# Snorkel AI: Expert Review Board weight multipliers
# Rotate by episode number % 4
# ---------------------------------------------------------------------------
EXPERT_WEIGHT_MULTIPLIERS = {
    "speed": {
        "mttr": 1.5,
        "diagnosis": 0.8,
        "customer": 1.0,
        "coordination": 1.0,
        "oversight": 1.0,
    },
    "communication": {
        "mttr": 0.8,
        "diagnosis": 0.8,
        "customer": 1.8,
        "coordination": 1.2,
        "oversight": 1.0,
    },
    "technical": {
        "mttr": 0.8,
        "diagnosis": 1.6,
        "customer": 0.8,
        "coordination": 1.0,
        "oversight": 1.2,
    },
    "cost": {
        "mttr": 1.0,
        "diagnosis": 1.0,
        "customer": 1.0,
        "coordination": 1.4,
        "oversight": 1.4,
    },
}

EXPERT_CRITERIA_CYCLE = ["speed", "communication", "technical", "cost"]


def get_expert_criteria(episode_number: int, recent_scores: list = None) -> str:
    """
    Snorkel AI sub-theme — Simulated Experts-in-the-Loop with changing requirements.

    Criteria selection adapts based on recent performance:
    - If IC is fast (avg mttr high) → expert shifts focus to communication/technical
    - If IC neglects customers (avg customer low) → expert emphasises communication
    - If IC is technically weak (avg diagnosis low) → expert emphasises technical
    - Fallback: round-robin cycle so all criteria appear regularly

    This simulates a real expert board that notices agent strengths/weaknesses
    and changes their evaluation focus accordingly — not a static rotation.
    """
    if recent_scores and len(recent_scores) >= 3:
        last = recent_scores[-3:]
        avg_mttr = sum(s.get("mttr", 0.5) for s in last) / len(last)
        avg_customer = sum(s.get("customer", 0.5) for s in last) / len(last)
        avg_diagnosis = sum(s.get("diagnosis", 0.5) for s in last) / len(last)
        avg_coordination = sum(s.get("coordination", 0.5) for s in last) / len(last)

        # Expert reacts to weakest dimension — changes requirements to stress it
        min_dim = min(
            [("communication", avg_customer), ("technical", avg_diagnosis),
             ("cost", avg_coordination), ("speed", avg_mttr)],
            key=lambda x: x[1]
        )
        # Only override if a dimension is clearly weak (below 0.4)
        if min_dim[1] < 0.4:
            return min_dim[0]

    return EXPERT_CRITERIA_CYCLE[episode_number % 4]


def apply_expert_criteria(raw_scores: dict, criteria: str) -> dict:
    """Apply expert multipliers — preserves raw scores, returns adjusted scores."""
    multipliers = EXPERT_WEIGHT_MULTIPLIERS.get(criteria, {k: 1.0 for k in raw_scores})
    return {k: v * multipliers.get(k, 1.0) for k, v in raw_scores.items()}


# ---------------------------------------------------------------------------
# 1. MTTR Score (weight 0.30)
# ---------------------------------------------------------------------------
def compute_mttr_score(state: EpisodeState) -> float:
    """
    Score based on how fast resolution vs optimal and baseline.
    Returns 0.0–1.0. Clamped — cannot go negative.

    If elapsed_minutes <= optimal: score = 1.0
    If elapsed_minutes >= baseline: score = 0.0
    Linear interpolation between optimal and baseline.
    """
    if not state.done:
        # Episode not done — penalise by current elapsed vs max
        t = state.elapsed_minutes
        max_t = state.incident.baseline_mttr_minutes * 1.5
        return max(0.0, 1.0 - t / max_t)

    t = state.elapsed_minutes
    opt = state.incident.optimal_mttr_minutes
    baseline = state.incident.baseline_mttr_minutes

    if t <= opt:
        return 1.0
    if t >= baseline:
        return 0.0
    return 1.0 - (t - opt) / (baseline - opt)


# ---------------------------------------------------------------------------
# 2. Diagnosis Score (weight 0.25) — root cause accuracy with evidence
# ---------------------------------------------------------------------------
def compute_diagnosis_score(state: EpisodeState) -> float:
    """
    Score root cause accuracy. Anti-shortcut: requires evidence via tool queries,
    not just guessing.

    Evidence = tool_outputs pointing to root_cause_service.
    Hypothesis = IC hypothesis matches correct_hypothesis_keywords.
    """
    incident = state.incident
    score = 0.0

    # Evidence check: at least one tool output implicates the root cause service
    root_service = incident.root_cause_service
    evidence_found = any(
        root_service in str(t.parameters) or root_service in str(t.result)
        for t in state.tool_outputs
    )

    # Hypothesis check: IC stated a hypothesis containing correct keywords
    correct_keywords = incident.correct_hypothesis_keywords
    hypothesis_correct = any(
        any(kw.lower() in h.lower() for kw in correct_keywords)
        for h in state.hypotheses_stated
    )

    # Mitigation check: correct runbook steps executed
    correct_steps = {s.step_id for s in incident.available_runbooks if s.is_correct_step}
    steps_done = set(state.runbook_steps_completed)
    mitigation_ratio = len(steps_done & correct_steps) / max(len(correct_steps), 1)

    # Coalition bonus (hard+ incidents)
    coalition_bonus = 0.0
    if incident.competing_hypotheses and state.coalition_correct:
        coalition_bonus = 0.15

    # Evidence is gating — hypothesis without evidence scores low
    if evidence_found and hypothesis_correct:
        score = 0.5 + 0.35 * mitigation_ratio + coalition_bonus
    elif evidence_found:
        score = 0.3 + 0.2 * mitigation_ratio
    elif hypothesis_correct:
        score = 0.1  # Guessed right but no evidence — low score
    else:
        score = 0.0

    return min(1.0, score)


# ---------------------------------------------------------------------------
# 3. Customer Impact Score (weight 0.20)
# ---------------------------------------------------------------------------
def compute_customer_score(state: EpisodeState) -> float:
    """
    Score customer impact management.
    Requires PROACTIVE notification (agent must act, not just identify issue).
    Penalises SLA breaches. Rewards early notification.

    Anti-shortcut: IC cannot score here by just identifying user impact —
    must actually send notification via CustomerPortal tool.
    """
    score = 0.0
    incident = state.incident

    # Proactive notification (mandatory for full score)
    if state.notifications_sent > 0:
        score += 0.5

        # Early notification bonus: rewarded if notified before step 10
        if state.first_notification_step is not None and state.first_notification_step <= 8:
            score += 0.2
        elif state.first_notification_step is not None and state.first_notification_step <= 12:
            score += 0.1

    # SLA preservation
    slas_breached = len(incident.blast_radius.get("slas_breached", []))
    if not state.sla_breached and slas_breached > 0:
        score += 0.3  # SLA preserved despite breach risk
    elif state.sla_breached:
        score -= 0.1  # Penalty for SLA breach (clamped below)

    # Revenue impact minimisation: bonus for fast resolution reducing total loss
    if state.done:
        total_rev_at_risk = incident.revenue_per_minute * incident.baseline_mttr_minutes
        actual_rev_lost = incident.revenue_per_minute * state.elapsed_minutes
        if total_rev_at_risk > 0:
            preservation_ratio = 1.0 - (actual_rev_lost / total_rev_at_risk)
            score += 0.2 * max(0.0, preservation_ratio)

    return max(0.0, min(1.0, score))


# ---------------------------------------------------------------------------
# 4. Coordination Score (weight 0.15)
# ---------------------------------------------------------------------------
def compute_coordination_score(state: EpisodeState) -> float:
    """
    Score coordination quality.
    Rewards: findings shared across agents, coalition success, unique tool queries.
    Penalises: duplicate tool queries, agents querying same tool redundantly.
    """
    score = 0.5  # Start at neutral

    # Findings shared (agents contributing unique observations)
    findings_per_agent: dict = {}
    for f in state.agent_findings:
        findings_per_agent.setdefault(f.agent, 0)
        findings_per_agent[f.agent] += 1

    active_agents = len([a for a, c in findings_per_agent.items() if c > 0])
    if active_agents >= 3:
        score += 0.2
    elif active_agents >= 2:
        score += 0.1

    # Duplicate tool penalty — redundant queries indicate poor coordination
    # Find tool calls with same (agent, tool, action, params)
    seen_calls = set()
    duplicate_count = 0
    for t in state.tool_outputs:
        key = (t.agent, t.tool, t.action, str(sorted(t.parameters.items())))
        if key in seen_calls:
            duplicate_count += 1
        seen_calls.add(key)

    score -= 0.1 * min(duplicate_count, 3)  # Cap penalty at 3 duplicates

    # Low-signal directive penalty — repeated acknowledgements/no-op actions
    # should not look like productive coordination.
    low_signal_findings = sum(
        1 for f in state.agent_findings
        if "acknowledged" in f.finding.lower() or f.tool_used.lower() in {"no_op", "noop"}
    )
    score -= 0.05 * min(low_signal_findings, 4)

    # Coalition bonus
    if state.coalition_result:
        if state.coalition_correct:
            score += 0.2
        else:
            score -= 0.1  # Wrong coalition consensus

    # Findings shared across agents (Team 2+ agents reported findings)
    score += 0.05 * min(state.findings_shared, 4) / 4

    return max(0.0, min(1.0, score))


# ---------------------------------------------------------------------------
# 5. Oversight Compliance Score (weight 0.05)
# ---------------------------------------------------------------------------
def compute_oversight_score(state: EpisodeState) -> float:
    """
    Score protocol compliance based on OversightAgent findings.
    Violations: -0.2 each. Warnings: -0.05 each.
    Floor: 0.0.
    """
    score = 1.0
    for finding in state.oversight_findings:
        if finding.finding_type == "VIOLATION":
            score -= 0.2
        elif finding.finding_type == "WARNING":
            score -= 0.05
    return max(0.0, score)


# ---------------------------------------------------------------------------
# 6. Mercor Reasoning Depth Bonus — UNCAPPED
# ---------------------------------------------------------------------------
def compute_depth_bonus(state: EpisodeState) -> float:
    """
    Mercor sub-theme: reward longer, better-structured IC reasoning.
    UNCAPPED — per BRD Section 10.7: rewards scale with token output without ceiling.

    Calibration principle (per Mercor requirement):
    - Short canned strings (<30 words) earn 0 — they do not represent "reasoning"
    - Medium assessments (30-80 words) earn a small base bonus
    - Long, keyword-rich assessments (80+ words) earn substantial bonus
    - Baseline scripted policy (10-20 word boilerplate) must score near 0
    - Trained model producing 100-300 word detailed analysis should score 0.3-0.8+

    Structure keywords require minimum 30 words to prevent gaming via keyword injection.

    Returns: float (unbounded above 0, typically 0.0–1.0+ for well-reasoned responses)
    """
    if not state.situation_assessments:
        return 0.0

    # Domain-specific keywords that indicate genuine incident reasoning
    STRUCTURE_KEYWORDS = [
        "root cause", "hypothesis", "mitigation", "coalition",
        "red herring", "runbook", "sla breach", "blast radius",
        "escalat", "deploy history", "cascade", "rollback",
    ]

    total_bonus = 0.0
    for i, assessment in enumerate(state.situation_assessments[:10]):  # First 10 only
        words = assessment.lower().split()
        word_count = len(words)

        # Minimum floor: <30 words earns nothing (filters out boilerplate)
        if word_count < 30:
            continue

        # Base: 0.005 per qualifying assessment (reduced from 0.01)
        assessment_score = 0.005

        # Length bonus: 0.002 per word above 80 (raised floor from 50)
        if word_count > 80:
            assessment_score += (word_count - 80) * 0.002

        # Structure bonus: only if assessment is substantive (>=30 words already checked)
        for kw in STRUCTURE_KEYWORDS:
            if kw in assessment.lower():
                assessment_score += 0.04

        # Diminishing returns on later assessments
        diminish_factor = 1.0 / (1 + i * 0.2)
        total_bonus += assessment_score * diminish_factor

    return round(total_bonus, 4)


# ---------------------------------------------------------------------------
# Master reward computation
# ---------------------------------------------------------------------------
BASE_WEIGHTS = {
    "mttr": 0.30,
    "diagnosis": 0.25,
    "customer": 0.20,
    "coordination": 0.15,
    "oversight": 0.05,
}


def compute_total_reward(state: EpisodeState) -> RewardBreakdown:
    """
    Compute full episode reward with expert criteria adjustment.
    Returns RewardBreakdown with all components visible (for demo panel).
    """
    # Raw scores
    raw_scores = {
        "mttr": compute_mttr_score(state),
        "diagnosis": compute_diagnosis_score(state),
        "customer": compute_customer_score(state),
        "coordination": compute_coordination_score(state),
        "oversight": compute_oversight_score(state),
    }

    # Apply expert criteria multipliers (Snorkel AI)
    adjusted = apply_expert_criteria(raw_scores, state.expert_criteria)

    # Normalise adjusted weights to sum to 1.0
    total_multiplied_weight = sum(
        BASE_WEIGHTS[k] * EXPERT_WEIGHT_MULTIPLIERS[state.expert_criteria].get(k, 1.0)
        for k in BASE_WEIGHTS
    )

    # Weighted sum
    weighted_sum = sum(
        adjusted[k] * BASE_WEIGHTS[k]
        for k in BASE_WEIGHTS
    ) / total_multiplied_weight * sum(BASE_WEIGHTS.values())

    # Mercor depth bonus (uncapped)
    depth_bonus = compute_depth_bonus(state)

    total = weighted_sum + depth_bonus

    return RewardBreakdown(
        mttr=round(raw_scores["mttr"], 4),
        diagnosis=round(raw_scores["diagnosis"], 4),
        customer=round(raw_scores["customer"], 4),
        coordination=round(raw_scores["coordination"], 4),
        oversight=round(raw_scores["oversight"], 4),
        depth_bonus=round(depth_bonus, 4),
        expert_criteria=state.expert_criteria,
        total=round(total, 4),
    )


# ---------------------------------------------------------------------------
# Inline unit tests (run directly: python -m server.reward)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uuid
    from server.incidents import get_incident
    from server.data_models import EpisodeState, ToolOutput, AgentFinding

    inc = get_incident("INC001")

    def make_state(**kwargs):
        defaults = dict(
            session_id=str(uuid.uuid4()),
            incident=inc,
            step=5,
            phase="mitigation",
            elapsed_minutes=18.0,
            expert_criteria="speed",
            schema_version="v1.0",
            done=True,
        )
        defaults.update(kwargs)
        return EpisodeState(**defaults)

    # Test 1: Optimal resolution
    s1 = make_state(
        elapsed_minutes=inc.optimal_mttr_minutes,
        notifications_sent=1,
        first_notification_step=6,
        hypotheses_stated=["stripe api header version mismatch causing 400s"],
        runbook_steps_completed=["rb_check_logs", "rb_check_stripe_header", "rb_update_stripe_client"],
        tool_outputs=[
            ToolOutput("datadog", "l2_engineer", "query",
                       {"service": "payment-service"}, {"data": []}, 2),
        ],
        agent_findings=[
            AgentFinding("l2_engineer", "stripe 400 pattern", 3, "check_logs"),
            AgentFinding("sre_agent", "runbook identified", 4, "list_runbooks"),
            AgentFinding("l1_support", "customers notified", 5, "send_notification"),
        ],
    )
    r1 = compute_total_reward(s1)
    assert r1.mttr == 1.0, f"Expected MTTR 1.0, got {r1.mttr}"
    assert r1.customer > 0.5, f"Expected customer > 0.5, got {r1.customer}"
    assert r1.total > 0.7, f"Expected total > 0.7, got {r1.total}"
    print(f"Test 1 (optimal): total={r1.total:.3f} mttr={r1.mttr} diag={r1.diagnosis} cust={r1.customer}")

    # Test 2: No notification — customer score should be low
    s2 = make_state(notifications_sent=0, sla_breached=True)
    r2 = compute_total_reward(s2)
    assert r2.customer < 0.3, f"Expected customer < 0.3 without notification, got {r2.customer}"
    print(f"Test 2 (no notification): customer={r2.customer}")

    # Test 3: Depth bonus with rich assessments
    s3 = make_state(
        situation_assessments=[
            "Root cause hypothesis: payment-service sending wrong Stripe API version header. Evidence from logs shows 400 responses correlating with stripe-client deployment. Mitigation: update stripe client to v2023-11. Timeline: 5 minutes to resolution.",
            "Coalition consensus: all agents agree root cause is stripe header mismatch. Impact: 140k users, $8400/min revenue loss. Runbook steps rb_update_stripe_client identified as correct mitigation.",
        ]
    )
    r3 = compute_total_reward(s3)
    assert r3.depth_bonus > 0.3, f"Expected depth_bonus > 0.3, got {r3.depth_bonus}"
    print(f"Test 3 (depth bonus): depth_bonus={r3.depth_bonus}")

    # Test 4: Expert criteria changes scores
    s4_speed = make_state(elapsed_minutes=15.0, expert_criteria="speed")
    s4_tech = make_state(elapsed_minutes=15.0, expert_criteria="technical")
    r4_speed = compute_total_reward(s4_speed)
    r4_tech = compute_total_reward(s4_tech)
    print(f"Test 4 (criteria): speed_total={r4_speed.total:.3f} tech_total={r4_tech.total:.3f}")

    print("All reward tests passed.")
