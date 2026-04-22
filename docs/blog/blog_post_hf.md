---
title: "NEXUS Enhanced: Training AI to Respond to CrowdStrike-Scale Incidents"
thumbnail: /blog/assets/nexus-enhanced/thumbnail.png
authors:
  - user: kunalkachru23
---

# NEXUS Enhanced: Training AI to Respond to CrowdStrike-Scale Incidents

*Team Falcons — Meta PyTorch OpenEnv Hackathon Grand Finale, April 2026*

**Live Demo:** [huggingface.co/spaces/kunalkachru23/nexus-enhanced](https://huggingface.co/spaces/kunalkachru23/nexus-enhanced)  
**Training Notebook:** [grpo_colab.ipynb](https://huggingface.co/spaces/kunalkachru23/nexus-enhanced/blob/main/notebooks/grpo_colab.ipynb)

---

## The Problem: A $5.4 Billion Outage Nobody Wants to Repeat

On July 19, 2024, a single faulty CrowdStrike update crashed 8.5 million Windows machines worldwide in 78 minutes. Airlines, hospitals, and banks went dark. The total economic loss exceeded $5.4 billion. At peak, the outage was burning through an estimated $48,000 per minute across affected enterprises.

The tragedy wasn't just technical — it was *coordination failure*. Multiple teams had different pieces of the picture, no one had authority to synthesize them fast enough, and the escalation protocols were too slow for the pace of the crisis.

We built **NEXUS Enhanced** to train AI to do better.

---

## What We Built

NEXUS Enhanced is a multi-agent reinforcement learning environment where an **Incident Commander (IC)** AI learns to orchestrate five specialist agents to detect, triage, investigate, mitigate, and resolve production incidents — from a simple payment service timeout all the way to a CrowdStrike-scale global failure.

The IC is trained using **GRPO (Group Relative Policy Optimization)** via HuggingFace TRL on Qwen2.5-1.5B. The specialist agents are deterministic simulators — this keeps the training signal clean and tractable for a 1.5B model in 48 hours.

### The 6-Agent Team

| Agent | Tool | Role |
|---|---|---|
| **Incident Commander** | All (coordinator) | Orchestrates all agents — the trained policy |
| L2 Engineer | SimDatadog | Analyzes metrics and logs |
| SRE Agent | SimRunbook | Executes infrastructure runbooks |
| Product Manager | SimJira | Tracks SLA and revenue impact |
| L1 Support | SimSlack + Portal | Customer communication |
| Oversight Agent | Monitor | Compliance, explainability, protocol |

Each agent operates with **partial observability** — the L2 Engineer sees Datadog logs but not SLA metrics; the Product Manager sees revenue impact but not runbook steps. The IC must synthesize partial views into a coherent incident response.

The IC also starts with **minimal information** (Halluminate sub-theme): at step 0, it only sees "3 alerts firing" — not which services or what metrics. Scope is discovered by dispatching agents to investigate.

---

## The Reward Model: 6 Dimensions, Zero Shortcuts

A naive reward like "did the incident resolve?" creates shortcuts. We designed a **6-dimensional sparse reward** that requires genuine evidence of incident mastery:

```python
episode_reward = (
    0.30 * mttr_score           # faster resolution = higher score
  + 0.25 * diagnosis_score      # root cause accuracy + tool evidence (gated)
  + 0.20 * customer_score       # proactive notification required
  + 0.15 * coordination_score   # unique tool queries, no duplicates
  + 0.05 * oversight_score      # protocol compliance
  + depth_bonus                 # UNCAPPED — scales with reasoning word count
)
```

**Anti-shortcuts built in:**
- Diagnosis requires a tool output implicating the root-cause service — guessing scores 0.1 max
- Customer score requires dispatching `send_notification` — awareness alone scores nothing
- Coordination penalises duplicate `(agent, tool, params)` calls — redundancy is punished
- Depth bonus ignores assessments under 30 words — boilerplate strings earn zero

**Mercor sub-theme:** The depth bonus is uncapped and scales with word count past 80 words plus structural keywords (root cause, coalition, blast radius, etc.). A 200-word structured analysis earns ~0.3–0.5 on this dimension alone.

---

## The 7 Incident Cases

| Case | Difficulty | Key Challenge | Revenue Burn |
|---|---|---|---|
| INC001 | Easy | Payment service, Stripe API version mismatch | $8,400/min |
| INC002 | Easy | DB pool exhaustion, cascade to 3 services | $12,000/min |
| **INC003** | **Medium** | **Red herrings + ML model memory leak** | **$15,600/min** |
| INC004 | Hard | Vendor retry storm, root cause masked | $22,000/min |
| INC005 | Hard | JWT key rotation, conflicting signals | $18,500/min |
| INC006 | Very Hard | Multi-region CDN misrouting | $36,000/min |
| INC007 | Nightmare | CrowdStrike-scale + live schema drift | $48,000/min |

**INC003 (primary demo):** Three alerts fire simultaneously. The recommendation-service has 96% memory (real root cause: ML model v4 feature vector cache with no LRU eviction). The search-service has 8% errors (red herring — within threshold). The ad-service has 78% CPU (red herring — load-correlated). A trained IC learns to ignore the red herrings, form a coalition vote on the correct hypothesis, and execute the runbook — all within 28 steps.

---

## Training Results (Pre-Event Baseline)

Before on-site GPU training, 30 scripted baseline episodes established the floor:

- **Baseline avg reward: 0.265** (range 0.195–0.336)
- Baseline behaviour: 8-word canned assessments, no coalition, late/no notification
- **Improvement headroom to trained target (0.65): +0.306**

Expected trained model performance after 200 GRPO steps: **0.55–0.75**

The gap shows clear, observable training signal — satisfying BRD Criterion 3 (observable reward improvement evidence).

---

## Coalition Mechanic (Halluminate)

For medium+ incidents, the IC must cast a coalition vote naming a hypothesis. Specialist agents evaluate it against ground-truth keywords. A correct vote unlocks:
- +0.15 to diagnosis score
- +0.2 to coordination score

This incentivises the IC to build genuine consensus, communicate clearly, and commit to a hypothesis with evidence — not just guess.

---

## Schema Drift (Patronus AI)

INC007 includes a live schema change at step 18:
- **RunBook**: `step_id` → `runbook_ref`, `expected_outcome` → `expected_output + success_criteria`
- **CustomerPortal**: notification API now requires `gdpr_compliant=true`

An IC trained only on earlier incidents will encounter API errors on INC007 and must adapt mid-episode.

---

## Expert Review Board (Snorkel AI)

The reward weights adapt based on recent IC performance:

| Criteria | When activated | Effect |
|---|---|---|
| Speed | Default / mttr weak | Boosts MTTR weight 1.5× |
| Communication | Customer score weak (<0.4) | Boosts customer weight 1.8× |
| Technical | Diagnosis weak (<0.4) | Boosts diagnosis weight 1.6× |
| Cost | Coordination weak (<0.4) | Boosts coordination + oversight |

The expert board notices IC weaknesses and shifts its evaluation focus — simulating real subject-matter experts with changing requirements.

---

## Try It

```bash
# Live demo — no install needed
curl -X POST https://kunalkachru23-nexus-enhanced.hf.space/demo/run/INC003 | python -m json.tool

# Or open the web dashboard
https://huggingface.co/spaces/kunalkachru23/nexus-enhanced
```

**Training notebook** (GRPO on Qwen2.5-1.5B, cells 1–3 run without GPU):  
`notebooks/grpo_colab.ipynb` in the Space repo.

---

*Built by Team Falcons (Kunal Kachru) for the Meta PyTorch OpenEnv Hackathon Grand Finale.*  
*OpenEnv v0.2.3 | HuggingFace TRL GRPO | Qwen2.5-1.5B | 185 tests passing*
