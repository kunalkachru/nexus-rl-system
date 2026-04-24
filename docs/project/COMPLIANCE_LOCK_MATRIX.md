# Compliance Lock Matrix (hackathon-aligned)

Purpose: freeze **mandatory requirements** and **judging rubric** traceability so implementation changes stay aligned with hackathon compliance.

## Mandatory requirements (pass/fail)

| Gate | Requirement | Project evidence | Verification command |
|---|---|---|---|
| OpenEnv latest workflow | Use OpenEnv validation/deployment workflow | `openenv.yaml`, `server/app.py`, deployment scripts | `openenv validate .` and `openenv validate --url https://kunalkachru23-nexus-enhanced-stage.hf.space` |
| Colab training script | Minimal Colab script with TRL/Unsloth path | `notebooks/grpo_colab_v2.ipynb` | Notebook config + run cells |
| Public artifact | HF blog or <2 min video | `docs/blog/*`, `docs/pitch/YOUTUBE_RECORDING_SCRIPT.md` | Submission URL checklist |

## Weighted scoring criteria map (judging rubric)

These four rows are what Cerebral Valley–aggregated scoring uses. The **Demonstration** column is how a judge should *see* each criterion in the live Space or repo in under five minutes.

| Criterion | Weight | What judges need (intent) | NEXUS evidence | How the design demonstrates it (demo / artefact) |
|---|---:|---|---|---|
| **1 — Environment Innovation** | 40% | Novel, creative, or challenging; meaningfully tests agent behaviour | `server/environment.py`, `server/incidents.py`, `server/agents.py`, `server/tools.py`, `docs/project/SUBTHEME_EVIDENCE_MATRIX.md` | Open the dashboard **Training** tab → **manual validation** on **INC008** (Theme 3.2) and INC004–INC007; show **coalition**, **role-scoped tooling**, **INC007 schema drift** in Q&A or deep demo. Eight incidents = difficulty ladder + operational nuance + personalized track. |
| **2 — Storytelling** | 30% | Clear explanation of problem, environment, and agent behaviour; demo **engaging and easy to follow** | `docs/pitch/PITCH.md`, `docs/pitch/DEMO_WALKTHROUGH.md`, `docs/project/FINAL_OPERATIONS_RUNBOOK.md` | Follow `DEMO_WALKTHROUGH.md`: metrics -> **Validation tab auto-demo** (INC003) -> optional **Guided** steps to completion. One sentence hook: “IC coordinates specialists under partial observability and contract drift.” |
| **3 — Improvement in Rewards** | 20% | **Observable** training progress: reward curves, metrics, or before/after behaviour | `/metrics`, `/learning-curve`, `docs/project/snapshots/*`, `docs/project/BEHAVIORAL_DELTA_PROOF.md`, `scripts/export_reward_plot.py` | Live **rolling average vs baseline** on the chart; frozen numbers in `docs/project/snapshots/`; Colab-exported curves in **Advanced Metrics** when shipped. Tie narrative to **behaviour** delta doc, not only scalars. |
| **4 — Reward + Training Pipeline** | 10% | Reward logic **coherent**; pipeline improves **inference / how the agent acts** | `server/reward.py`, `notebooks/grpo_colab_v2.ipynb`, `docs/project/REWARD_HACKING_DEFENSE.md` | Explain sparse terminal reward + dimensions + optional depth bonus; show Colab hits **real** `/reset`→`/step` Space API; cite `BEHAVIORAL_DELTA_PROOF.md` for “acts differently after training.” |

---

## Hackathon content themes — how NEXUS maps

Official hackathon **themes** (organizer brief) are distinct from the **four scoring criteria** above. NEXUS is architected as an **enterprise incident-command** environment; the table below states where each parent theme is **primary** (core loop), **secondary** (explicit mechanic but not the headline), or **bridge** (honest pitch link without claiming a different product genre).

| Parent theme | Track | Primary requirement (summary) | NEXUS demonstration | Verification |
|---|---|---|---|---|
| **Theme 1 — Multi-agent** | Multi-agent track | Cooperation / competition / negotiation / **coalition**; **partial observability**; theory-of-mind style incentives | Five specialist roles + IC; coalition votes on harder incidents; IC observation is a slice, not full state | `server/environment.py`, `server/agents.py`, INC003+ in `server/incidents.py`, manual validation + `/state/{session_id}` |
| **Theme 2 — Long horizon & instruction following** | Long-horizon track | **Sparse / delayed** reward; task **beyond one context**; decomposition & recovery; Scale sub-theme: **non-code** business workflows (incl. **HR & IT**) | Episode-level reward on `done`; long `max_steps` incidents; **server-side** session state and tool history so the task cannot fit in one static transcript; **IT ops** coordination (not a coding benchmark) | `server/reward.py`, `server/app.py` session store, INC006–INC007 length/complexity; see Scale AI row in `SUBTHEME_EVIDENCE_MATRIX.md` |
| **Theme 3.1 — World modeling (professional)** | World modeling | Realistic tools/workflows; **anti-shortcut**; causal / persistent world | Datadog / runbook / portal-style tools; evidence-gated diagnosis; runbook steps; red herrings on harder tracks | `server/tools.py`, `server/reward.py`, `docs/project/REWARD_HACKING_DEFENSE.md` |
| **Theme 3.2 — World modeling (personalized)** | Personalized track | Personal delegation / conflicts / messaging-style tasks | **Dedicated incident INC008** (EA calendar: board prep vs school concert, family thread, auto-accept root cause) using `IncidentType.PERSONAL_ASSISTANT`, same multi-agent tool loop as ops incidents. **Plus** enterprise paths: customer **notifications** and SLA framing on INC001–INC007. | Manual validation **INC008** on dashboard; `server/incidents.py` (`INC008`), `server/data_models.py` |
| **Theme 4 — Self-improvement** | Self-improvement track | Curriculum / adaptive difficulty; recursive capability growth | **Process-wide adaptive tier:** `server/global_curriculum.py` + `GET /curriculum` — last-5 rolling avg ≥ 0.55 promotes difficulty across **HTTP/Colab sessions** (not lost per `NexusEnvironment()`). **Plus** seven-incident ladder + **Snorkel-style** rotating `expert_criteria`. Full recursive self-play is out of scope; GRPO improves policy externally. | `server/difficulty.py`, `server/global_curriculum.py`, `server/app.py` `/curriculum`, Colab GRPO |
| **Theme 5 — Wild card** | Wild card | Creative value for LLM training on a defined task | **Primary positioning option:** “Out-of-box” fusion of **multi-agent ops + schema drift + oversight + token-scaled depth bonus** in one OpenEnv-deployable stack | Pitch close in `docs/pitch/PITCH.md`; innovation narrative in rubric row 1 |

### Sub-theme bonuses — already locked in `SUBTHEME_EVIDENCE_MATRIX.md`

Fleet, Halluminate, Snorkel, Patronus, Mercor, Scaler AI Labs rows remain the detailed sponsor map. This matrix ties **parent themes** to the same implementation so evaluators see both **theme** and **sponsor** coverage.

### One-line pitch bank (theme → sentence)

Use in Q&A if asked “which themes?”

1. **Theme 1:** “IC coordinates five roles under partial observability and coalition mechanics.”
2. **Theme 2:** “Sparse end-of-episode reward and persistent server state force long-horizon planning beyond a single context.”
3. **Theme 3.1:** “Tool-bound enterprise workflows with anti-shortcut evidence and runbook discipline.”
4. **Theme 3.2:** “**INC008** is a personalized EA-style conflict (calendar + family messaging) on the same engine; other incidents stress customer delegation under SLA.”
5. **Theme 4:** “**`/curriculum`** shows live adaptive difficulty from rolling rewards; expert criteria rotate; GRPO improves the policy.”
6. **Theme 5:** “Wild-card angle: one deployable environment that fuses the hardest ops themes for LLM incident command training.”

---

## Non-regression compliance checklist

Before sign-off, all must be true:

1. `pytest tests/ -q` passes.
2. `openenv validate .` passes.
3. `openenv validate --url https://kunalkachru23-nexus-enhanced-stage.hf.space` passes.
4. `python test_hf_space_deployment.py --url https://kunalkachru23-nexus-enhanced-stage.hf.space` passes (11 checks: core API + **`GET /curriculum`**, **`GET /incidents`** includes INC008, **`POST /reset`** INC008 smoke).
5. `python test_regression_local.py` passes (includes INC008 reset + global curriculum status shape).
6. Pitch/demo/video script metrics match latest frozen snapshot in `docs/project/snapshots/`.
