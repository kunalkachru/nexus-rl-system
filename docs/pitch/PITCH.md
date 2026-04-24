# NEXUS Enhanced — 3-minute pitch + 2-minute Q&A

**Event:** Meta PyTorch OpenEnv Hackathon × Scaler — Grand Finale  
**Format (per hackathon compliance):** 3 min pitch + 2 min Q&A = 5 min total.

---

## Opening hook (~20 s)

> “Production incidents are not single-agent chat tasks. They are **partially observable**, **multi-agent**, and **tool-bound** — exactly the gap OpenEnv is meant to stress-test. NEXUS Enhanced is a CrowdStrike-scale **enterprise incident command** simulator where a trained **Incident Commander** orchestrates five specialists with conflicting views, sparse end-of-episode rewards, and live **schema drift** on the nightmare track.”

---

## Problem & why it matters (~25 s)

- Enterprises lose minutes to hours when humans must merge Slack, Datadog, Jira, runbooks, and customer comms under pressure.
- RL for operations fails when environments are toy MDPs: no coordination cost, no contract drift, no red herrings.
- **NEXUS** encodes that complexity: L1/L2/SRE/PM + oversight, each with **role-scoped** observations so the IC must **synthesize**, not memorize a single transcript.

---

## What we built (~50 s)

1. **Seven incidents** from easy payment timeouts to **INC007 nightmare** with **schema / API drift** mid-episode (Patronus-aligned sub-theme).
2. **FastAPI + OpenEnv workflow:** `openenv validate` / `openenv push` to HF Space; **`openenv validate --url`** green on contract checks; core loop remains **`/reset` → `/step/{session_id}` → `/state/{session_id}`**.
3. **Sparse reward** at episode end with dimensions aligned to operational quality (MTTR, diagnosis, customer, coordination, oversight + depth).
4. **Judge dashboard:** live **metrics**, **learning curve**, and a **Validation tab** that supports both scripted INC003 auto-demo and manual/guided validation.
5. **Colab path:** GRPO + **HF TRL + Unsloth** against the deployed Space (`notebooks/grpo_colab_v2.ipynb`).

---

## Observable evidence (~35 s) — reward improvement (judging rubric)

- Show **dashboard** reward curve and rolling average vs **baseline** (pre-event benchmark).
- Use one canonical metrics callout (snapshot `2026-04-24T16:48:26Z`, stage URL): **episodes 387**, **avg 0.4634**, **best 1.0032**, **+74.9% vs baseline 0.265**.
- In **Validation** tab: one click **Run auto-demo (INC003)** -> completed episode + reward breakdown.
- Optional: “We export the same curve for slides via `python scripts/export_reward_plot.py --url …`.”

---

## Training & improvement (~30 s) — improvement + pipeline coherence

- **Colab** runs minimal GRPO training against the **real** remote environment API (not a mocked reward).
- Improvement is **observable** on the curve and in **behaviour** (shorter paths, better notifications, fewer oversight violations) — tie any checkpoint story to **what the IC does differently**, not only the scalar.

---

## Close (~20 s)

> “NEXUS is **OpenEnv-shaped**: isolated episodes, structured actions, measurable outcomes, and a problem that stays hard after the novelty wears off. We meet **hackathon compliance**: OpenEnv latest in the toolchain, Colab TRL/Unsloth training, and the required HF blog or short video slot—and we optimised for the **40% environment** and **30% storytelling** rubric weights with a demo you can **drive live** in under two minutes.”

**Stop at 3:00. Breathe. Hand off for Q&A.**

---

## Q&A — prepared bullets (~2 min bank)

Answer in **short paragraphs**; do not invent numbers not on the dashboard.

| Likely question | Bullet answer |
|-----------------|---------------|
| **Why OpenEnv?** | Packaging, `openenv validate` / `push`, HF Space deploy, and alignment with “structured environments + measurable outcomes” from the organiser email. |
| **Latest OpenEnv version?** | Colab installs `openenv>=0.2.3`; local/README document `openenv validate .` and `--url`. HF Docker omits OpenEnv **only** to keep Space builds reliable — tradeoff stated in README. |
| **Is `/metadata` / `/schema` / `/mcp` real?** | **Contract stubs** for CLI HTTP checks only. **No** change to episode physics; real state is still **`/state/{session_id}`**. |
| **Reward hacking?** | Sparse terminal reward + oversight + coalition + tool budgets; red herrings in harder incidents. |
| **What is partial observability?** | IC observation is a slice; specialists see tool outputs for their role; IC never sees everything at once. |
| **INC007 in 30 s?** | Nightmare incident: multi-region blast radius; **schema drift** forces contract change mid-episode — reserved for sharp Q&A, not the full live path if time is short. |
| **Why GRPO / TRL / Unsloth?** | Per compliance: minimal training in Colab with **HF TRL** and **Unsloth** for efficient QLoRA on Qwen-class IC policy. |
| **What if the Space is slow?** | Training is async from Colab; dashboard refreshes on timer; auto-demo is one POST chain. |
| **Baseline 0.265?** | Pre-event scripted benchmark documented in server; curve compares **trained vs that baseline** for “observable improvement.” |
| **Single strongest differentiator?** | Multi-agent + sparse reward + **schema drift** on INC007 in one OpenEnv-hosted stack judges can open in the browser. |

---

## Demo order (recommended)

1. Training tab -> metrics + curve (5–10 s).  
2. Validation tab -> **Run auto-demo (INC003)** (20–30 s).  
3. Validation tab -> **Start Test** -> **Guided: fill + execute** until **Complete** (45–60 s).  
4. If asked for artefacts: show `docs/images/training_reward_curve.png` (repo) or refresh via export script / Colab plots.

Use stage URL consistently in demo:

- `https://kunalkachru23-nexus-enhanced-stage.hf.space/`
