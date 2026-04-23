"""Process-wide adaptive curriculum (Theme 4)."""

from server import global_curriculum


def test_five_strong_episodes_promote_tier_once():
    global_curriculum.reset()
    assert global_curriculum.get_current_tier() == "easy"
    promoted = None
    for _ in range(5):
        promoted = global_curriculum.record_episode_reward(0.62)
    assert global_curriculum.get_current_tier() == "medium"
    assert promoted == "medium"


def test_status_shape():
    global_curriculum.reset()
    global_curriculum.record_episode_reward(0.1)
    st = global_curriculum.status()
    assert st["tier_index"] == 0
    assert st["episodes_recorded"] == 1
    assert "last_rewards" in st
