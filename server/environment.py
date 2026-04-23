"""
NexusEnvironment — OpenEnv v0.2.3 Gymnasium-compatible interface.

6-phase episode state machine:
  detection → triage → investigation → mitigation → resolution → postmortem

Key mechanics:
- Partial observability: each agent sees only role-scoped tool outputs
- Coalition debate: hard+ incidents require hypothesis vote before resolution
- Schema drift: INC007 at step 18-22 changes RunBook and CustomerPortal field names
- DifficultyAdapter: promotes to harder incidents at avg > 0.55
- OversightAgent: monitors every step, analyses at episode end
"""

import uuid
import random
from typing import Dict, Any, Optional, List, Tuple

from server.data_models import (
    EpisodeState, EpisodeConfig, IncidentCase,
    IncidentCommanderAction, AgentDirective, AgentFinding, ToolOutput,
)
from server.incidents import INCIDENT_LIBRARY, get_incident
from server.tools import ToolRegistry
from server.agents import (
    L1SupportAgent, L2EngineerAgent, SREAgent, ProductManagerAgent,
    OversightAgent, get_specialist_agents, build_agent_observation,
)
from server.reward import compute_total_reward, get_expert_criteria
from server.difficulty import DifficultyAdapter


# Phase progression order
PHASES = ["detection", "triage", "investigation", "mitigation", "resolution", "postmortem"]

# Minutes elapsed per step (simulated time)
MINUTES_PER_STEP = 2.0


class NexusEnvironment:
    """
    OpenEnv v0.2.3 compatible multi-agent incident response environment.

    Usage:
        env = NexusEnvironment()
        obs = env.reset(incident_id="INC003")
        while not done:
            action = coordinator_model.generate(obs)
            obs, reward, done, info = env.step(action)
        print(env.current_state.reward_breakdown)
    """

    metadata = {
        "name": "nexus-enhanced",
        "version": "1.0.0",
        "openenv_version": "0.2.3",
        "num_agents": 6,
        "observation_type": "partial",
        "action_space": "structured_dict",
    }

    def __init__(self, difficulty: Optional[str] = None, seed: Optional[int] = None):
        # difficulty=None → follow process-wide adaptive tier (Theme 4, multi-session)
        self.difficulty_adapter = DifficultyAdapter(starting_difficulty=difficulty)
        self.seed = seed
        self._episode_count = 0

        # Agents (specialists are scripted; IC is the trained agent)
        self._specialists = get_specialist_agents()
        self._oversight = OversightAgent()

        # Current episode state
        self.current_state: Optional[EpisodeState] = None
        self._tool_registry: Optional[ToolRegistry] = None

    # ------------------------------------------------------------------
    # OpenEnv interface: reset
    # ------------------------------------------------------------------
    def reset(self, incident_id: Optional[str] = None,
              difficulty: Optional[str] = None,
              seed: Optional[int] = None,
              session_id: Optional[str] = None,
              expert_criteria: Optional[str] = None) -> Dict[str, Any]:
        """
        Reset environment for new episode.
        Returns initial observation dict for the Incident Commander.
        """
        config = EpisodeConfig(
            incident_id=incident_id,
            difficulty=difficulty,
            seed=seed or self.seed,
            session_id=session_id or str(uuid.uuid4()),
            expert_criteria=expert_criteria,
        )

        incident = self.difficulty_adapter.select_incident(config)
        criteria = expert_criteria or get_expert_criteria(self._episode_count)

        self.current_state = EpisodeState(
            session_id=config.session_id,
            incident=incident,
            step=0,
            phase="detection",
            elapsed_minutes=0.0,
            expert_criteria=criteria,
            schema_version=incident.schema_version,
        )

        self._tool_registry = ToolRegistry(incident)

        # Re-instantiate L1 (stateful notification tracking)
        self._specialists["l1_support"] = L1SupportAgent()

        return self._build_ic_observation()

    # ------------------------------------------------------------------
    # OpenEnv interface: step
    # ------------------------------------------------------------------
    def step(self, action: Dict[str, Any]) -> Tuple[Dict, float, bool, Dict]:
        """
        Execute one IC action. Dispatches directives to specialists.
        Returns (observation, reward, done, info).

        action dict keys (all optional except situation_assessment):
          situation_assessment: str   — IC's reasoning (scored by Mercor bonus)
          hypothesis: str             — IC's root cause hypothesis
          coalition_vote: str         — hypothesis vote (medium+ incidents)
          l1_directive: dict          — {action, parameters, reasoning}
          l2_directive: dict          — {action, parameters, reasoning}
          sre_directive: dict         — {action, parameters, reasoning}
          pm_directive: dict          — {action, parameters, reasoning}
          resolution_confidence: float — episode ends if > 0.80
          escalation_required: bool
          direct_tool: dict           — IC can query tools directly
            {tool, action, parameters}
        """
        assert self.current_state is not None, "Call reset() before step()"
        state = self.current_state

        if state.done:
            return self._build_ic_observation(), 0.0, True, {"error": "Episode already done"}

        state.step += 1
        state.elapsed_minutes += MINUTES_PER_STEP

        # --- Patronus AI: Schema drift trigger (INC007 step 18–22) ---
        self._maybe_trigger_schema_drift(state)

        # --- Record IC situation assessment (Mercor depth bonus) ---
        assessment = action.get("situation_assessment", "")
        if assessment:
            state.situation_assessments.append(assessment)

        hypothesis = action.get("hypothesis", "")
        if hypothesis:
            state.hypotheses_stated.append(hypothesis)

        # --- IC direct tool call ---
        direct_tool = action.get("direct_tool")
        if direct_tool:
            tool_result = self._tool_registry.call(
                tool=direct_tool.get("tool", ""),
                action=direct_tool.get("action", ""),
                agent="incident_commander",
                params=direct_tool.get("parameters", {}),
            )
            tool_output = ToolOutput(
                tool=direct_tool.get("tool", ""),
                agent="incident_commander",
                action=direct_tool.get("action", ""),
                parameters=direct_tool.get("parameters", {}),
                result=tool_result,
                step=state.step,
            )
            state.tool_outputs.append(tool_output)

        # --- Dispatch directives to specialists ---
        directives = {
            "l1_support": action.get("l1_directive"),
            "l2_engineer": action.get("l2_directive"),
            "sre_agent": action.get("sre_directive"),
            "product_manager": action.get("pm_directive"),
        }

        for agent_name, directive_dict in directives.items():
            if not directive_dict:
                continue
            directive = AgentDirective(
                action=directive_dict.get("action", "no_op"),
                parameters=directive_dict.get("parameters", {}),
                reasoning=directive_dict.get("reasoning", ""),
            )
            specialist = self._specialists[agent_name]
            finding = specialist.act(state, directive, self._tool_registry)
            state.agent_findings.append(finding)
            state.findings_shared += 1

            # Track notifications
            if "notification" in finding.tool_used.lower() or "notify" in finding.finding.lower():
                if state.notifications_sent == 0:
                    state.first_notification_step = state.step
                state.notifications_sent += 1

            # Track runbook steps executed by SRE
            if agent_name == "sre_agent" and directive.action == "execute_runbook_step":
                step_id = directive.parameters.get("step_id", "")
                if step_id and step_id not in state.runbook_steps_completed:
                    state.runbook_steps_completed.append(step_id)

            # Record tool output for specialist actions
            tool_output = ToolOutput(
                tool=self._infer_tool(directive.action),
                agent=agent_name,
                action=directive.action,
                parameters=directive.parameters,
                result={"finding": finding.finding},
                step=state.step,
            )
            state.tool_outputs.append(tool_output)

        # --- Coalition mechanic (medium+ incidents) ---
        coalition_vote = action.get("coalition_vote")
        if coalition_vote:
            self._process_coalition(state, coalition_vote)

        # --- Oversight monitoring (real-time) ---
        new_findings = self._oversight.monitor(state, self._tool_registry)
        state.oversight_findings.extend(new_findings)

        # --- Phase progression ---
        self._advance_phase(state, action)

        # --- Escalation ---
        if action.get("escalation_required") and not state.escalation_done:
            state.escalation_done = True

        # --- Episode termination check ---
        resolution_confidence = float(action.get("resolution_confidence", 0.0))
        done = self._check_done(state, resolution_confidence)

        reward = 0.0
        info: Dict[str, Any] = {
            "step": state.step,
            "phase": state.phase,
            "elapsed_minutes": state.elapsed_minutes,
        }

        if done:
            state.done = True
            # Oversight end-of-episode analysis
            end_findings = self._oversight.analyse(state)
            state.oversight_findings.extend(end_findings)

            breakdown = compute_total_reward(state)
            state.reward_breakdown = breakdown
            reward = breakdown.total

            self._episode_count += 1
            new_difficulty = self.difficulty_adapter.record_episode(reward)

            info.update({
                "reward_breakdown": {
                    "mttr": breakdown.mttr,
                    "diagnosis": breakdown.diagnosis,
                    "customer": breakdown.customer,
                    "coordination": breakdown.coordination,
                    "oversight": breakdown.oversight,
                    "depth_bonus": breakdown.depth_bonus,
                    "expert_criteria": breakdown.expert_criteria,
                    "total": breakdown.total,
                },
                "oversight_report": self._oversight.explain(state),
                "difficulty_advanced_to": new_difficulty,
                "episode_count": self._episode_count,
            })

        return self._build_ic_observation(), reward, done, info

    # ------------------------------------------------------------------
    # Coalition mechanic
    # ------------------------------------------------------------------
    def _process_coalition(self, state: EpisodeState, vote: str):
        """
        Process IC coalition vote. Requires medium+ difficulty with competing hypotheses.
        Correct coalition: coalition_correct=True, findings_shared += 2.
        Wrong coalition: coalition_correct=False — must self-correct.
        """
        incident = state.incident
        if not incident.competing_hypotheses:
            return
        if state.coalition_result is not None:
            return  # Already decided
        if state.step < 2:
            return  # Too early for coalition

        vote_lower = vote.lower()
        correct = any(kw.lower() in vote_lower for kw in incident.correct_hypothesis_keywords)
        state.coalition_result = vote
        state.coalition_correct = correct
        state.findings_shared += 2  # Coalition counts as 2 shared findings

    # ------------------------------------------------------------------
    # Schema drift (Patronus AI)
    # ------------------------------------------------------------------
    def _maybe_trigger_schema_drift(self, state: EpisodeState):
        """Trigger schema drift for INC007 at the specified step."""
        drift_step = state.incident.schema_drift_step
        if drift_step is None:
            return
        if state.step == drift_step and state.schema_version == "v1.0":
            state.schema_version = "v2.0"
            self._tool_registry.apply_schema_drift("v2.0")

    # ------------------------------------------------------------------
    # Phase progression
    # ------------------------------------------------------------------
    def _advance_phase(self, state: EpisodeState, action: Dict[str, Any]):
        """Advance phase based on accumulated evidence."""
        current_idx = PHASES.index(state.phase)

        if state.phase == "detection" and state.step >= 2:
            state.phase = "triage"

        elif state.phase == "triage":
            # Require at least two findings and some cross-agent coverage before investigation.
            # Fallback on step>=4 prevents deadlock when one specialist is repeatedly used.
            active_agents = {f.agent for f in state.agent_findings}
            if len(state.agent_findings) >= 2 and (len(active_agents) >= 2 or state.step >= 4):
                state.phase = "investigation"

        elif state.phase == "investigation":
            # Advance to mitigation if hypothesis stated and evidence found
            root_service = state.incident.root_cause_service
            evidence_found = any(
                root_service in str(t.parameters) or root_service in str(t.result)
                for t in state.tool_outputs
            )
            if state.hypotheses_stated and (state.runbook_steps_completed or evidence_found):
                state.phase = "mitigation"
            # Also advance if coalition succeeded
            elif state.coalition_correct:
                state.phase = "mitigation"

        elif state.phase == "mitigation":
            # Advance to resolution if key runbook steps completed
            correct_steps = {s.step_id for s in state.incident.available_runbooks if s.is_correct_step}
            done_correct = set(state.runbook_steps_completed) & correct_steps
            if len(done_correct) >= max(1, len(correct_steps) - 1):
                state.phase = "resolution"

        elif state.phase == "resolution":
            # Advance to postmortem when IC declares high confidence
            if float(action.get("resolution_confidence", 0.0)) > 0.80:
                state.phase = "postmortem"

    # ------------------------------------------------------------------
    # Episode termination
    # ------------------------------------------------------------------
    def _check_done(self, state: EpisodeState, resolution_confidence: float) -> bool:
        """Episode ends when: IC confident in postmortem, or max steps reached."""
        if state.phase == "postmortem" and resolution_confidence > 0.80:
            return True
        if state.step >= state.incident.max_steps:
            return True
        return False

    # ------------------------------------------------------------------
    # IC observation builder
    # ------------------------------------------------------------------
    def _build_ic_observation(self) -> Dict[str, Any]:
        """
        Build Incident Commander observation.

        Halluminate sub-theme — task discovery mechanic:
        At step 0 (detection), the IC only sees a terse PagerDuty-style alert summary.
        Full alert details, affected services, and competing hypotheses are discovered
        through agent findings as the episode progresses. The IC must dispatch agents
        to investigate before the full picture emerges.
        """
        state = self.current_state
        if state is None:
            return {}

        incident = state.incident
        is_detection_start = state.step == 0

        # Halluminate: at step 0, expose only terse alert count — IC must discover scope
        if is_detection_start:
            firing_count = sum(1 for a in incident.initial_alerts if a.value > a.threshold)
            initial_alerts_view = [{"summary": f"{firing_count} alert(s) firing — dispatch agents to investigate"}]
            customer_reports_view = [f"{len(incident.customer_reports)} customer report(s) received"]
            affected_services_view = ["unknown — pending L2 investigation"]
        else:
            initial_alerts_view = [
                {
                    "service": a.service,
                    "metric": a.metric,
                    "value": a.value,
                    "threshold": a.threshold,
                    "status": "CRITICAL" if a.value > a.threshold else "OK",
                }
                for a in incident.initial_alerts
            ]
            customer_reports_view = incident.customer_reports
            affected_services_view = incident.affected_services

        return {
            "session_id": state.session_id,
            "incident_id": incident.case_id,
            "incident_title": incident.title,
            "severity": incident.severity.value,
            "difficulty": incident.difficulty,
            "phase": state.phase,
            "step": state.step,
            "elapsed_minutes": state.elapsed_minutes,
            "schema_version": state.schema_version,
            "expert_criteria": state.expert_criteria,

            # Progressive discovery — full details unlock after step 0
            "initial_alerts": initial_alerts_view,
            "customer_reports": customer_reports_view,
            "affected_services": affected_services_view,
            "affected_regions": incident.affected_regions,

            # Accumulated findings from all specialists
            "agent_findings": [
                {"agent": f.agent, "finding": f.finding, "step": f.step}
                for f in state.agent_findings[-10:]  # Last 10
            ],

            # Competing hypotheses (medium+ incidents)
            "competing_hypotheses": incident.competing_hypotheses,
            "coalition_result": state.coalition_result,
            "coalition_correct": state.coalition_correct,

            # State tracking
            "runbook_steps_completed": state.runbook_steps_completed,
            "notifications_sent": state.notifications_sent,
            "escalation_done": state.escalation_done,
            "oversight_violations": len([f for f in state.oversight_findings if f.finding_type == "VIOLATION"]),

            # Episode end
            "done": state.done,
            "reward_breakdown": (
                {
                    "mttr": state.reward_breakdown.mttr,
                    "diagnosis": state.reward_breakdown.diagnosis,
                    "customer": state.reward_breakdown.customer,
                    "coordination": state.reward_breakdown.coordination,
                    "oversight": state.reward_breakdown.oversight,
                    "depth_bonus": state.reward_breakdown.depth_bonus,
                    "total": state.reward_breakdown.total,
                }
                if state.reward_breakdown else None
            ),
        }

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def _infer_tool(self, action: str) -> str:
        action_lower = action.lower()
        if "slack" in action_lower or "message" in action_lower or "deploy" in action_lower:
            return "slack"
        if "runbook" in action_lower or "execute" in action_lower:
            return "runbook"
        if "metric" in action_lower or "alert" in action_lower or "datadog" in action_lower:
            return "datadog"
        if "ticket" in action_lower or "jira" in action_lower or "escalat" in action_lower:
            return "jira"
        if "customer" in action_lower or "notification" in action_lower or "sla" in action_lower:
            return "customer_portal"
        return "unknown"

    def compute_reward(self) -> float:
        """Convenience method for smoke test: compute reward on current state."""
        if self.current_state is None:
            return 0.0
        breakdown = compute_total_reward(self.current_state)
        self.current_state.reward_breakdown = breakdown
        return breakdown.total

    def get_tool_registry(self) -> Optional[ToolRegistry]:
        return self._tool_registry

    def get_state(self) -> Optional[EpisodeState]:
        return self.current_state
