#!/usr/bin/env python3
"""
Run compact, reproducible reward-behavior ablations for evidence docs.

This is not a training run; it compares controlled state variants to show
directional effects of key reward controls.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.data_models import AgentFinding, EpisodeState, ToolOutput
from server.incidents import get_incident
from server.reward import (
    compute_coordination_score,
    compute_customer_score,
    compute_diagnosis_score,
)


def make_state(case_id: str = "INC003", **kwargs) -> EpisodeState:
    inc = get_incident(case_id)
    defaults = dict(
        session_id=str(uuid.uuid4()),
        incident=inc,
        step=8,
        phase="investigation",
        elapsed_minutes=24.0,
        expert_criteria="technical",
        schema_version="v1.0",
        done=False,
    )
    defaults.update(kwargs)
    return EpisodeState(**defaults)


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    safe_ts = ts.replace("-", "").replace(":", "")
    out_dir = Path("docs/project/snapshots")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Ablation 1: evidence gating for diagnosis
    guessed_only = make_state(
        hypotheses_stated=["ML model cache eviction issue causing leak"],
    )
    evidence_backed = make_state(
        hypotheses_stated=["ML model cache eviction issue causing leak"],
        tool_outputs=[
            ToolOutput("datadog", "l2_engineer", "query", {"service": "recommendation-service"}, {"status": "critical"}, 5)
        ],
    )

    # Ablation 2: customer action gating
    no_notification = make_state(phase="mitigation", notifications_sent=0)
    proactive_notification = make_state(phase="mitigation", notifications_sent=1, first_notification_step=4)

    # Ablation 3: coordination anti-noise behavior
    noisy = make_state(
        agent_findings=[
            AgentFinding("l2_engineer", "L2: check acknowledged", 3, "no_op"),
            AgentFinding("sre_agent", "SRE: acknowledged", 4, "no_op"),
            AgentFinding("product_manager", "PM: acknowledged", 5, "no_op"),
        ],
        tool_outputs=[
            ToolOutput("datadog", "l2_engineer", "query", {"metric": "heap"}, {}, 3),
            ToolOutput("datadog", "l2_engineer", "query", {"metric": "heap"}, {}, 4),
        ],
    )
    coordinated = make_state(
        agent_findings=[
            AgentFinding("l2_engineer", "heap growth confirmed on recommendation-service", 3, "query_metrics"),
            AgentFinding("sre_agent", "runbook mitigation staged", 4, "execute_runbook_step"),
            AgentFinding("l1_support", "customers proactively notified", 5, "send_notification"),
        ],
        tool_outputs=[
            ToolOutput("datadog", "l2_engineer", "query", {"metric": "heap", "service": "recommendation-service"}, {}, 3),
        ],
    )

    results = {
        "timestamp_utc": ts,
        "ablations": [
            {
                "name": "diagnosis_evidence_gating",
                "without_evidence": round(compute_diagnosis_score(guessed_only), 4),
                "with_evidence": round(compute_diagnosis_score(evidence_backed), 4),
            },
            {
                "name": "customer_action_gating",
                "without_notification": round(compute_customer_score(no_notification), 4),
                "with_notification": round(compute_customer_score(proactive_notification), 4),
            },
            {
                "name": "coordination_noise_penalty",
                "noisy_pattern": round(compute_coordination_score(noisy), 4),
                "coordinated_pattern": round(compute_coordination_score(coordinated), 4),
            },
        ],
    }

    json_path = out_dir / f"reward_ablation_{safe_ts}.json"
    md_path = out_dir / f"reward_ablation_{safe_ts}.md"
    json_path.write_text(json.dumps(results, indent=2))

    lines = [
        "# Compact Reward Ablation Snapshot",
        "",
        f"Timestamp (UTC): `{ts}`",
        "",
        "| Ablation | Variant A | Variant B | Direction |",
        "|---|---:|---:|---|",
    ]

    d = results["ablations"][0]
    lines.append(
        f"| diagnosis_evidence_gating | {d['without_evidence']:.4f} | {d['with_evidence']:.4f} | evidence-backed > guess-only |"
    )
    c = results["ablations"][1]
    lines.append(
        f"| customer_action_gating | {c['without_notification']:.4f} | {c['with_notification']:.4f} | proactive notify > no notify |"
    )
    k = results["ablations"][2]
    lines.append(
        f"| coordination_noise_penalty | {k['noisy_pattern']:.4f} | {k['coordinated_pattern']:.4f} | coordinated > noisy |"
    )

    md_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
