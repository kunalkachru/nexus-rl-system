# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

NEXUS Enhanced — OpenEnv v0.2.3 compatible multi-agent enterprise incident response RL environment for the Meta PyTorch OpenEnv Hackathon Grand Finale (April 25–26, 2026).

## Commands

```bash
# Install
pip install -r requirements.txt

# Test (all)
pytest tests/ -q

# Test (single)
pytest tests/test_env.py::TestCoalition -v

# Start server
uvicorn server.app:app --reload --port 7860

# Auto-demo (no server needed)
python -c "from server.app import run_demo; import json; print(json.dumps(run_demo('INC003'), indent=2))"

# Reward inline tests
python -m server.reward

# Smoke test (from project root)
python -c "
from server.environment import NexusEnvironment
env = NexusEnvironment()
obs = env.reset(incident_id='INC003')
print('Alert:', obs['incident_title'])
obs2, r, done, info = env.step({'situation_assessment': 'investigating', 'resolution_confidence': 0.1})
print('Step 1 done:', done)
print('Reward:', env.compute_reward())
"
```

## Module Build Order

Never import a module before its dependencies exist:

```
Level 0: data_models.py, incidents.py
Level 1: tools.py
Level 2: agents.py, reward.py, difficulty.py
Level 3: environment.py
Level 4: app.py (FastAPI)
Level 5: client.py, inference.py, train.py, grpo_train.py (Day 3)
Level 6: tests/, notebooks/, web/
Level 7: openenv.yaml, Dockerfile, README.md
```

## Architecture

**`server/data_models.py`** — All dataclasses. Every other module imports from here. Key types: `EpisodeState`, `IncidentCase`, `IncidentCommanderAction`, `RewardBreakdown`.

**`server/incidents.py`** — 7 incident cases (INC001–INC007). `INCIDENT_LIBRARY` dict. Ground truth fields (`root_cause`, `is_red_herring`) are hidden from agents — only used by reward and OversightAgent.

**`server/tools.py`** — 5 simulators: `SimDatadog` (rate-limited, 3 unique queries/episode), `SimSlack`, `SimJira` (VP approval, change freeze), `SimRunbook` (prerequisite chain, v1.0/v2.0 schema), `SimCustomerPortal` (GDPR in v2.0). `ToolRegistry` enforces role-based access via `ROLE_TOOL_SCOPES`.

**`server/agents.py`** — 5 scripted specialists (`L1SupportAgent`, `L2EngineerAgent`, `SREAgent`, `ProductManagerAgent`, `OversightAgent`). Specialists are deterministic during training. `build_agent_observation()` implements partial observability per role.

**`server/reward.py`** — 6 reward dimensions. Expert criteria in `EXPERT_WEIGHT_MULTIPLIERS` rotate by `episode % 4` (Snorkel AI). Mercor depth bonus is UNCAPPED. `compute_total_reward()` returns `RewardBreakdown`.

**`server/difficulty.py`** — `DifficultyAdapter`: promote at avg > 0.55, generate variant at avg > 0.65.

**`server/environment.py`** — `NexusEnvironment`: OpenEnv-compatible `reset()`/`step()` interface. 6-phase state machine (detection→postmortem). Handles: coalition voting, schema drift (INC007 step 18+), phase progression, oversight monitoring, difficulty advancement.

**`server/app.py`** — FastAPI server. `_sessions` dict is the server-side external state store (required by Theme 2 — hard/nightmare episodes exceed model context). Key endpoints: `POST /reset`, `POST /step/{session_id}`, `POST /demo/run/{incident_id}`.

## Key Design Decisions

- **IC is the only trained agent** (GRPO). Specialists are scripted. This isolates the coordination learning signal and is tractable for 1.5B–7B models in 48h.
- **Sparse reward** — only on episode resolution, not per-step. Anti-shortcut.
- **Coalition needs keywords not exact match** — `correct_hypothesis_keywords` list checked against coalition vote substring.
- **Schema drift is Patronus AI mechanic** — `SimRunbook` renames `step_id→runbook_ref`, `expected_outcome→expected_output+success_criteria`. `SimCustomerPortal` adds `gdpr_compliant=true` requirement. Both triggered by `ToolRegistry.apply_schema_drift("v2.0")`.
- **Datadog rate limit** — 3 unique `(service, metric)` combinations per episode. Tests duplicate-query detection for OversightAgent.
- **Mercor bonus UNCAPPED** — capping would discourage responses longer than cap threshold.

## Incident Difficulty Map

| ID | Difficulty | Key Mechanic | Demo Use |
|----|------------|--------------|----------|
| INC001 | easy | Single service, clear logs | None |
| INC002 | easy | DB pool, cascade | None |
| INC003 | medium | Red herrings, ML leak | **Primary demo** |
| INC004 | hard | External vendor, masked retry | None |
| INC005 | hard | JWT key mismatch, conflicting signals | None |
| INC006 | very_hard | Multi-region CDN misrouting | None |
| INC007 | nightmare | CrowdStrike-scale + schema drift | **Q&A demo** |

## Reward Weights

| Dimension | Weight | Anti-Shortcut |
|-----------|--------|---------------|
| MTTR | 30% | Linear interpolation between optimal/baseline |
| Diagnosis | 25% | Requires tool evidence + correct keywords |
| Customer | 20% | Requires proactive `send_notification` action |
| Coordination | 15% | Penalises duplicate tool queries |
| Oversight | 5% | Violations: -0.2 each; warnings: -0.05 |
| Depth bonus | uncapped | Word count + structure keywords |

## Sub-Theme Targets (6/7)

Scaler AI Labs (host), Fleet AI (OversightAgent), Halluminate (multi-actor), Scale AI (IT domain), Mercor (uncapped depth), Snorkel AI (rotating expert board). Patronus AI (schema drift in INC007).
