# Training Multi-Agent Incident Response at CrowdStrike Scale via GRPO

**How to build an AI incident commander that coordinates 6 specialized agents to resolve production emergencies in minutes, not hours.**

## The Problem: When Everything Breaks

On July 19, 2024, CrowdStrike's faulty kernel update affected 8.5 million Windows machines globally. The outage cascaded: airlines grounded flights, hospitals diverted patients, financial markets went dark. Global impact: $5.4 billion in losses.

What went wrong? Not technical architecture—that's hard to break. What failed was **human coordination under chaos**. A single engineer had to:
- Parse fragmented alerts (Datadog, Slack, PagerDuty)
- Hypothesize the root cause (cache? kernel? config?)
- Coordinate fix across L1 support, L2 engineering, SRE, and product
- Explain decisions in real-time to stakeholders
- Race against a ticking SLA clock

By the time they figured out the pattern, millions were offline.

**What if an AI incident commander could handle that coordination?**

## The Solution: NEXUS Enhanced

NEXUS Enhanced is an OpenEnv-compatible multi-agent reinforcement learning environment that trains an AI **Incident Commander** to orchestrate 6 specialized agents responding to production incidents of escalating severity—from single-service timeouts to CrowdStrike-scale global failures.

### The 6-Agent Architecture

The environment simulates a real SOC war room:

| Role | Specialty | Observability |
|------|-----------|---|
| **Incident Commander** (trained) | Decision-making | Full context |
| **L2 Engineer** | Log analysis | Service metrics only |
| **SRE Agent** | Infrastructure fixes | System state |
| **Product Manager** | Business impact | Revenue, SLA only |
| **L1 Support** | Customer comms | Tickets, sentiment |
| **Oversight Agent** | Compliance | Policy violations |

Each agent operates under **partial observability**: the L2 Engineer can't see SLA metrics; the PM doesn't see kernel logs. The IC must synthesize fragmented signals into a coherent narrative and action plan.

## The Training Problem

Naïve supervised learning fails here. Why? Because there's no "ground truth" for good incident response. Speed matters, but not at the cost of cascading damage. Coordination matters, but not if it delays critical actions.

We use **Generative Reward Policy Optimization (GRPO)** — a lightweight alternative to PPO that's ideal for language models. The reward function incentivizes:

- **MTTR (30%)**: Resolve in 15 minutes, not 2 hours
- **Root Cause Accuracy (25%)**: Diagnose the actual problem, not a red herring
- **Customer Impact (20%)**: Proactively notify affected users
- **Coordination Quality (15%)**: Leverage agent insights; avoid duplicate queries
- **Compliance (5%)**: Respect change freezes, SLAs, GDPR
- **Reasoning Depth (uncapped)**: Deeper postmortems unlock higher rewards

The kicker: **Rewards only fire at episode end**, forcing the IC to reason holistically rather than chasing step-by-step incentives.

## 7 Incident Scenarios (Escalating Difficulty)

1. **INC001** (easy): Service timeout → straightforward query + restart
2. **INC002** (easy): Database pool exhaustion → cascade pattern
3. **INC003** (medium): ML cache memory leak with red herrings
4. **INC004** (hard): External vendor failure with masked retries
5. **INC005** (hard): JWT key mismatch with conflicting signals
6. **INC006** (very hard): Multi-region CDN misrouting
7. **INC007** (nightmare): CrowdStrike-scale global failure with schema drift

Each case is fully randomized. Root causes vary, agent responses are stochastic, tool outputs change between episodes.

## The Training Pipeline

### Deploy to HF Spaces (30 min)
```bash
export HF_TOKEN='hf_xxxxx'
python deploy_to_hf_spaces.py
# Monitor: https://huggingface.co/spaces/kunalkachru23/nexus-enhanced
```

### Train in Colab (6 hours for 50 episodes)
```python
# Open notebooks/grpo_colab_v2.ipynb in Colab GPU
# Cell 1: Validate OpenEnv==0.2.3 ✓ 
# Cell 2: Install ML stack (unsloth, trl, transformers)
# Cell 5: Load Qwen2.5-1.5B with 4-bit QLoRA
# Cell 11: Train 50+ episodes via GRPO
# Monitor: https://kunalkachru23-nexus-enhanced.hf.space/learning-curve
```

### Expected Results
- **Episodes 1-5**: Baseline reward ~0.28 (random IC)
- **Episodes 10-30**: Improvement to 0.4–0.6 (learns Datadog queries, notifications)
- **Episodes 30+**: Convergence to 0.6–0.8 (chains reasoning properly)
- **MTTR**: Drops from 28 steps → 8 steps

The IC learns emergent behaviors:
- Proactively notify customers before investigating
- Chain Datadog queries intelligently (not brute-force)
- Leverage SRE runbooks only with evidence
- Escalate to PM only when SLA threatened

## Why This Matters

Targets 6 of 7 sponsor sub-themes:

- **Scaler AI Labs** (host): Large-scale RL pipeline
- **Fleet AI**: Oversight agent monitors IC for bias + compliance
- **Halluminate**: 6-agent coordination under partial observability
- **Scale AI**: Real IT incident domain (not toys)
- **Mercor**: Uncapped reasoning depth reward
- **Snorkel AI**: Rotating expert review per episode

More fundamentally: **If AI can coordinate humans coordinating infrastructure, we're close to fully autonomous incident response.** And that saves lives when billions depend on digital systems.

## Live Demo & Code

**Dashboard**: https://kunalkachru23-nexus-enhanced.hf.space/

Watch live training, trigger manual simulations, inspect agent observations, review compliance violations.

**Code**: All incident cases, tool simulators, reward logic are deterministic and reproducible. Zero external API calls—everything in-process.

## Next Steps

1. Deploy to HF Spaces (ready to run)
2. Open Colab, run grpo_colab_v2.ipynb with GPU
3. Watch reward curves at /learning-curve
4. Download artifacts and results

---

**Kunal Kachru** • Team Falcons • Meta PyTorch OpenEnv Hackathon Grand Finale (April 25–26, 2026)
