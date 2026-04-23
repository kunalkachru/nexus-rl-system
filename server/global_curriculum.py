"""
Global adaptive curriculum (Theme 4 — self-improvement).

Across FastAPI sessions each `NexusEnvironment()` is new, so per-instance
DifficultyAdapter would never accumulate five episodes. This module keeps a
process-wide rolling reward window and difficulty tier so training / Colab /
multi-reset clients see real curriculum progression.
"""

from typing import Dict, List, Optional

from server.incidents import DIFFICULTY_ORDER

PROMOTE_THRESHOLD = 0.55
_RECENT_WINDOW = 5
_MAX_HISTORY = 120

_rewards: List[float] = []
_tier_idx: int = 0


def reset() -> None:
    """Reset tier and history (tests and explicit admin)."""
    global _rewards, _tier_idx
    _rewards = []
    _tier_idx = 0


def get_current_tier() -> str:
    return DIFFICULTY_ORDER[_tier_idx]


def _recent_avg(n: int = _RECENT_WINDOW) -> Optional[float]:
    if len(_rewards) < n:
        return None
    chunk = _rewards[-n:]
    return sum(chunk) / len(chunk)


def record_episode_reward(reward: float) -> Optional[str]:
    """
    Append a completed-episode reward; maybe promote difficulty one step.
    Returns new tier name if promoted, else None.
    """
    global _tier_idx
    _rewards.append(float(reward))
    if len(_rewards) > _MAX_HISTORY:
        del _rewards[: len(_rewards) - _MAX_HISTORY]

    avg = _recent_avg()
    if avg is None:
        return None
    if avg < PROMOTE_THRESHOLD:
        return None
    if _tier_idx >= len(DIFFICULTY_ORDER) - 1:
        return None

    _tier_idx += 1
    return DIFFICULTY_ORDER[_tier_idx]


def status() -> Dict:
    return {
        "current_difficulty_tier": get_current_tier(),
        "tier_index": _tier_idx,
        "episodes_recorded": len(_rewards),
        "recent_avg_reward": _recent_avg(),
        "promote_threshold": PROMOTE_THRESHOLD,
        "recent_window": _RECENT_WINDOW,
        "last_rewards": [round(x, 4) for x in _rewards[-10:]],
    }
