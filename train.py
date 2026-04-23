"""
train.py — Reward-conditioned CPU training loop for NEXUS Enhanced IC agent.

Reward-conditioned prompting: at each episode, the IC policy is shown its
past N episode rewards + breakdowns so it can self-correct (Scale AI / Snorkel AI).
This simulates the expert review feedback loop without GPU training.

Usage:
    # 30 episodes on easy+medium (matches pre-event benchmark)
    python train.py --episodes 30

    # Specific difficulty mix
    python train.py --episodes 20 --difficulties easy,medium,hard

    # Single incident stress test
    python train.py --episodes 10 --incident INC003

    # Save artifacts + generate chart
    python train.py --episodes 30 --output training_artifacts/run_$(date +%s).json --plot

    # LLM-backed IC (requires API key in env)
    python train.py --episodes 20 --policy llm --model claude-haiku-4-5-20251001

    # Quiet mode for CI / headless
    python train.py --episodes 10 --quiet
"""

import os
import sys
import json
import argparse
import time
import random
from typing import Dict, List, Optional, Tuple

from client import NexusClient
from inference import baseline_policy, make_llm_policy, build_ic_prompt, parse_llm_action


# ---------------------------------------------------------------------------
# Reward-conditioned wrapper policy
# ---------------------------------------------------------------------------

class RewardConditionedPolicy:
    """
    Wraps a base policy and injects past episode performance
    into each step observation so the IC can self-correct.

    This implements the Snorkel AI 'simulated expert' mechanic:
    the expert feedback is the previous-episode reward breakdown.
    """

    def __init__(self, base_policy, history_window: int = 3):
        self.base_policy = base_policy
        self.history_window: List[Dict] = []
        self.history_window_size = history_window

    def record_episode(self, result: Dict):
        """Call after each episode to update feedback history."""
        rb = result.get("reward_breakdown") or {}
        self.history_window.append({
            "incident": result.get("incident_id"),
            "reward": result.get("reward", 0.0),
            "mttr": rb.get("mttr", 0.0),
            "diagnosis": rb.get("diagnosis", 0.0),
            "customer": rb.get("customer", 0.0),
            "coordination": rb.get("coordination", 0.0),
            "depth_bonus": rb.get("depth_bonus", 0.0),
            "notifications_sent": result.get("notifications_sent", 0),
            "coalition_correct": result.get("coalition_correct"),
        })
        if len(self.history_window) > self.history_window_size:
            self.history_window.pop(0)

    def _feedback_text(self) -> str:
        if not self.history_window:
            return ""
        lines = ["PAST PERFORMANCE (use to self-correct):"]
        for ep in self.history_window[-3:]:
            lines.append(
                f"  {ep['incident']}: reward={ep['reward']:.3f} "
                f"mttr={ep['mttr']:.2f} diag={ep['diagnosis']:.2f} "
                f"cust={ep['customer']:.2f} coord={ep['coordination']:.2f} "
                f"notif={ep['notifications_sent']} "
                f"coalition={'correct' if ep['coalition_correct'] else 'wrong' if ep['coalition_correct'] is False else 'n/a'}"
            )
        avg = sum(e["reward"] for e in self.history_window) / len(self.history_window)
        weakest = min(
            [("mttr", avg), ("customer", sum(e["customer"] for e in self.history_window) / len(self.history_window)),
             ("diagnosis", sum(e["diagnosis"] for e in self.history_window) / len(self.history_window)),
             ("coordination", sum(e["coordination"] for e in self.history_window) / len(self.history_window))],
            key=lambda x: x[1]
        )
        lines.append(f"  Rolling avg reward: {avg:.3f} | Weakest dimension: {weakest[0]} ({weakest[1]:.2f})")
        return "\n".join(lines)

    def __call__(self, obs: Dict) -> Dict:
        # Inject feedback into situation_assessment prefix
        action = self.base_policy(obs)
        feedback = self._feedback_text()
        if feedback and action.get("situation_assessment"):
            action["situation_assessment"] = f"{feedback}\n\n{action['situation_assessment']}"
        return action


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

DIFFICULTY_INCIDENTS = {
    "easy": ["INC001", "INC002", "INC008"],
    "medium": ["INC003", "INC004"],
    "hard": ["INC005", "INC006"],
    "very_hard": ["INC006"],
    "nightmare": ["INC007"],
}


def select_incident(difficulties: List[str], episode: int, fixed_incident: Optional[str]) -> Tuple[str, str]:
    """Returns (incident_id, difficulty)."""
    if fixed_incident:
        # Infer difficulty from incident ID
        for diff, ids in DIFFICULTY_INCIDENTS.items():
            if fixed_incident in ids:
                return fixed_incident, diff
        return fixed_incident, "unknown"
    difficulty = difficulties[episode % len(difficulties)]
    candidates = DIFFICULTY_INCIDENTS.get(difficulty, ["INC001"])
    incident_id = candidates[episode % len(candidates)]
    return incident_id, difficulty


def compute_rolling_avg(rewards: List[float], window: int = 5) -> List[float]:
    rolling = []
    for i in range(len(rewards)):
        chunk = rewards[max(0, i - window + 1):i + 1]
        rolling.append(sum(chunk) / len(chunk))
    return rolling


def save_results(results: List[Dict], output_path: str):
    rewards = [r["reward"] for r in results]
    avg = sum(rewards) / len(rewards) if rewards else 0.0
    data = {
        "episodes": len(results),
        "avg_reward": round(avg, 4),
        "min_reward": round(min(rewards), 4) if rewards else 0.0,
        "max_reward": round(max(rewards), 4) if rewards else 0.0,
        "rolling_avg": compute_rolling_avg(rewards),
        "results": results,
    }
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    return data


def plot_curve(results: List[Dict], plot_path: str, baseline_value: float = 0.265):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("[train] matplotlib not installed — skipping plot")
        return

    rewards = [r["reward"] for r in results]
    rolling = compute_rolling_avg(rewards, window=5)
    episodes = list(range(1, len(rewards) + 1))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Left: reward curve
    ax1.plot(episodes, rewards, "o", alpha=0.5, color="#4C72B0", markersize=5, label="Episode reward")
    ax1.plot(episodes, rolling, "-", color="#4C72B0", linewidth=2.5, label="5-ep rolling avg")
    ax1.axhline(y=baseline_value, color="red", linestyle="--", linewidth=1.5, label=f"Baseline ({baseline_value})")
    ax1.set_xlabel("Episode", fontsize=11)
    ax1.set_ylabel("Total Reward", fontsize=11)
    ax1.set_title("NEXUS Enhanced — Training Reward Curve", fontsize=12, fontweight="bold")
    ax1.legend(fontsize=10)
    ax1.set_ylim(0, max(1.1, max(rewards) + 0.1) if rewards else 1.1)
    ax1.grid(alpha=0.3)

    # Right: reward breakdown heatmap (last 10 episodes)
    last = results[-min(10, len(results)):]
    dims = ["mttr", "diagnosis", "customer", "coordination", "depth_bonus"]
    labels = ["MTTR", "Diag", "Cust", "Coord", "Depth"]
    data = [[r["reward_breakdown"].get(d, 0.0) if r.get("reward_breakdown") else 0.0
             for d in dims] for r in last]

    import numpy as np
    arr = np.array(data)
    im = ax2.imshow(arr.T, aspect="auto", cmap="YlOrRd", vmin=0, vmax=1)
    ax2.set_xticks(range(len(last)))
    ax2.set_xticklabels([f"ep{len(results)-len(last)+i+1}" for i in range(len(last))], fontsize=8, rotation=45)
    ax2.set_yticks(range(len(dims)))
    ax2.set_yticklabels(labels, fontsize=10)
    ax2.set_title("Reward Breakdown — Last 10 Episodes", fontsize=12, fontweight="bold")
    plt.colorbar(im, ax=ax2, fraction=0.046, pad=0.04)

    plt.tight_layout()
    os.makedirs(os.path.dirname(plot_path) if os.path.dirname(plot_path) else ".", exist_ok=True)
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[train] Chart saved → {plot_path}")


# ---------------------------------------------------------------------------
# Main training loop
# ---------------------------------------------------------------------------

def train(
    client: NexusClient,
    policy,
    difficulties: List[str],
    fixed_incident: Optional[str],
    n_episodes: int,
    max_steps: int,
    quiet: bool,
    verbose: bool,
) -> List[Dict]:
    """
    Run the full training loop with reward-conditioned feedback.
    Returns list of episode result dicts.
    """
    rc_policy = RewardConditionedPolicy(policy, history_window=3)
    results = []

    # Per-difficulty tracking
    difficulty_stats: Dict[str, List[float]] = {d: [] for d in difficulties}

    print(f"\n{'='*60}")
    print(f"NEXUS Enhanced — Training Loop")
    print(f"Episodes: {n_episodes} | Difficulties: {difficulties}")
    print(f"Max steps/episode: {max_steps}")
    print(f"{'='*60}\n")

    for ep in range(n_episodes):
        incident_id, difficulty = select_incident(difficulties, ep, fixed_incident)

        if not quiet:
            print(f"Episode {ep+1:3d}/{n_episodes} | {incident_id} ({difficulty})", end="", flush=True)

        t0 = time.time()
        try:
            sid, obs = client.reset(incident_id=incident_id)
            step = 0
            reward = 0.0
            done = False
            info = {}

            while not done and step < max_steps:
                action = rc_policy(obs)
                obs, reward, done, info = client.step(sid, action)
                step += 1

                if verbose:
                    print(f"\n    step={step} phase={obs.get('phase','?')} done={done} reward={reward:.4f}")

            state = client.get_state(sid)
            rb = state.get("reward_breakdown") or {}

            result = {
                "episode": ep + 1,
                "incident_id": incident_id,
                "difficulty": difficulty,
                "steps": step,
                "reward": reward,
                "done": done,
                "reward_breakdown": rb,
                "notifications_sent": state.get("notifications_sent", 0),
                "coalition_correct": state.get("coalition_correct"),
                "oversight_violations": state.get("oversight_violations", 0),
                "elapsed_minutes": state.get("elapsed_minutes", 0),
                "wall_time_s": round(time.time() - t0, 2),
            }

        except Exception as e:
            print(f" ERROR: {e}")
            result = {
                "episode": ep + 1, "incident_id": incident_id, "difficulty": difficulty,
                "steps": 0, "reward": 0.0, "done": False, "reward_breakdown": {},
                "error": str(e), "wall_time_s": round(time.time() - t0, 2),
            }

        results.append(result)
        rc_policy.record_episode(result)

        if difficulty in difficulty_stats:
            difficulty_stats[difficulty].append(result["reward"])

        if not quiet:
            rb = result.get("reward_breakdown", {})
            print(
                f" → reward={result['reward']:.4f} steps={result['steps']} "
                f"done={result['done']} notif={result.get('notifications_sent',0)} "
                f"({result['wall_time_s']}s)"
            )
            if rb and not verbose:
                print(
                    f"         mttr={rb.get('mttr',0):.3f} diag={rb.get('diagnosis',0):.3f} "
                    f"cust={rb.get('customer',0):.3f} coord={rb.get('coordination',0):.3f} "
                    f"depth={rb.get('depth_bonus',0):.3f}"
                )

        # Print rolling stats every 5 episodes
        if (ep + 1) % 5 == 0 and not quiet:
            recent = [r["reward"] for r in results[-5:]]
            rolling_avg = sum(recent) / len(recent)
            print(f"\n  --- 5-ep rolling avg: {rolling_avg:.4f} ---\n")

    # Final summary
    rewards = [r["reward"] for r in results]
    print(f"\n{'='*60}")
    print(f"Training complete — {n_episodes} episodes")
    print(f"Avg reward:     {sum(rewards)/len(rewards):.4f}")
    print(f"Best reward:    {max(rewards):.4f}  (ep {rewards.index(max(rewards))+1})")
    print(f"Worst reward:   {min(rewards):.4f}  (ep {rewards.index(min(rewards))+1})")
    for diff, scores in difficulty_stats.items():
        if scores:
            print(f"  {diff:<12}: {len(scores)} episodes | avg={sum(scores)/len(scores):.4f}")
    print(f"{'='*60}\n")

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="NEXUS Enhanced reward-conditioned training loop (CPU)"
    )
    parser.add_argument("--server", default="http://localhost:7860", help="NEXUS server URL")
    parser.add_argument("--episodes", type=int, default=30, help="Total episodes to run")
    parser.add_argument("--difficulties", default="easy,medium",
                        help="Comma-separated difficulty list to cycle (easy,medium,hard,very_hard,nightmare)")
    parser.add_argument("--incident", help="Fix a single incident ID for all episodes")
    parser.add_argument("--policy", choices=["baseline", "llm"], default="baseline",
                        help="IC policy type")
    parser.add_argument("--model", default="claude-haiku-4-5-20251001",
                        help="LLM model ID for --policy llm")
    parser.add_argument("--max-steps", type=int, default=28, help="Max steps per episode")
    parser.add_argument("--output", default="training_artifacts/train_results.json",
                        help="JSON output path")
    parser.add_argument("--plot", action="store_true", help="Generate matplotlib reward curve PNG")
    parser.add_argument("--plot-path", default="training_artifacts/reward_curve.png",
                        help="Plot output path (used with --plot)")
    parser.add_argument("--verbose", action="store_true", help="Print every step")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-episode output")
    args = parser.parse_args()

    client = NexusClient(args.server)

    # Verify server
    try:
        h = client.health()
        print(f"Server: {h.get('status')} | {h.get('environment','nexus-enhanced')} v{h.get('version','?')}")
    except Exception as e:
        print(f"Cannot reach server at {args.server}: {e}")
        sys.exit(1)

    # Build base policy
    if args.policy == "llm":
        base_policy = make_llm_policy(args.model)
        print(f"Policy: LLM ({args.model})")
    else:
        base_policy = baseline_policy
        print("Policy: Scripted baseline + reward-conditioned feedback")

    difficulties = [d.strip() for d in args.difficulties.split(",")]
    for d in difficulties:
        if d not in DIFFICULTY_INCIDENTS:
            print(f"Unknown difficulty '{d}'. Valid: {list(DIFFICULTY_INCIDENTS.keys())}")
            sys.exit(1)

    # Run training loop
    results = train(
        client=client,
        policy=base_policy,
        difficulties=difficulties,
        fixed_incident=args.incident,
        n_episodes=args.episodes,
        max_steps=args.max_steps,
        quiet=args.quiet,
        verbose=args.verbose,
    )

    # Save results
    data = save_results(results, args.output)
    print(f"Results saved → {args.output}")

    # Generate plot
    if args.plot:
        plot_curve(results, args.plot_path)

    return data


if __name__ == "__main__":
    main()
