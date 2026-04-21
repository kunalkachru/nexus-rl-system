"""
NexusClient — HTTP client for the NEXUS Enhanced FastAPI server.

Usage:
    from client import NexusClient
    c = NexusClient("http://localhost:7860")
    sid, obs = c.reset("INC003")
    obs, reward, done, info = c.step(sid, {"situation_assessment": "...", "resolution_confidence": 0.0})
"""

import json
import requests
from typing import Dict, Any, List, Optional, Tuple


class NexusClient:
    """Thin HTTP client wrapping every NEXUS FastAPI endpoint."""

    def __init__(self, base_url: str = "http://localhost:7860", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get(self, path: str) -> Dict:
        r = requests.get(f"{self.base_url}{path}", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, payload: Dict) -> Dict:
        r = requests.post(f"{self.base_url}{path}", json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------
    # Core episode interface
    # ------------------------------------------------------------------
    def health(self) -> Dict:
        """Return server health dict."""
        return self._get("/health")

    def reset(
        self,
        incident_id: Optional[str] = None,
        difficulty: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> Tuple[str, Dict]:
        """
        Reset environment for a new episode.
        Returns (session_id, observation).
        """
        payload = {}
        if incident_id:
            payload["incident_id"] = incident_id
        if difficulty:
            payload["difficulty"] = difficulty
        if seed is not None:
            payload["seed"] = seed

        resp = self._post("/reset", payload)
        return resp["session_id"], resp["observation"]

    def step(self, session_id: str, action: Dict[str, Any]) -> Tuple[Dict, float, bool, Dict]:
        """
        Execute one IC action.
        Returns (observation, reward, done, info).

        action keys (all optional except situation_assessment):
            situation_assessment: str
            hypothesis: str
            coalition_vote: str | None
            l1_directive: {action, parameters, reasoning}
            l2_directive: {action, parameters, reasoning}
            sre_directive: {action, parameters, reasoning}
            pm_directive: {action, parameters, reasoning}
            resolution_confidence: float  (>0.80 can end episode)
            escalation_required: bool
        """
        resp = self._post(f"/step/{session_id}", action)
        return (
            resp["observation"],
            float(resp["reward"]),
            bool(resp["done"]),
            resp.get("info", {}),
        )

    def get_state(self, session_id: str) -> Dict:
        """Return full episode state for a session."""
        return self._get(f"/state/{session_id}")

    def get_reward(self, session_id: str) -> Dict:
        """Return current reward breakdown without ending the episode."""
        return self._get(f"/reward/{session_id}")

    # ------------------------------------------------------------------
    # Information endpoints
    # ------------------------------------------------------------------
    def list_incidents(self) -> List[Dict]:
        """Return all 7 incident definitions."""
        return self._get("/incidents")["incidents"]

    def get_incident(self, incident_id: str) -> Dict:
        """Return one incident definition."""
        return self._get(f"/incidents/{incident_id}")

    def get_metrics(self) -> Dict:
        """Return global episode metrics."""
        return self._get("/metrics")

    def get_history(self) -> Dict:
        """Return completed episode history with reward breakdowns."""
        return self._get("/history")

    def get_learning_curve(self) -> Dict:
        """Return reward time-series and rolling average."""
        return self._get("/learning-curve")

    def run_demo(self, incident_id: str = "INC003") -> Dict:
        """Run a pre-scripted demo episode. Returns full trace."""
        return self._post(f"/demo/run/{incident_id}", {})

    # ------------------------------------------------------------------
    # Convenience: run a full episode with a policy function
    # ------------------------------------------------------------------
    def run_episode(
        self,
        policy,
        incident_id: Optional[str] = None,
        difficulty: Optional[str] = None,
        seed: Optional[int] = None,
        max_steps: int = 30,
        verbose: bool = False,
    ) -> Dict:
        """
        Run one full episode using `policy(obs) -> action`.

        Returns summary dict:
            {session_id, incident_id, steps, reward, done,
             reward_breakdown, notifications_sent, coalition_correct}
        """
        sid, obs = self.reset(incident_id=incident_id, difficulty=difficulty, seed=seed)
        step = 0
        reward = 0.0
        done = False
        info = {}

        while not done and step < max_steps:
            action = policy(obs)
            obs, reward, done, info = self.step(sid, action)
            step += 1
            if verbose:
                phase = obs.get("phase", "?")
                conf = action.get("resolution_confidence", 0.0)
                print(f"  step={step:2d} phase={phase:<14} reward={reward:.4f} done={done} conf={conf:.2f}")

        state = self.get_state(sid)
        rb = state.get("reward_breakdown") or {}

        return {
            "session_id": sid,
            "incident_id": obs.get("incident_id", incident_id),
            "steps": step,
            "reward": reward,
            "done": done,
            "reward_breakdown": rb,
            "notifications_sent": state.get("notifications_sent", 0),
            "coalition_correct": state.get("coalition_correct"),
            "oversight_violations": state.get("oversight_violations", 0),
            "elapsed_minutes": state.get("elapsed_minutes", 0),
        }
