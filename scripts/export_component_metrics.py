#!/usr/bin/env python3
"""
Export timestamped component-level metrics snapshots from a live NEXUS Space.

This script is intentionally lightweight and read-only.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import requests


def fetch_json(base_url: str, endpoint: str) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()


def safe_div(a: float, b: float) -> float:
    return 0.0 if b == 0 else a / b


def build_summary(metrics: Dict[str, Any], training_metrics: Dict[str, Any], learning_curve: Dict[str, Any], ts: str, base_url: str) -> Dict[str, Any]:
    episode_count = int(metrics.get("episode_count") or training_metrics.get("episode_count") or 0)
    avg_reward = float(metrics.get("avg_reward") or training_metrics.get("avg_reward") or 0.0)
    baseline = float(metrics.get("baseline_reward") or learning_curve.get("baseline") or 0.265)
    improvement_pct = float(metrics.get("improvement_pct") or safe_div((avg_reward - baseline) * 100, 1.0))
    dimensions = training_metrics.get("dimensions") or {}
    latest_dimensions = {
        name: (vals[-1] if isinstance(vals, list) and vals else 0.0)
        for name, vals in dimensions.items()
    }

    return {
        "timestamp_utc": ts,
        "base_url": base_url.rstrip("/"),
        "episode_count": episode_count,
        "avg_reward": avg_reward,
        "baseline_reward": baseline,
        "improvement_pct": improvement_pct,
        "best_reward": float(metrics.get("best_reward") or training_metrics.get("best_reward") or 0.0),
        "recent_avg": float(metrics.get("recent_avg") or training_metrics.get("recent_avg") or 0.0),
        "latest_component_signals": latest_dimensions,
        "success_rate": float((metrics.get("training_progress") or {}).get("success_rate") or 0.0),
        "total_steps": int((metrics.get("training_progress") or {}).get("total_steps") or 0),
    }


def markdown_from_summary(summary: Dict[str, Any]) -> str:
    dim = summary.get("latest_component_signals", {})
    dim_lines = "\n".join(
        f"- `{k}`: `{float(v):.4f}`"
        for k, v in sorted(dim.items())
    ) or "- No component metrics available."
    return f"""# Component Metrics Snapshot

Timestamp (UTC): `{summary["timestamp_utc"]}`
Environment URL: `{summary["base_url"]}`

## Headline metrics

- Episode count: `{summary["episode_count"]}`
- Average reward: `{summary["avg_reward"]:.4f}`
- Baseline reward: `{summary["baseline_reward"]:.3f}`
- Improvement: `+{summary["improvement_pct"]:.1f}%`
- Best reward: `{summary["best_reward"]:.4f}`
- Recent average: `{summary["recent_avg"]:.4f}`
- Success rate: `{summary["success_rate"]:.1f}%`
- Total steps observed: `{summary["total_steps"]}`

## Latest component signals

{dim_lines}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Export timestamped component metrics")
    parser.add_argument("--url", required=True, help="Base URL of the deployed environment")
    parser.add_argument("--out-dir", default="docs/project/snapshots", help="Output directory")
    args = parser.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    safe_ts = ts.replace("-", "").replace(":", "")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    metrics = fetch_json(args.url, "/metrics")
    training_metrics = fetch_json(args.url, "/training-metrics")
    learning_curve = fetch_json(args.url, "/learning-curve")
    summary = build_summary(metrics, training_metrics, learning_curve, ts, args.url)

    payload = {
        "summary": summary,
        "metrics": metrics,
        "training_metrics": training_metrics,
        "learning_curve": learning_curve,
    }

    json_path = out_dir / f"component_metrics_{safe_ts}.json"
    md_path = out_dir / f"component_metrics_{safe_ts}.md"

    json_path.write_text(json.dumps(payload, indent=2))
    md_path.write_text(markdown_from_summary(summary))

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
