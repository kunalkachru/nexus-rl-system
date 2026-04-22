# NEXUS Enhanced — Demo manual test cases

Use this checklist during judge demos and release smoke tests.  
**Primary demo incident:** `INC003`. **Optional Q&A:** `INC007`.

**Environments**

| Environment | Base URL | Notes |
|---------------|----------|--------|
| Local | `http://127.0.0.1:7860/` | Must run FastAPI (e.g. uvicorn) from `nexus-enhanced`. |
| HF Stage | `https://kunalkachru23-nexus-enhanced-stage.hf.space/` | Run `openenv push` (or your deploy path) after UI changes so the Space serves the latest `web/dashboard.html`. |

**Cursor browser validation (2026-04-22)**

- **Local:** Manual Validation → `INC003` → **Start Test** → repeated **Guided: fill + execute** until completion. **Result:** Status **Complete**, phase **postmortem**, step **7**, **Episode Complete: Yes**, reward **0.8889**. Guided fields advanced (Situation / RCA / Confidence slider matched scripted steps).
- **HF Stage:** After `openenv push` to `kunalkachru23/nexus-enhanced-stage`, the Manual tab shows **Insert sample text**, **Guided: fill next step**, and **Guided: fill + execute** (same as local). Re-run TC-MAN-04–06 on `https://kunalkachru23-nexus-enhanced-stage.hf.space/` whenever you change `web/dashboard.html`.

---

## TC-TRAIN-01 — Health and dashboard shell

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open `{BASE_URL}/health` | JSON `status` is `healthy` (OpenEnv contract) or legacy `ok` (200). |
| 2 | Open `{BASE_URL}/` | Page title contains “NEXUS Enhanced”; Training Metrics tab visible. |
| 3 | Wait ≤10 s | Metric cards populate (non-error); no blank crash. |

---

## TC-TRAIN-02 — Training metrics refresh

| Step | Action | Expected |
|------|--------|----------|
| 1 | Stay on Training tab ≥5 s | Episode / reward numbers refresh (interval polling). |
| 2 | Open `{BASE_URL}/metrics` in browser or curl | `episode_count` / `total_episodes` keys present; HTTP 200. |

---

## TC-TRAIN-03 — Reward curve

| Step | Action | Expected |
|------|--------|----------|
| 1 | Training tab → scroll to “Reward Curve” | Chart renders (no JS error overlay). |
| 2 | After at least one completed episode (demo or manual) | Curve shows history or updates on refresh. |

---

## TC-TRAIN-04 — Live auto-demo (INC003)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Training tab → **Run Auto-Demo** | Button disables briefly; status area shows progress / completion. |
| 2 | After completion | Final phase and reward summary shown; metrics / episode list refresh. |
| 3 | Optional: `POST {BASE_URL}/demo/run/INC003` | JSON includes `done: true`, `demo_completed: true`, `reward_breakdown.total` (aligned with `test_hf_space_deployment.py`). |

---

## TC-MAN-01 — Manual tab load

| Step | Action | Expected |
|------|--------|----------|
| 1 | Click **Manual Validation** | Incident select, Situation textarea, RCA input, confidence slider, **Start Test**, **Execute Step** visible. |
| 2 | (Latest UI) | **Insert sample text**, **Guided: fill next step**, **Guided: fill + execute** visible; helper line mentions hardcoded guided text. |

---

## TC-MAN-02 — Start session (reset)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Select `INC003` → **Start Test** | Results panel: Status **Running**, phase **detection**, step **0**, Episode Complete **No**. |
| 2 | Network (DevTools) | `POST /reset` returns 200 with `session_id` and `observation`. |

---

## TC-MAN-03 — Insert sample text (latest UI)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Change incident in dropdown (no active session) | Situation + RCA update to incident-specific starter text. |
| 2 | Click **Insert sample text** | Fields refresh for currently selected incident. |

---

## TC-MAN-04 — Guided: fill next step (latest UI)

| Step | Action | Expected |
|------|--------|----------|
| 1 | With an active session, click **Guided: fill next step** once | Situation, RCA, and confidence update to the next scripted line; fields remain editable. |
| 2 | Click again | Values advance to the following scripted line (index increments). |

---

## TC-MAN-05 — Guided: fill + execute to completion (primary)

| Step | Action | Expected |
|------|--------|----------|
| 1 | **Start Test** on `INC003` | Session running (TC-MAN-02). |
| 2 | Repeat **Guided: fill + execute** until complete | Phase advances through workflow; step increases; no permanent UI stall. |
| 3 | Final state | Status **Complete**, Episode Complete **Yes**; optional alert with final reward; guided index resets on next **Start Test**. |
| 4 | Network | Each cycle issues `POST /step/{session_id}` with 200 and coherent `observation`. |

**Recorded local pass:** postmortem, step 7, reward **0.8889** (environment-dependent; assert structure, not exact reward).

---

## TC-MAN-06 — Manual Execute Step (no guided)

| Step | Action | Expected |
|------|--------|----------|
| 1 | **Start Test** | New session. |
| 2 | Type plausible Situation + RCA, set confidence, **Execute Step** | Step increments; phase may change; 200 response. |
| 3 | Repeat until done or max 25 steps | Either **Episode Complete: Yes** or documented stall (file bug with incident + phase + step). |

---

## TC-MAN-07 — Incident switch guard (latest UI)

| Step | Action | Expected |
|------|--------|----------|
| 1 | **Start Test** (session active) | Try changing incident in dropdown. |
| 2 | Expected | Alert warns not to switch; selection reverts to incident under test. |

---

## TC-REG-01 — No JavaScript console errors (demo bar)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open DevTools → Console on `/` | No uncaught errors during Training + Manual flows above. |

---

## Automation reference (CI / gate)

- Local API + web: `pytest tests/test_api.py::TestWebEndpoint` (includes dashboard string checks).
- HF remote: `python test_hf_space_deployment.py --url https://kunalkachru23-nexus-enhanced-stage.hf.space` (extend if you add HF-specific UI assertions).

---

## Demo script (spoken, ~2 min)

1. “Training tab shows live metrics and learning curve from the environment.”  
2. “Run Auto-Demo for INC003 for a scripted commander path.”  
3. “Manual Validation proves the same `/reset` and `/step` APIs with human-written or guided IC input.”  
4. “Guided mode is deterministic hardcoded copy for judges—no LLM required.”
