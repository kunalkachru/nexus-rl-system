#!/usr/bin/env python3
"""
Copy Colab backup artifacts into web/training_runs/ for the metrics dashboard.

Reads NEXUS_GRPO_backups/run_*/learning_curve.json and run_manifest.json,
writes web/training_runs/runs/<id>/export.json plus optional PNGs, and
updates web/training_runs/index.json.

Run from repo root:
  python scripts/sync_training_runs_web.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKUPS = ROOT / "NEXUS_GRPO_backups"
OUT = ROOT / "web" / "training_runs"
RUNS_DIR = OUT / "runs"

PLOT_NAMES = ("training_analysis.png", "reward_curves_hires.png")


def main() -> None:
    if not BACKUPS.is_dir():
        print(f"Skip: no {BACKUPS}")
        return

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []

    for run_dir in sorted(BACKUPS.iterdir()):
        if not run_dir.is_dir() or not run_dir.name.startswith("run_"):
            continue
        lc = run_dir / "learning_curve.json"
        if not lc.is_file():
            continue
        data = json.loads(lc.read_text())
        rewards = data.get("rewards") or []
        manifest = {}
        mf = run_dir / "run_manifest.json"
        if mf.is_file():
            manifest = json.loads(mf.read_text())

        rid = run_dir.name
        dest = RUNS_DIR / rid
        dest.mkdir(parents=True, exist_ok=True)

        export = {
            "schema_version": 1,
            "run_id": rid,
            "source": "colab_backup",
            "manifest": manifest,
            "episodes": {"reward": [float(x) for x in rewards]},
            "baseline": float(data.get("baseline", 0.265)),
        }
        (dest / "export.json").write_text(json.dumps(export, indent=2) + "\n", encoding="utf-8")

        plots: dict[str, str] = {}
        for name in PLOT_NAMES:
            src = run_dir / name
            if src.is_file():
                shutil.copy2(src, dest / name)
                plots[name.replace(".png", "")] = f"runs/{rid}/{name}"

        label = "Quick" if "quick" in rid else "Full"
        entries.append(
            {
                "id": rid,
                "label": f"{label} — {rid.replace('run_', '')}",
                "export": f"runs/{rid}/export.json",
                "plots": plots,
            }
        )

    entries.sort(key=lambda e: e["id"], reverse=True)
    index = {"schema_version": 1, "runs": entries}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} run(s) under {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
