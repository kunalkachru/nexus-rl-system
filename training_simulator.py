"""
Training Simulator — Mimics real GRPO training without an LLM

This script demonstrates how the environment works in real training:
  1. Episode resets with incident
  2. Mock IC reads observation
  3. Mock IC generates action (assessment, hypothesis, confidence)
  4. Environment rewards the action
  5. IC learns from reward signal (in real training)
  6. Repeat for multiple episodes

vs. Selenium testing which tests the UI/form filling.
"""

import json
from server.environment import NexusEnvironment
from server.incidents import INCIDENT_LIBRARY

class MockIncidentCommander:
    """Simulates an Incident Commander that reads observation and generates actions"""

    def __init__(self, incident_id: str):
        self.incident_id = incident_id
        self.incident = INCIDENT_LIBRARY[incident_id]
        self.step_count = 0

    def generate_action(self, observation: dict) -> dict:
        """
        Mock IC reads observation and generates action.

        In real training, this would be an LLM prompt:
          "You are an incident commander. Given this observation,
           what is your assessment, hypothesis, and confidence?"

        For simulation, we use heuristic rules.
        """
        self.step_count += 1

        # Mock logic: read observation → generate action
        assessment = self._generate_assessment(observation)
        hypothesis = self._generate_hypothesis(observation)
        confidence = self._generate_confidence(observation)

        action = {
            "situation_assessment": assessment,
            "hypothesis": hypothesis,
            "resolution_confidence": confidence
        }

        print(f"\n[Step {self.step_count}] Mock IC Generated Action:")
        print(f"  Assessment: {assessment[:60]}...")
        print(f"  Hypothesis: {hypothesis[:60]}...")
        print(f"  Confidence: {confidence:.2f}")

        return action

    def _generate_assessment(self, obs: dict) -> str:
        """Generate assessment from observation"""
        parts = []

        if obs.get('initial_alerts'):
            parts.append(f"{obs['initial_alerts'][0]}")
        if obs.get('customer_reports'):
            parts.append(f"{obs['customer_reports'][0]}")
        if obs.get('affected_regions'):
            parts.append(f"Affected regions: {', '.join(obs['affected_regions'])}")
        if obs.get('agent_findings'):
            parts.append(f"Agent reports: {len(obs['agent_findings'])} findings")

        return " | ".join(parts) if parts else "Investigating incident..."

    def _generate_hypothesis(self, obs: dict) -> str:
        """Generate hypothesis from competing hypotheses"""
        if obs.get('competing_hypotheses'):
            # Mock IC picks the first hypothesis (in real training, LLM would reason about best one)
            return obs['competing_hypotheses'][0]
        return "Unable to determine root cause"

    def _generate_confidence(self, obs: dict) -> float:
        """Generate confidence based on agent findings"""
        # Heuristic: more findings = higher confidence
        num_findings = len(obs.get('agent_findings', []))
        step_progress = min(self.step_count / 5.0, 0.95)  # Confidence increases with steps

        base_confidence = 0.1 + (num_findings * 0.15) + step_progress
        return min(base_confidence, 0.95)


def run_training_simulation(incident_id: str, num_episodes: int = 3, steps_per_episode: int = 5):
    """
    Simulate training episodes.

    This is what GRPO training does (without the LLM learning part):
      For each episode:
        1. Reset environment
        2. For each step:
           a. Get observation
           b. IC generates action
           c. Step environment
           d. Collect reward
        3. Track episode reward
    """

    print(f"\n{'='*80}")
    print(f"TRAINING SIMULATOR: {incident_id}")
    print(f"Episodes: {num_episodes} | Steps per episode: {steps_per_episode}")
    print(f"{'='*80}\n")

    env = NexusEnvironment()
    episode_rewards = []

    for episode_num in range(num_episodes):
        print(f"\n{'─'*80}")
        print(f"EPISODE {episode_num + 1}/{num_episodes}")
        print(f"{'─'*80}")

        # Reset environment
        observation = env.reset(incident_id=incident_id)
        ic = MockIncidentCommander(incident_id)

        print(f"Incident: {observation['incident_title']}")
        print(f"Severity: {observation['severity']}")
        print(f"Difficulty: {observation['difficulty']}")

        episode_total_reward = 0.0

        for step_num in range(steps_per_episode):
            # Mock IC reads observation and generates action
            action = ic.generate_action(observation)

            # Environment steps (same as real training)
            observation, reward, done, info = env.step(action)
            episode_total_reward += reward

            print(f"  → Reward this step: {reward:.4f}")
            print(f"  → Phase: {observation['phase']}")

            if done:
                print(f"  → Episode ended (done=True)")
                break

        # Final reward breakdown
        final_reward = env.compute_reward()
        episode_rewards.append(final_reward)

        print(f"\n[Episode Summary]")
        print(f"  Total steps: {ic.step_count}")
        print(f"  Final reward: {final_reward:.4f}")
        print(f"  (Step rewards: {episode_total_reward:.4f})")

    # Training curve
    print(f"\n{'='*80}")
    print(f"TRAINING RESULTS")
    print(f"{'='*80}")
    print(f"Episode rewards: {[f'{r:.4f}' for r in episode_rewards]}")
    print(f"Average reward: {sum(episode_rewards) / len(episode_rewards):.4f}")
    print(f"Best episode: {max(episode_rewards):.4f}")
    print(f"\nThis is what GRPO training tracks and tries to improve!")
    print(f"(In real training, the IC model learns to maximize this reward over time)")


def compare_testing_approaches():
    """Show the difference between Selenium testing and training simulation"""

    comparison = """
    ╔════════════════════════════════════════════════════════════════════════════╗
    ║                    TESTING APPROACHES COMPARISON                           ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║                                                                            ║
    ║  SELENIUM BROWSER TESTING (UI Testing)                                    ║
    ║  ─────────────────────────────────────                                    ║
    ║  ✓ Opens browser: http://localhost:7860/web                               ║
    ║  ✓ Clicks incident in dropdown                                            ║
    ║  ✓ Waits for form to appear                                               ║
    ║  ✓ Fills text fields (assessment, hypothesis)                             ║
    ║  ✓ Sets confidence slider                                                 ║
    ║  ✓ Clicks "Execute Step" button                                           ║
    ║  ✓ Verifies HTML/DOM updated correctly                                    ║
    ║                                                                            ║
    ║  Tests: Dashboard UI works, form fields respond, buttons work              ║
    ║  NOT testing: Training pipeline or reward logic                            ║
    ║                                                                            ║
    ║  ─────────────────────────────────────────────────────────────────────    ║
    ║                                                                            ║
    ║  TRAINING SIMULATION (Environment Testing)                                ║
    ║  ────────────────────────────────────────                                 ║
    ║  ✓ Creates NexusEnvironment instance                                      ║
    ║  ✓ Calls env.reset(incident_id) → gets observation JSON                   ║
    ║  ✓ Mock IC reads observation                                              ║
    ║  ✓ Mock IC generates: assessment, hypothesis, confidence                  ║
    ║  ✓ Calls env.step(action) → gets reward                                   ║
    ║  ✓ Tracks reward curve across episodes                                    ║
    ║                                                                            ║
    ║  Tests: Environment logic, reward calculations, episode mechanics          ║
    ║  This is what GRPO training actually does!                                ║
    ║                                                                            ║
    ║  ─────────────────────────────────────────────────────────────────────    ║
    ║                                                                            ║
    ║  REAL GRPO TRAINING (What happens April 25-26)                            ║
    ║  ──────────────────────────────────────────────                           ║
    ║  ✓ Same as Training Simulation BUT:                                       ║
    ║  ✓ IC is a real LLM (Qwen2.5-1.5B)                                        ║
    ║  ✓ LLM learns from reward signal (GRPO optimizer)                         ║
    ║  ✓ LLM weights updated based on trajectory rewards                        ║
    ║  ✓ Repeat 1000+ episodes → reward improves                                ║
    ║                                                                            ║
    ║  Tests: Can LLM learn to solve incidents? Do rewards guide learning?       ║
    ║                                                                            ║
    ╚════════════════════════════════════════════════════════════════════════════╝
    """

    print(comparison)


if __name__ == "__main__":
    # Show the difference between approaches
    compare_testing_approaches()

    # Run training simulation
    print("\n\nRunning training simulation on INC003...\n")
    run_training_simulation("INC003", num_episodes=3, steps_per_episode=5)
