# NEXUS Enhanced: Training AI to Respond to CrowdStrike-Scale Incidents

*Team Falcons — Meta PyTorch OpenEnv Hackathon Grand Finale, April 2026*

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

---

## The Reward Model: 6 Dimensions, Zero Shortcuts

A naive reward like "did the incident resolve?" creates shortcuts — the IC learns to declare resolution without doing any real work. We designed a **6-dimensional sparse reward** that requires genuine evidence of incident mastery:

```python
episode_reward = (
    0.30 * mttr_score           # faster resolution = higher score
  + 0.25 * diagnosis_score      # root cause accuracy + tool evidence
  + 0.20 * customer_score       # proactive notification (not just awareness)
  + 0.15 * coordination_score   # unique tool queries, agent findings shared
  + 0.05 * oversight_score      # protocol compliance
  + depth_bonus                 # UNCAPPED — scales with reasoning quality
)
```

### Anti-Shortcuts Built In

- **Diagnosis requires evidence**: the IC can't score on root cause by guessing. A tool output implicating the correct service is required. Hypothesis without evidence scores 0.1 max.
- **Customer score requires action**: identifying user impact doesn't score. The IC must dispatch L1 to `send_notification` via `SimCustomerPortal`.
- **Coordination penalises redundancy**: duplicate `(agent, tool, action, params)` tuples subtract 0.1 each. Good ICs delegate efficiently.
- **Depth bonus guards against boilerplate**: assessments under 30 words earn zero. A 10-word canned string like "Investigating root cause, gathering evidence" earns nothing — even if it contains the right keywords.

### Mercor Reasoning Depth Bonus

The depth bonus is **uncapped** — it scales with word count and structural richness of the IC's situation assessments. A 200-word structured analysis mentioning root cause, coalition vote, blast radius, and mitigation timeline can earn 0.5+ on this dimension alone. This directly rewards the kind of transparent, legible reasoning that makes AI safe to deploy in high-stakes operations.

---

## The 7 Incident Cases

We built 7 incident cases with escalating severity, each designed to test a different failure mode:

| Case | Difficulty | Key Challenge | Revenue Impact |
|---|---|---|---|
| INC001 | Easy | Single service, clear logs | $8,400/min |
| INC002 | Easy | DB pool exhaustion, cascade | $12,000/min |
| **INC003** | **Medium** | **Red herrings, ML memory leak** | **$15,600/min** |
| INC004 | Hard | External vendor, masked retry storm | $22,000/min |
| INC005 | Hard | JWT key mismatch, conflicting signals | $18,500/min |
| INC006 | Very Hard | Multi-region CDN misrouting | $36,000/min |
| INC007 | Nightmare | CrowdStrike-scale + schema drift | $48,000/min |

INC003 is our primary demo case. Three alerts fire simultaneously: the recommendation-service has 96% memory usage (real root cause: ML model v4 feature vector cache with no LRU eviction), the search-service has 8% error rate (red herring — within threshold), and the ad-service has 78% CPU (red herring — load-correlated). A trained IC learns to ignore the red herrings, form a coalition vote on the correct hypothesis, and execute the runbook.

---

## Training Results

Before on-site GPU training, we ran 30 episodes with a **scripted baseline policy** to establish a floor:

- Baseline average reward: **0.265** (range: 0.195–0.336)
- Baseline policy behaviour: canned 8-word assessments, no coalition, late notification

The baseline was deliberately calibrated to score below 0.5, leaving clear headroom for GRPO improvement. We expect trained model rewards in the **0.55–0.75** range after 200 GRPO steps on HuggingFace compute.

Here's what the pre-training reward distribution looks like:

```
Episode Rewards (Scripted Baseline, 30 episodes):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
0.195  ████████████████████ 15 episodes (easy difficulty)
0.336  ████████████████████ 15 episodes (medium difficulty)
                           avg: 0.265
```

---

## The Coalition Mechanic

For medium and hard incidents, NEXUS implements a **coalition voting system**. The IC must call a coalition vote with a hypothesis string. All specialist agents evaluate it against the true root cause keywords. A correct coalition vote unlocks a +0.15 diagnosis bonus and +0.2 coordination bonus.

This mechanic incentivises the IC to:
1. Form a clear, specific hypothesis (not vague guesses)
2. Build consensus before acting — which reduces expensive rollback runbook executions
3. Communicate transparently so other agents can validate the reasoning

---

## Schema Drift (Patronus AI)

INC007 includes a live schema change at step 18: the runbook tool renames `step_id → runbook_ref` and `expected_outcome → expected_output + success_criteria`. A trained IC that learned to parse `step_id` will fail on this incident without adaptation.

This tests **out-of-distribution robustness** — one of the hardest problems in deploying AI to production infrastructure environments.

---

## The Expert Review Board (Snorkel AI)

The reward function's weights rotate every 4 episodes via an **Expert Review Board** mechanic:

| Criteria | MTTR weight | Diagnosis weight | Customer weight |
|---|---|---|---|
| Speed | **1.5×** | 0.8× | 1.0× |
| Communication | 0.8× | 0.8× | **1.8×** |
| Technical | 0.8× | **1.6×** | 0.8× |
| Cost | 1.0× | 1.0× | 1.0× |

This forces the IC to learn a balanced policy that performs well across all dimensions — not just optimising for the metric that happened to dominate training.

---

## Try It Yourself

The environment is fully self-contained — no external API calls, fully deterministic simulators.

```bash
pip install openenv==0.2.3 trl unsloth fastapi pytest

# Start the server
uvicorn server.app:app --reload --port 7860

# Open the web dashboard
open http://localhost:7860/web

# Or run the auto-demo directly
curl -X POST http://localhost:7860/demo/run/INC003 | python -m json.tool
```

The Colab training notebook (`notebooks/grpo_colab.ipynb`) is runnable end-to-end on HuggingFace's free GPU tier — cells 1–3 run without GPU for local inspection.

---

## What's Next

The trained IC checkpoint will be pushed to HuggingFace Hub after on-site training completes (April 25–26, 2026). Watch this space for the before/after MTTR curve showing GRPO improvement over the scripted baseline.

If you're building training environments for AI in high-stakes operational domains — incident response, network operations, financial risk management — we'd love to hear from you. The multi-agent partial observability pattern generalises well beyond enterprise IT.

---

*Built by Team Falcons for the Meta PyTorch OpenEnv Hackathon Grand Finale.*
*Environment code, reward model, training notebook, and demo: [github.com/team-falcons/nexus-enhanced](https://github.com)*
