#!/usr/bin/env python3
"""
Export a timestamped submission snapshot from a live NEXUS Space.

Outputs:
  - JSON payload (metrics + learning_curve summary)
  - Markdown summary for judge-facing references
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import requests


def fetch_json(base_url: str, path: str) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()


def build_summary(metrics: Dict[str, Any], curve: Dict[str, Any], ts: str, base_url: str) -> Dict[str, Any]:
    rewards = list(curve.get("rewards", []))
    return {
        "timestamp_utc": ts,
        "base_url": base_url.rstrip("/"),
        "episode_count": int(curve.get("episode_count", len(rewards))),
        "avg_reward": float(metrics.get("avg_reward", curve.get("current_avg", 0.0))),
        "best_reward": float(metrics.get("best_reward", max(rewards) if rewards else 0.0)),
        "baseline_reward": float(metrics.get("baseline_reward", curve.get("baseline", 0.265))),
        "improvement_pct": float(metrics.get("improvement_pct", 0.0)),
        "recent_avg": float(metrics.get("recent_avg", 0.0)),
    }


def write_markdown(path: Path, summary: Dict[str, Any]) -> None:
    md = f"""# NEXUS Submission Snapshot

Timestamp (UTC): `{summary["timestamp_utc"]}`
Environment URL: `{summary["base_url"]}`

- Episode count: `{summary["episode_count"]}`
- Average reward: `{summary["avg_reward"]:.4f}`
- Best reward: `{summary["best_reward"]:.4f}`
- Baseline reward: `{summary["baseline_reward"]:.3f}`
- Improvement: `+{summary["improvement_pct"]:.1f}%`
- Recent average: `{summary["recent_avg"]:.4f}`
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(md)


def main() -> int:
    p = argparse.ArgumentParser(description="Export timestamped submission snapshot")
    p.add_argument("--url", required=True, help="Base URL, e.g. https://...hf.space")
    p.add_argument(
        "--out-dir",
        default="docs/project/snapshots",
        help="Output directory for timestamped files",
    )
    args = p.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    safe_ts = ts.replace(":", "").replace("-", "")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    metrics = fetch_json(args.url, "/metrics")
    curve = fetch_json(args.url, "/learning-curve")
    summary = build_summary(metrics, curve, ts, args.url)

    json_path = out_dir / f"submission_snapshot_{safe_ts}.json"
    md_path = out_dir / f"submission_snapshot_{safe_ts}.md"
    json_path.write_text(json.dumps({"summary": summary, "metrics": metrics, "learning_curve": curve}, indent=2))
    write_markdown(md_path, summary)

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
