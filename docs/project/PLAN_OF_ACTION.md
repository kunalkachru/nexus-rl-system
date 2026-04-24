# Plan of action + BRD compliance matrix

**Authority:** [`../../../design/hackathon_brd.md`](../../../design/hackathon_brd.md) (Section 17 hard gates, Section 18 rubric, §18.1 pitch format).

---

## BRD compliance — strict review (evidence-based)

| Ref | Requirement | Repo / runtime evidence | Status |
|-----|----------------|-------------------------|--------|
| **§17.1** | OpenEnv **(latest release)** — not fork, not old | `openenv validate .` OK; `openenv validate --url` OK after contract routes; `openenv push` workflow; Colab `pip install openenv>=0.2.3`; README “BRD hard gate — OpenEnv” | **Pass** — document `openenv --version` on submission day |
| **§17.2** | Minimal training in **Colab** with **Unsloth** or **HF TRL** | `notebooks/grpo_colab_v2.ipynb` installs TRL + Unsloth + trains GRPO | **Pass pending** — you must execute notebook once on GPU before final submit |
| **§17.3** | **HF blog** *or* **YouTube video &lt; 2 min** | `docs/blog/blog_post.md` draft exists; **publish** + URL in README/submission | **Gap** — publishing is owner action |
| **§18.1** | **3 min** pitch + **2 min** Q&A | `docs/pitch/PITCH.md` script + Q&A table timed to format | **Pass** (content) — rehearsal is owner action |
| **§18.2 C1** | Environment innovation **40%** | Multi-agent, partial observability, 7 incidents, INC007 schema drift, coalition | **Strong** — rehearse one INC007 sentence |
| **§18.2 C2** | Storytelling **30%** | Dashboard + demo flow in `docs/pitch/DEMO_MANUAL_TEST_CASES.md` + `docs/pitch/PITCH.md` | **Pass** — practice run |
| **§18.2 C3** | Observable reward improvement **20%** | `/learning-curve`, dashboard, `scripts/export_reward_plot.py` | **Pass** — keep Space populated for live curve |
| **§18.2 C4** | Reward + pipeline coherence **10%** | Sparse reward, dimensions in README; trained **behaviour** narrative | **Medium** — tie checkpoint to different IC actions, not only reward |

**Non-BRD but operational:** `pytest tests/` green; `test_hf_space_deployment.py` 8/8 on stage URL; `./gate.sh` or `scripts/shell/gate.sh` optional full run before deploy.

---

## Todo table — plan of action (priority order)

| # | Task | Owner | Done when |
|---|------|-------|-----------|
| 1 | Run **`./gate.sh`** (or pytest + `openenv validate --url` on stage) before each demo | Team | All green |
| 2 | **`openenv push`** stage Space after meaningful code/doc change | Team | HF dashboard matches local |
| 3 | Execute **`grpo_colab_v2.ipynb`** on Colab T4+ end-to-end | Team | Notebook completes; curve updates on stage |
| 4 | **`python scripts/export_reward_plot.py --url https://kunalkachru23-nexus-enhanced-stage.hf.space`** → drop PNG into deck | Team | `docs/images/training_reward_curve.png` in slide asset folder |
| 5 | Rehearse **`docs/pitch/PITCH.md`** with live demo (timer **3:00**) | Team | No overrun; Q&A 2:00 bank ready |
| 6 | **Publish** HF blog *or* record **≤2 min** YouTube; add URL to README | Team | BRD §17.3 satisfied |
| 7 | Submission package: Space URL, Colab link, blog/video link, `openenv --version` screenshot | Team | Checklist complete |
| 8 | (Optional) INC007 **60 s** clip for innovation Q&A | Team | Recorded path in repo or drive link |

---

## Backlog

| Item | Notes |
|------|--------|
| **HF post-push readiness** | `openenv validate --url` used to fail right after `openenv push` while the Space was still on the old Docker image. **Mitigation (done):** `scripts/shell/gate.sh` polls `GET /health` (until `status=healthy`) and `GET /metadata` (200), with `NEXUS_POST_PUSH_WAIT_MAX` (default 360s) and `NEXUS_POST_PUSH_WAIT_INTERVAL` (default 15s), before remote validate + HF tests. **Follow-up:** tune defaults per typical build time; optionally integrate HF build-status API when stable. |

---

## Quick commands (copy-paste)

```bash
cd nexus-enhanced
pytest tests/ -q
openenv validate .
openenv validate --url https://kunalkachru23-nexus-enhanced-stage.hf.space
python scripts/export_reward_plot.py --url https://kunalkachru23-nexus-enhanced-stage.hf.space --out docs/images/training_reward_curve.png
```
