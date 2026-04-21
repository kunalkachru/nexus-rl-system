"""Models for NEXUS Enhanced OpenEnv Environment

Defines agent action and observation models for type validation.
"""

from pydantic import BaseModel
from typing import Dict, Any, Optional


class AgentAction(BaseModel):
    """Action schema for Incident Commander agent"""
    situation_assessment: str
    resolution_confidence: float


class EnvironmentConfig(BaseModel):
    """Configuration for NEXUS environment"""
    incident_id: str
    episode_id: Optional[str] = None
    max_steps: int = 50
    difficulty_tier: Optional[str] = None


class RewardBreakdown(BaseModel):
    """6-dimensional reward structure"""
    mttr: float
    diagnosis: float
    customer: float
    coordination: float
    oversight: float
    depth_bonus: float
    total: float
    expert_criteria: Optional[str] = None


class StepResult(BaseModel):
    """Result of environment step"""
    observation: Dict[str, Any]
    reward: float
    done: bool
    info: Dict[str, Any]
