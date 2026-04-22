# NEXUS Enhanced — project status & backlog

**Source of truth for judging:** [`../../../design/hackathon_brd.md`](../../../design/hackathon_brd.md) (Section 17 hard gates + Section 18 rubric).  
**Last reviewed:** [`../pitch/PITCH.md`](../pitch/PITCH.md), [`PLAN_OF_ACTION.md`](PLAN_OF_ACTION.md), [`../../scripts/export_reward_plot.py`](../../scripts/export_reward_plot.py), BRD compliance matrix.

**See also:** [`../pitch/DEMO_MANUAL_TEST_CASES.md`](../pitch/DEMO_MANUAL_TEST_CASES.md).

---

## Done (recent)

| Area | Item |
|------|------|
| OpenEnv CLI | `openenv validate .` (local package layout) |
| OpenEnv remote | **`openenv validate --url` passes** with `/health` (`status: healthy`, real session/version fields), plus **contract-only** stubs: `/metadata`, `/schema`, `GET /state` (no id), `POST /mcp`. Episode logic still uses `POST /reset`, `POST /step/...`, **`GET /state/{session_id}`** only. |
| HF Space | Stage deploy, `test_hf_space_deployment.py` **8/8**, INC003 auto-demo completes |
| UI | Training metrics, learning curve, INC003 auto-demo, manual validation + sample text + **guided fill / fill+execute** |
| Docs | [`../pitch/DEMO_MANUAL_TEST_CASES.md`](../pitch/DEMO_MANUAL_TEST_CASES.md), [`../guides/QUICK_START.md`](../guides/QUICK_START.md) URLs for stage |
| Gate runner | `gate.sh` (wrapper) / `scripts/shell/gate.sh` — pytest, regression, optional push + HF tests |
| Colab default URL | `notebooks/grpo_colab_v2.ipynb` → `BASE_URL` / dashboard links → **nexus-enhanced-stage** |
| Repo hygiene | `outputs/` present for OpenEnv; README OpenEnv reproduce section |

---

## BRD hard gates (Section 17) — checklist

| # | Requirement | Status |
|---|-------------|--------|
| 1 | OpenEnv **latest release** | **Evidence in repo:** README “BRD hard gate — OpenEnv” commands; `openenv validate .` + `openenv validate --url` green after stubs; Colab still `pip install openenv>=0.2.3`. Record `openenv --version` in your pitch appendix. |
| 2 | Minimal **Colab** training script (**Unsloth** or **HF TRL**) | **Notebook aligned:** `grpo_colab_v2.ipynb` now defaults `BASE_URL` to **stage** (`kunalkachru23-nexus-enhanced-stage.hf.space`). You still need one successful T4+ run before submission. |
| 3 | **Blog (HF)** or **Video (YouTube, &lt;2 min)** | **You own:** publish + link in submission. |

---

## Judging rubric (Section 18) — quick gap scan

| Criterion | Weight | Focus next |
|-----------|--------|------------|
| Environment innovation | 40% | One sharp “why NEXUS is hard” story (partial observability, schema drift, coalitions) backed by INC007 / live UI. |
| Storytelling | 30% | 3-minute pitch script rehearsed; demo path: metrics → auto-demo → guided manual complete. |
| Observable reward improvement | 20% | Keep dashboard + `/learning-curve` honest; optional: export static plot artifact for slides. |
| Reward / pipeline coherence | 10% | Tie reward dimensions to BRD wording; show before/after behaviour if you have checkpoints. |

---

## Technical backlog (recommended order)

1. ~~**Submission hygiene:** OpenEnv reproduce block in README + `outputs/` for clean `openenv validate .`~~ (done this iteration).  
2. **Colab:** Run `grpo_colab_v2.ipynb` once on T4+; capture reward curve screenshot for slides.  
3. **Judge artifacts (BRD gate):** Publish HF **blog** or **YouTube &lt;2 min** and add the link next to README “Blog Post” section.  
4. **Pitch (30% storytelling):** 3-minute path: Training tab metrics → **Run Auto-Demo** → Manual **Guided: fill + execute** to complete (see [`../pitch/DEMO_MANUAL_TEST_CASES.md`](../pitch/DEMO_MANUAL_TEST_CASES.md)).  
5. **Optional hardening:** Richer `/schema` from Pydantic models (cosmetic).

---

## Out of scope / non-goals

- Replacing the FastAPI sim with a full MCP runtime (stubs satisfy validate only).  
- Git-based HF deploy (per your workflow: `openenv push` only).
