"""
DifficultyAdapter — Theme 4 self-improvement mechanic.

Tracks agent performance and promotes to harder incidents when average reward
exceeds thresholds (see server.global_curriculum for cross-session persistence).

Incident selection:
- If no explicit incident_id in config: select randomly from current difficulty tier
- If all current-tier incidents have been seen: expand to include next tier
"""

import random
from typing import List, Optional, Dict
from server.data_models import EpisodeConfig, IncidentCase
from server.incidents import INCIDENT_LIBRARY, DIFFICULTY_ORDER, get_incidents_by_difficulty
from server import global_curriculum


PROMOTE_THRESHOLD = 0.55  # avg reward over 5 episodes → advance difficulty (mirrors global)
VARIANT_THRESHOLD = 0.65  # avg reward over 5 episodes → generate harder variant


class DifficultyAdapter:
    """Tracks performance and manages difficulty progression."""

    def __init__(self, starting_difficulty: Optional[str] = None):
        # None = follow process-wide adaptive tier (HTTP / Colab multi-episode)
        self.current_difficulty = (
            starting_difficulty
            if starting_difficulty is not None
            else global_curriculum.get_current_tier()
        )
        self._episode_rewards: List[float] = []
        self._episode_count = 0

    def record_episode(self, reward: float) -> Optional[str]:
        """Record reward; sync tier from global curriculum. Returns new tier name if promoted."""
        self._episode_rewards.append(reward)
        self._episode_count += 1
        promoted = global_curriculum.record_episode_reward(reward)
        self.current_difficulty = global_curriculum.get_current_tier()
        return promoted

    def _recent_avg(self, n: int = 5) -> Optional[float]:
        recent = self._episode_rewards[-n:]
        if len(recent) < n:
            return None
        return sum(recent) / len(recent)

    def should_promote(self) -> bool:
        avg = self._recent_avg()
        if avg is None:
            return False
        current_idx = DIFFICULTY_ORDER.index(self.current_difficulty) if self.current_difficulty in DIFFICULTY_ORDER else 0
        return avg >= PROMOTE_THRESHOLD and current_idx < len(DIFFICULTY_ORDER) - 1

    def should_generate_variant(self) -> bool:
        avg = self._recent_avg()
        return avg is not None and avg >= VARIANT_THRESHOLD

    def maybe_advance(self) -> Optional[str]:
        """Legacy hook; promotion is applied inside record_episode()."""
        return None

    def select_incident(self, config: EpisodeConfig) -> IncidentCase:
        """
        Select incident for next episode.
        Priority: explicit incident_id > config difficulty > current difficulty.
        """
        if config.incident_id:
            return INCIDENT_LIBRARY[config.incident_id]

        difficulty = config.difficulty or self.current_difficulty
        candidates = get_incidents_by_difficulty(difficulty)

        if not candidates:
            # Fallback to easy
            candidates = get_incidents_by_difficulty("easy")

        seed = config.seed
        if seed is not None:
            random.seed(seed)

        return random.choice(candidates)

    @property
    def episode_count(self) -> int:
        return self._episode_count

    @property
    def recent_average(self) -> Optional[float]:
        return self._recent_avg()

    def status(self) -> Dict:
        return {
            "current_difficulty": self.current_difficulty,
            "episode_count": self._episode_count,
            "recent_avg_reward": self.recent_average,
            "promote_threshold": PROMOTE_THRESHOLD,
            "variant_threshold": VARIANT_THRESHOLD,
            "episodes_since_last_5": min(5, len(self._episode_rewards)),
        }
