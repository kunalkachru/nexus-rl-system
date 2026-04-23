# Sub-Theme Evidence Matrix (Judge-Ready)

This matrix maps implemented mechanics to BRD wording and where judges can verify each claim.

**Parent BRD themes (§9–14)** and the **four §18 scoring criteria** are mapped end-to-end in `docs/project/COMPLIANCE_LOCK_MATRIX.md` (theme demonstration + demo beats). This file focuses on **§15 sponsor sub-themes** and cross-links to the same implementation paths.

## Targeted sub-themes

| Sponsor / Sub-theme | BRD wording to satisfy | Implemented evidence | Where to verify |
|---|---|---|---|
| **Theme 3.2 — Personalized (BRD §12)** | Personal tasks, delegation, conflicting priorities | **INC008** — executive EA calendar conflict (family vs board), smart-scheduler auto-accept root cause; `IncidentType.PERSONAL_ASSISTANT` | Dashboard manual validation select **INC008**; `server/incidents.py` |
| Fleet AI — Scalable Oversight | "monitor, analyze, and explain" | Oversight-oriented behavior + oversight reward component in final score model | `server/reward.py`, `server/agents.py`, live run transcript from `/demo/run/INC003` |
| Halluminate — Multi-Actor Environments | "interacts with and manages multiple actors ... to discover and achieve task" | IC orchestrates L1/L2/SRE/PM actions with partial observability; coalition mechanics present | `server/environment.py`, `server/agents.py`, `server/incidents.py` (INC003+), dashboard manual flow |
| Snorkel AI — Simulated Experts | "changing requirements/preferences" | Rotating expert criteria and adaptive scoring emphasis over episodes | `server/reward.py`, project docs (`README.md`, `docs/project/PLAN_OF_ACTION.md`) |
| Patronus AI — Schema Drift | "data schemas, API contracts, policies/rules change" | INC007 schema drift and contract adaptation behavior path | `server/incidents.py`, `server/tools.py`, `openenv.yaml` references |
| Mercor — Token-scaled reasoning reward | "rewards scale with token output" | Depth/reasoning bonus in reward logic | `server/reward.py` reward breakdown and docs reward model section |
| Scale AI — Non-code business (HR & IT) | Long-horizon **non-code** workflows in Sales / PM / **HR & IT** only | **IT / on-call incident command** (status pages, escalations, runbooks, customer comms)—no code-writing task as the core object | Multi-step dashboard validation, SLA/revenue semantics in `server/incidents.py`, L1 customer paths |
| Scaler AI Labs — Multi-App Enterprise RL | "business rule nuances" in enterprise multi-app world | Datadog/Jira/Runbook/Customer interactions with operational constraints and role-specific visibility | `server/tools.py`, `server/incidents.py`, dashboard and auto-demo flow |

## Cross-criterion reinforcement

- Criterion 1 (Innovation 40%): multi-agent + partial observability + schema drift + business-rule constraints.
- Criterion 2 (Storytelling 30%): deterministic live flow in `docs/pitch/PITCH.md` and `docs/pitch/DEMO_WALKTHROUGH.md`.
- Criterion 3 (Improvement 20%): `/learning-curve`, `/metrics`, `docs/images/training_reward_curve.png`.
- Criterion 4 (Pipeline 10%): Colab GRPO script + behavior delta sheet (`docs/project/BEHAVIORAL_DELTA_PROOF.md`).
