# NEXUS Enhanced: Multi-Agent RL for Enterprise Incident Response

**By Kunal Kachru & Sandhya Tripathi | Team Falcons**

*An OpenEnv-based multi-agent environment for training AI incident commanders to resolve production crises at scale.*

---

## The Problem: CrowdStrike-Scale Incidents

On January 19, 2025, a CrowdStrike software update caused a global IT outage affecting **8.5 million machines**. Recovery required coordinated action across multiple specialized teams: engineers debugging logs, SREs executing runbooks, product managers tracking impact, customer support communicating outages, and incident commanders orchestrating all of it.

Most RL environments train single agents on toy problems. **Real enterprise incidents demand multi-agent coordination under partial information.**

**NEXUS Enhanced** tackles this: train an AI Incident Commander to coordinate 5 specialist agents, routing information between them, and resolving production incidents of escalating severity—culminating in a CrowdStrike-scale scenario.

---

## The Environment

NEXUS Enhanced is an OpenEnv v0.2.3 environment simulating 7 incident cases across a 6-phase state machine:

```
Detection → Triage → Investigation → Mitigation → Resolution → Postmortem
```

### 6 Agent Roles

| Agent | Primary Tool | Observation Scope |
|---|---|---|
| **Incident Commander** (Trained) | All 5 tools | Strategic view (trained via GRPO) |
| L2 Engineer | SimDatadog | Metrics & logs only |
| SRE Agent | SimRunbook | Infrastructure procedures |
| Product Manager | SimJira | Revenue/SLA impact |
| L1 Support | SimSlack | Customer communication |
| Oversight Agent | All tools | Compliance monitoring |

### 5 Enterprise Tool Simulators

Each simulator is deterministic and rule-based—no external APIs:

- **SimDatadog** — Metric queries (rate-limited: 3 unique per episode)
- **SimRunbook** — Procedure execution with prerequisite chains
- **SimSlack** — Customer notifications & escalations
- **SimJira** — Ticket management with VP approval gates
- **SimCustomerPortal** — User communication (schema drift in INC007)

### Partial Observability

The Incident Commander doesn't see raw logs or metrics—it receives **role-scoped observations** from each specialist. This mirrors real incident response: you don't call the on-call engineer directly; you work through their reporting.

---

## The Reward Model: Multi-Dimensional Sparse Rewards

Rewards fire **only at episode completion** (done=True), not per-step, preventing agents from gaming short-term rewards.

### 6 Dimensions (Total = 1.0)

| Dimension | Weight | What It Measures |
|---|---|---|
| **MTTR** | 30% | Speed to resolution vs optimal baseline |
| **Diagnosis** | 25% | Root cause accuracy (tool evidence + keywords) |
| **Customer** | 20% | Proactive notifications (early bonus: +0.2) |
| **Coordination** | 15% | Multi-agent synergy (penalizes duplicate queries) |
| **Oversight** | 5% | Compliance violations checked |
| **Depth Bonus** | Uncapped | Reasoning quality in postmortem assessment |

### Why Sparse?

Sparse rewards prevent degenerate behaviors like:
- Querying the same metric 100 times
- Spamming notifications without investigation
- Skipping diagnosis to fake quick "resolution"

Only substantive, reasoned incident response yields high rewards.

---

## Training: GRPO in Colab

Using **HuggingFace TRL's GRPO** (Generative Reward Policy Optimization) with **Unsloth 4-bit QLoRA** fine-tuning on Qwen2.5-1.5B:

```python
# Training setup in notebooks/grpo_colab_v2.ipynb
- Model: Qwen2.5-1.5B-Instruct (4-bit LoRA)
- Algorithm: GRPO (100 generation steps per batch)
- Dataset: 60 incident prompts (10 variants × 6 repeats)
- Compute: Colab T4 GPU (~1-2 hours per full run)
- Validation: Real-time reward tracking via HF Spaces API
```

### The Reward Function

```python
def reward_fn(completions):
    """Run full episodes until completion, return rewards."""
    rewards = []
    for completion_text in completions:
        session_id, obs = env.reset("INC003")
        done = False
        step_count = 0
        
        while not done and step_count < 28:
            action = parse_ic_action(completion_text)
            obs, reward, done, info = env.step(session_id, action)
            step_count += 1
        
        rewards.append(reward)  # Only fires when done=True
    return rewards
```

---

## Live Results: 99 Episodes Trained

Training on **INC003 (Memory Leak)** — a medium-difficulty incident with red herrings and coalition debates:

| Metric | Value |
|---|---|
| **Episodes Completed** | 99 |
| **Average Reward** | 0.5060 |
| **Best Episode** | 0.9484 |
| **Baseline (Untrained)** | 0.265 |
| **Improvement** | **+24.1%** |

### What This Means

- The model went from random action (~0.265) to consistently above 0.50
- Best episodes show the IC successfully:
  - Querying root cause service (Datadog)
  - Notifying affected customers
  - Executing correct runbook steps in order
  - Completing full diagnosis + mitigation in <28 steps

### Learning Curve (Last 10 Episodes)

Recent episodes average **0.52**, showing the training hasn't plateaued—improvement continues with more episodes.

---

## Deployment: HF Spaces + FastAPI

**Live Demo:** https://kunalkachru23-nexus-enhanced.hf.space/

Architecture:

```
Colab (Training)
    ↓ GRPO fine-tuning Qwen2.5-1.5B
    ↓
HF Spaces (Inference + Evaluation)
    ├─ FastAPI Server (port 7860)
    │  ├─ POST /reset → start episode
    │  ├─ POST /step/{session_id} → take action
    │  ├─ GET /learning-curve → reward history
    │  └─ GET /metrics → training progress
    │
    └─ Web Dashboard (live metrics)
       ├─ Episode count
       ├─ Average/best rewards
       ├─ Reward curve (updates every 5s)
       └─ Agent findings log
```

---

## Innovation Highlights

### 1. **Partial Observability**
Unlike most RL environments (which give agents omniscient state), NEXUS agents only see information relevant to their role. This mirrors real enterprise workflows where no single person has complete visibility.

### 2. **Coalition Voting**
In INC003, multiple hypotheses compete (code bug vs config issue). The IC must build consensus among specialists via coalition_vote before committing to a runbook. This incentivizes multi-agent reasoning over solo decision-making.

### 3. **Schema Drift (INC007)**
The CrowdStrike-scale scenario (INC007) introduces breaking API changes at step 18—the SimRunbook and SimCustomerPortal swap field names and add new requirements. This tests the agent's ability to handle production-grade system changes mid-crisis.

### 4. **Mercor Depth Bonus (Uncapped)**
The postmortem assessment has an uncapped bonus based on reasoning depth (word count + structure keywords). This encourages detailed, thoughtful explanations—not just quick action.

### 5. **Snorkel AI Rotating Experts**
Expert criteria rotate by episode modulo 4:
- Episode 0 mod 4: Technical expert (boost Diagnosis weight)
- Episode 1 mod 4: Customer expert (boost Customer weight)
- Episode 2 mod 4: Operations expert (boost Coordination weight)
- Episode 3 mod 4: Compliance expert (boost Oversight weight)

This prevents overfitting to a single evaluation lens.

---

## Why This Matters

**For Academia:** Multi-agent RL with partial observability remains unsolved. NEXUS provides a benchmarkable environment with real-world complexity (7 incident types, schema drift, coalition mechanics).

**For Enterprise:** Incident response is currently a purely human skill. AI can't yet reliably orchestrate the coordination needed. NEXUS demonstrates that with the right environment and training signal, language models can learn to coordinate specialized agents.

**For Meta & PyTorch:** This work validates OpenEnv as a framework for enterprise-grade agent training. The sparse reward design, multi-agent coordination, and real-world scenario grounding show the paradigm's potential.

---

## Get Started

**Try NEXUS Enhanced:**

1. **Clone & validate:**
   ```bash
   openenv validate --env nexus-enhanced
   ```

2. **Run tests:**
   ```bash
   pytest tests/ -q
   ```

3. **Train locally:**
   ```bash
   # Run the Colab notebook in Colab, or locally with:
   jupyter notebook notebooks/grpo_colab_v2.ipynb
   ```

4. **Deploy to HF Spaces:**
   ```bash
   openenv push --repo-id your-username/nexus-enhanced
   ```

5. **Monitor live:**
   Visit the dashboard → see reward curves update in real-time.

---

## Team

**Kunal Kachru** — Environment design, multi-agent orchestration, reward modeling  
**Sandhya Tripathi** — Agent implementations, testing, deployment

---

## References

- OpenEnv v0.2.3: https://github.com/huggingface/open-env
- HuggingFace TRL: https://github.com/huggingface/trl
- Unsloth: https://github.com/unslothai/unsloth
- Live Demo: https://kunalkachru23-nexus-enhanced.hf.space/

---

**The hackathon challenge: Can an AI incident commander coordinate multiple specialists to resolve a crisis at scale? NEXUS Enhanced shows it's possible.**
