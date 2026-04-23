from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class IncidentType(Enum):
    SERVICE_DOWN = "service_down"
    PERF_DEGRADATION = "perf_degradation"
    CASCADE = "cascade"
    SECURITY = "security"
    DATA = "data"
    # Theme 3.2 — personalized delegation / conflicting priorities (BRD §12)
    PERSONAL_ASSISTANT = "personal_assistant"


class Severity(Enum):
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"
    P4 = "p4"


@dataclass
class DatadogAlert:
    service: str
    metric: str
    value: float
    threshold: float
    is_red_herring: bool  # Hidden from agents; used by OversightAgent


@dataclass
class SlackMessage:
    channel: str
    author: str
    timestamp: str
    content: str
    is_key_signal: bool  # Hidden; marks deploy history entries


@dataclass
class RunbookStep:
    step_id: str          # v1.0 field — becomes runbook_ref in v2.0 (INC007 schema drift)
    title: str
    description: str
    expected_outcome: str  # v1.0 field — split into expected_output + success_criteria in v2.0
    rollback_available: bool
    prerequisite_step_id: Optional[str]
    is_correct_step: bool  # Hidden from agents


@dataclass
class IncidentCase:
    case_id: str
    title: str
    incident_type: IncidentType
    severity: Severity
    difficulty: str  # "easy" | "medium" | "hard" | "nightmare"

    # What agents see at episode start
    initial_alerts: List[DatadogAlert]
    initial_slack_messages: List[SlackMessage]
    customer_reports: List[str]
    affected_services: List[str]
    affected_regions: List[str]

    # Ground truth — hidden from agents, used for scoring only
    root_cause: str
    root_cause_service: str
    correct_mitigation_steps: List[str]
    correct_escalation_path: List[str]
    blast_radius: Dict  # users_affected, revenue_per_minute, slas_breached

    # Complexity
    cascade_tree: Dict[str, List[str]]
    red_herrings: List[str]      # DatadogAlert.service names — is_red_herring=True
    masked_signals: List[str]    # Only discoverable via deep tool queries

    # Runbooks
    available_runbooks: List[RunbookStep]

    # Coalition debate (medium+ difficulty)
    competing_hypotheses: List[str]
    correct_hypothesis_keywords: List[str]

    # Snorkel AI — expert review criteria rotate per episode
    expert_review_criteria_set: str

    # Patronus AI — schema drift (INC007 only)
    schema_drift_step: Optional[int]  # None for non-nightmare
    schema_version: str = "v1.0"

    # Episode config
    optimal_mttr_minutes: int = 20
    baseline_mttr_minutes: int = 60
    max_steps: int = 25
    revenue_per_minute: int = 5000


@dataclass
class AgentDirective:
    action: str
    parameters: Dict[str, Any]
    reasoning: str


@dataclass
class IncidentCommanderAction:
    situation_assessment: str      # Scored by Mercor depth bonus
    hypothesis: str
    coalition_vote: Optional[str]
    l1_action: AgentDirective
    l2_action: AgentDirective
    sre_action: AgentDirective
    pm_action: AgentDirective
    severity_assessment: str
    resolution_confidence: float   # Episode ends when > 0.80
    escalation_required: bool


@dataclass
class OversightFinding:
    agent: str
    finding_type: str       # "VIOLATION" | "WARNING"
    finding_category: str   # "UNAUTHORIZED_ESCALATION" | "DUPLICATE_TOOL_QUERY" | etc.
    description: str
    recommendation: str
    step: int


@dataclass
class ToolOutput:
    tool: str
    agent: str
    action: str
    parameters: Dict
    result: Dict
    step: int


@dataclass
class AgentFinding:
    agent: str
    finding: str
    step: int
    tool_used: str


@dataclass
class RewardBreakdown:
    mttr: float
    diagnosis: float
    customer: float
    coordination: float
    oversight: float
    depth_bonus: float
    expert_criteria: str
    total: float


@dataclass
class EpisodeState:
    session_id: str
    incident: IncidentCase
    step: int
    phase: str  # detection|triage|investigation|mitigation|resolution|postmortem
    elapsed_minutes: float
    expert_criteria: str
    schema_version: str

    # Accumulated during episode
    tool_outputs: List[ToolOutput] = field(default_factory=list)
    agent_findings: List[AgentFinding] = field(default_factory=list)
    oversight_findings: List[OversightFinding] = field(default_factory=list)
    runbook_steps_completed: List[str] = field(default_factory=list)
    notifications_sent: int = 0
    first_notification_step: Optional[int] = None
    escalation_done: bool = False
    coalition_result: Optional[str] = None
    coalition_correct: Optional[bool] = None
    situation_assessments: List[str] = field(default_factory=list)
    hypotheses_stated: List[str] = field(default_factory=list)
    sla_breached: bool = False
    findings_shared: int = 0
    done: bool = False
    reward_breakdown: Optional[RewardBreakdown] = None


@dataclass
class EpisodeConfig:
    incident_id: Optional[str] = None
    difficulty: Optional[str] = None
    seed: Optional[int] = None
    session_id: Optional[str] = None
    expert_criteria: Optional[str] = None
