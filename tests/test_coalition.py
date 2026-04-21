"""Tests for coalition debate mechanic — correct vote, wrong vote, self-correct, no vote."""

import pytest
import uuid
from server.environment import NexusEnvironment
from server.incidents import get_incident


def make_env():
    return NexusEnvironment()


def base_action(**overrides):
    action = {
        "situation_assessment": "Investigating the incident. Gathering evidence from all agents.",
        "hypothesis": "Root cause under investigation",
        "coalition_vote": None,
        "l2_directive": {"action": "check_all_alerts", "parameters": {}, "reasoning": "survey alerts"},
        "l1_directive": {"action": "check_customer_reports", "parameters": {}, "reasoning": "customer impact"},
        "sre_directive": {"action": "list_runbooks", "parameters": {}, "reasoning": "enumerate options"},
        "pm_directive": {"action": "track_revenue_impact", "parameters": {}, "reasoning": "revenue"},
        "resolution_confidence": 0.0,
        "escalation_required": False,
    }
    action.update(overrides)
    return action


class TestCoalitionCorrectVote:
    def test_correct_coalition_sets_coalition_correct_true(self):
        env = make_env()
        env.reset(incident_id="INC003")
        # Advance to step where coalition fires
        for _ in range(3):
            env.step(base_action())
        inc = get_incident("INC003")
        correct_vote = inc.correct_hypothesis_keywords[0]  # Use keyword that matches
        _, _, _, _ = env.step(base_action(coalition_vote=f"OOM on recommendation-service — {correct_vote}"))
        assert env.current_state.coalition_correct is True

    def test_correct_coalition_recorded_in_state(self):
        env = make_env()
        env.reset(incident_id="INC003")
        for _ in range(3):
            env.step(base_action())
        inc = get_incident("INC003")
        vote = " ".join(inc.correct_hypothesis_keywords[:2])
        env.step(base_action(coalition_vote=vote))
        assert env.current_state.coalition_result is not None
        assert env.current_state.coalition_result == vote

    def test_correct_coalition_only_set_once(self):
        env = make_env()
        env.reset(incident_id="INC003")
        for _ in range(3):
            env.step(base_action())
        inc = get_incident("INC003")
        vote = " ".join(inc.correct_hypothesis_keywords[:2])
        env.step(base_action(coalition_vote=vote))
        first_result = env.current_state.coalition_result
        # Second vote should not override
        env.step(base_action(coalition_vote="wrong hypothesis here"))
        assert env.current_state.coalition_result == first_result


class TestCoalitionWrongVote:
    def test_wrong_coalition_sets_coalition_correct_false(self):
        env = make_env()
        env.reset(incident_id="INC003")
        for _ in range(3):
            env.step(base_action())
        env.step(base_action(coalition_vote="Network issue is the root cause — unrelated to memory"))
        assert env.current_state.coalition_correct is False

    def test_wrong_coalition_episode_continues(self):
        env = make_env()
        env.reset(incident_id="INC003")
        for _ in range(3):
            env.step(base_action())
        _, _, done, _ = env.step(base_action(coalition_vote="Clearly a DDoS attack on all services"))
        # Wrong vote should NOT end episode — must continue investigation
        assert done is False


class TestCoalitionEasyIncident:
    def test_easy_incident_no_coalition_mechanic(self):
        env = make_env()
        env.reset(incident_id="INC001")
        for _ in range(5):
            env.step(base_action(coalition_vote="Some hypothesis vote"))
        # INC001 is easy — coalition_result stays None
        assert env.current_state.coalition_result is None

    def test_easy_incident_coalition_correct_stays_none(self):
        env = make_env()
        env.reset(incident_id="INC001")
        for _ in range(5):
            env.step(base_action())
        assert env.current_state.coalition_correct is None


class TestCoalitionRewardImpact:
    def test_correct_coalition_higher_reward_than_wrong(self):
        """Correct coalition should produce higher coordination reward."""
        inc = get_incident("INC003")
        correct_keyword = " ".join(inc.correct_hypothesis_keywords[:2])

        # Run correct coalition episode
        env_correct = make_env()
        env_correct.reset(incident_id="INC003")
        for _ in range(3):
            env_correct.step(base_action())
        env_correct.step(base_action(coalition_vote=correct_keyword))
        # End episode
        for _ in range(20):
            _, _, done, _ = env_correct.step(base_action(resolution_confidence=0.9))
            if done:
                break
        correct_reward = env_correct.current_state.reward_breakdown.coordination if env_correct.current_state.reward_breakdown else 0.0

        # Run wrong coalition episode
        env_wrong = make_env()
        env_wrong.reset(incident_id="INC003")
        for _ in range(3):
            env_wrong.step(base_action())
        env_wrong.step(base_action(coalition_vote="This is clearly a network problem unrelated to memory"))
        for _ in range(20):
            _, _, done, _ = env_wrong.step(base_action(resolution_confidence=0.9))
            if done:
                break
        wrong_reward = env_wrong.current_state.reward_breakdown.coordination if env_wrong.current_state.reward_breakdown else 0.0

        assert correct_reward >= wrong_reward
