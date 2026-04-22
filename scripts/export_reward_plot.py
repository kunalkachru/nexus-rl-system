#!/usr/bin/env python3
"""
Export a reward-curve PNG for judge slides / BRD Criterion 3 (observable evidence).

Data sources (first match wins):
  1) --url: GET {url}/learning-curve (same JSON as the live dashboard)
  2) --file: JSON list of floats, or {"rewards": [...]}, default ./episode_rewards.json

Output: --out (default outputs/reward_export.png)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import requests  # noqa: E402


def load_rewards_from_url(base_url: str) -> Tuple[List[float], List[float], float]:
    base = base_url.rstrip("/")
    resp = requests.get(f"{base}/learning-curve", timeout=60)
    resp.raise_for_status()
    data = resp.json()
    rewards = list(data.get("rewards") or [])
    rolling = list(data.get("rolling_avg") or [])
    baseline = float(data.get("baseline", 0.265))
    return rewards, rolling, baseline


def load_rewards_from_file(path: Path) -> Tuple[List[float], List[float], float]:
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return [], [], 0.265
    try:
        raw: Any = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return [], [], 0.265
    if isinstance(raw, list):
        rewards = [float(x) for x in raw]
    elif isinstance(raw, dict) and "rewards" in raw:
        rewards = [float(x) for x in raw["rewards"]]
    else:
        rewards = []
    # Match server/app.py get_learning_curve rolling window
    window = 5
    rolling = [
        round(sum(rewards[max(0, i - window) : i + 1]) / min(i + 1, window), 4)
        for i in range(len(rewards))
    ]
    return rewards, rolling, 0.265


def build_figure(
    rewards: List[float],
    rolling: List[float],
    baseline: float,
    title: str = "NEXUS Enhanced — reward history",
) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 5))
    if rewards:
        xs = list(range(1, len(rewards) + 1))
        ax.plot(xs, rewards, "o-", color="#0ea5e9", alpha=0.85, label="Episode reward", markersize=4)
        if rolling and len(rolling) == len(rewards):
            ax.plot(xs, rolling, "-", color="#10b981", linewidth=2, label="Rolling avg")
        ax.axhline(y=baseline, color="#ef4444", linestyle="--", linewidth=1.5, label=f"Baseline {baseline:.3f}")
        ax.set_xlabel("Episode")
        ax.set_ylabel("Reward")
        ax.set_ylim(bottom=0)
        ax.legend(loc="lower right")
    else:
        ax.text(
            0.5,
            0.5,
            "No reward history yet.\nTrain or hit /demo to populate episode_rewards.json\nor pass --url to a live Space.",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=11,
        )
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig


def export_plot(
    rewards: List[float],
    rolling: List[float],
    baseline: float,
    out_path: Path,
    title: str = "NEXUS Enhanced — reward history",
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig = build_figure(rewards, rolling, baseline, title=title)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", help="Base URL of running API (e.g. https://....hf.space)")
    p.add_argument("--file", type=Path, help="Path to episode_rewards.json (list or {rewards: []})")
    p.add_argument(
        "--out",
        type=Path,
        default=Path("outputs/reward_export.png"),
        help="Output PNG path",
    )
    p.add_argument("--title", default="NEXUS Enhanced — reward history", help="Chart title")
    args = p.parse_args(argv)

    if args.url:
        rewards, rolling, baseline = load_rewards_from_url(args.url)
    else:
        fp = args.file or Path("episode_rewards.json")
        rewards, rolling, baseline = load_rewards_from_file(fp)

    export_plot(rewards, rolling, baseline, args.out, title=args.title)
    print(f"Wrote {args.out} ({len(rewards)} episodes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
