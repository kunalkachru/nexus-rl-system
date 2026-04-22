"""
NexusClient — HTTP client for the NEXUS Enhanced environment server.

Used by train.py and inference.py to drive episodes via the REST API.
Works against both local (uvicorn) and HuggingFace Space deployments.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

import requests


class NexusClient:
    """
    Thin wrapper around the NEXUS FastAPI server.

    Usage:
        client = NexusClient("http://localhost:7860")
        session_id, obs = client.reset("INC003")
        obs, reward, done, info = client.step(session_id, action)
    """

    def __init__(self, base_url: str = "http://localhost:7860", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # Core episode interface
    # ------------------------------------------------------------------

    def reset(
        self,
        incident_id: Optional[str] = None,
        difficulty: Optional[str] = None,
        seed: Optional[int] = None,
        expert_criteria: Optional[str] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Start a new episode.
        Returns (session_id, observation).
        """
        payload = {}
        if incident_id:
            payload["incident_id"] = incident_id
        if difficulty:
            payload["difficulty"] = difficulty
        if seed is not None:
            payload["seed"] = seed
        if expert_criteria:
            payload["expert_criteria"] = expert_criteria

        resp = self._post("/reset", payload)
        session_id = resp["session_id"]
        observation = resp["observation"]
        return session_id, observation

    def step(
        self,
        session_id: str,
        action: Dict[str, Any],
    ) -> tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """
        Execute one IC action.
        Returns (observation, reward, done, info).
        """
        resp = self._post(f"/step/{session_id}", action)
        return resp["observation"], resp["reward"], resp["done"], resp.get("info", {})

    def get_state(self, session_id: str) -> Dict[str, Any]:
        return self._get(f"/state/{session_id}")

    def get_observation(self, session_id: str) -> Dict[str, Any]:
        return self._get(f"/observation/{session_id}")

    def get_reward(self, session_id: str) -> Dict[str, Any]:
        return self._get(f"/reward/{session_id}")

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def run_demo(self, incident_id: str = "INC003") -> Dict[str, Any]:
        return self._post(f"/demo/run/{incident_id}", {})

    def list_incidents(self) -> list[Dict[str, Any]]:
        return self._get("/incidents")["incidents"]

    def get_metrics(self) -> Dict[str, Any]:
        return self._get("/metrics")

    def health(self) -> Dict[str, Any]:
        return self._get("/health")

    def wait_until_ready(self, max_wait: int = 60) -> bool:
        """Poll /health until the server responds or timeout."""
        deadline = time.time() + max_wait
        while time.time() < deadline:
            try:
                resp = self.health()
                if resp.get("status") in ("ok", "healthy"):
                    return True
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(2)
        return False

    # ------------------------------------------------------------------
    # Episode runner (used by train.py)
    # ------------------------------------------------------------------

    def run_episode(
        self,
        incident_id: Optional[str] = None,
        difficulty: Optional[str] = None,
        policy_fn=None,
        max_steps: int = 45,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """
        Run a full episode end-to-end using policy_fn to generate actions.

        policy_fn(observation: dict) -> action: dict
        If policy_fn is None, uses a scripted baseline policy.

        Returns episode summary dict with reward breakdown.
        """
        session_id, obs = self.reset(incident_id=incident_id, difficulty=difficulty)
        if policy_fn is None:
            policy_fn = _baseline_policy

        trajectory = []
        total_reward = 0.0
        done = False
        step = 0

        while not done and step < max_steps:
            action = policy_fn(obs)
            obs, reward, done, info = self.step(session_id, action)
            total_reward += reward
            trajectory.append({
                "step": step + 1,
                "reward": reward,
                "done": done,
                "phase": obs.get("phase"),
            })
            step += 1
            if verbose:
                print(f"  step={step:2d} phase={obs.get('phase'):12s} reward={reward:.4f} done={done}")

        state = self.get_state(session_id)
        return {
            "session_id": session_id,
            "incident_id": state.get("incident_id"),
            "steps": step,
            "elapsed_minutes": state.get("elapsed_minutes"),
            "total_reward": total_reward,
            "reward_breakdown": state.get("reward_breakdown"),
            "coalition_result": state.get("coalition_result"),
            "coalition_correct": state.get("coalition_correct"),
            "notifications_sent": state.get("notifications_sent"),
            "phase": state.get("phase"),
            "trajectory": trajectory,
        }

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _post(self, path: str, payload: Dict) -> Dict:
        url = f"{self.base_url}{path}"
        try:
            resp = self._session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"POST {path} failed: {e.response.status_code} — {e.response.text}") from e

    def _get(self, path: str) -> Dict:
        url = f"{self.base_url}{path}"
        try:
            resp = self._session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"GET {path} failed: {e.response.status_code} — {e.response.text}") from e


# ------------------------------------------------------------------
# Baseline scripted policy (used as fallback and for pre-event curves)
# ------------------------------------------------------------------

def _baseline_policy(obs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic rule-based policy. Used for:
    - Generating pre-event reward curves (Criterion 3 evidence)
    - Filling in remaining steps during GRPO rollouts

    Not optimized — just coherent enough to produce valid episodes.
    """
    phase = obs.get("phase", "detection")
    step = obs.get("step", 0)
    incident_id = obs.get("incident_id", "INC001")
    competing = obs.get("competing_hypotheses", [])

    # Build situation assessment from current alerts
    alerts = obs.get("initial_alerts", [])
    firing = [a for a in alerts if a.get("status") == "CRITICAL"]
    assessment = (
        f"Phase: {phase}. Step {step}. "
        f"Investigating {incident_id}. "
        f"{len(firing)} active alerts. "
        f"Dispatching agents to gather evidence and identify root cause."
    )

    # Select coalition vote if hypotheses available
    coalition_vote = None
    if competing and step >= 10:
        coalition_vote = competing[-1]  # Pick last (usually correct in our incidents)

    # Resolution confidence ramps with step
    resolution_confidence = 0.0
    if phase in ("resolution", "postmortem") or step > 18:
        resolution_confidence = min(0.9, 0.05 * step)

    return {
        "situation_assessment": assessment,
        "hypothesis": f"Root cause investigation ongoing for {incident_id}",
        "coalition_vote": coalition_vote,
        "l1_directive": {
            "action": "check_customer_reports",
            "parameters": {},
            "reasoning": "Assess customer impact",
        },
        "l2_directive": {
            "action": "check_all_alerts",
            "parameters": {},
            "reasoning": "Sweep all active alerts",
        },
        "sre_directive": {
            "action": "execute_runbook_step",
            "parameters": {"step_id": "rb_check_logs"},
            "reasoning": "Follow runbook procedure",
        },
        "pm_directive": {
            "action": "track_revenue_impact",
            "parameters": {},
            "reasoning": "Track SLA and revenue",
        },
        "resolution_confidence": resolution_confidence,
        "escalation_required": step > 8,
    }
