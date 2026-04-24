# NEXUS Enhanced — 3-Minute Hackathon Pitch

**Target: 450 words, ~3 min at conversational pace**

---

## [OPENING — 15 seconds]

"January 19, 2025. A CrowdStrike software update broke 8.5 million machines globally. Recovery wasn't one person's job—it took engineers debugging logs, SREs executing procedures, product managers tracking impact, and support communicating with customers. All coordinated by an incident commander.

**NEXUS Enhanced is an OpenEnv environment that trains an AI incident commander to orchestrate this coordination and resolve production crises at scale.**

We're not training single agents on toy problems. We're training agents to handle real enterprise complexity."

---

## [1. PROBLEM STATEMENT — 30 seconds]

"The problem: Multi-agent incident response under **partial observability**. No agent sees everything. An engineer sees logs; a manager sees revenue impact; support sees angry customers. The commander's job: route information between them, synthesize decisions, and resolve the crisis.

This mirrors real enterprise workflows. And it's hard—most RL envs give agents omniscient state. We don't."

---

## [2. ENVIRONMENT — 40 seconds]

"NEXUS simulates 7 incident cases across a 6-phase state machine: Detection → Triage → Investigation → Mitigation → Resolution → Postmortem. We have 5 deterministic tool simulators—Datadog, Runbooks, Slack, Jira, CustomerPortal. No external APIs; everything is reproducible.

The environment scales from easy (single service timeout) to nightmare (CrowdStrike-scale global failure with schema drift mid-crisis).

**Partial observability is the key mechanic:** the IC receives role-scoped observations from specialists, not raw data. This forces meaningful multi-agent interaction."

---

## [3. AGENT CAPABILITIES — 25 seconds]

"Six agents, five are scripted specialists:
- L2 Engineer queries metrics
- SRE executes runbooks
- Product Manager tracks SLAs
- L1 Support notifies customers
- Oversight Agent monitors compliance

The Incident Commander—**this is the trained agent**—can call any tool, request information from any specialist, and make routing decisions. It sees no raw data; it synthesizes specialist reports into action."

---

## [4. TASKS — 20 seconds]

"Seven incident cases of escalating difficulty:
- INC001: Service timeout (easy, 3 steps optimal)
- INC003: Memory leak with red herrings (medium, 6 steps)
- INC007: CrowdStrike-scale failure (nightmare, includes schema drift)

Each case has a ground-truth root cause and an expert-guided optimal path. The IC must discover the cause, verify it, and execute the mitigation."

---

## [5. REWARD MODEL — 35 seconds]

"**Six sparse-reward dimensions:**
- MTTR (30%) — speed to resolution vs optimal
- Diagnosis (25%) — tool evidence + correct keywords
- Customer (20%) — proactive notifications (early bonus)
- Coordination (15%) — multi-agent synergy, penalizes duplicates
- Oversight (5%) — compliance violations
- Depth bonus (uncapped) — reasoning quality in postmortem

**Why sparse?** Rewards fire only at episode completion. This prevents gaming: agents can't spam queries or fake quick resolutions. Only thoughtful, substantive incident response yields high rewards."

---

## [6. SELF-IMPROVEMENT STRATEGY — 25 seconds]

"We use **GRPO (Generative Reward Policy Optimization)** from HuggingFace TRL with **Unsloth 4-bit QLoRA fine-tuning** on Qwen2.5-1.5B.

Training runs in Colab on 60 incident prompts. We've completed 99 episodes, achieving **+24.1% improvement over untrained baseline** (0.265 → 0.506 avg reward).

The trained model learns to query the right service, notify customers proactively, and coordinate specialists—exactly the behaviors our reward function incentivizes."

---

## [CLOSING — 20 seconds]

"NEXUS validates a critical insight: **with the right environment and training signal, language models can learn to orchestrate multi-agent coordination under partial information.**

For academia, it's a benchmarkable environment. For enterprise, it's a path toward AI-assisted incident management. For Meta and PyTorch, it demonstrates OpenEnv's potential for real-world complexity.

**Live demo:** https://kunalkachru23-nexus-enhanced-stage.hf.space/ 

Thank you."

---

## DEMO FLOW (for Q&A or live walkthrough)

1. **Show dashboard**: "Here's 99 episodes of live training. Average reward: 0.506. Baseline was 0.265. That's 24% improvement."
2. **Hit the API**: `curl /learning-curve` → show raw reward data
3. **Walk through one episode**: "Here's INC003 being solved: IC queries Datadog → finds the memory leak → notifies customers → executes the runbook."
4. **Highlight the multi-agent part**: "Notice: the IC never sees raw logs. It only sees what the L2 Engineer reports. That's partial observability in action."

---

## KEY SOUNDBITES (if judges interrupt)

- **On innovation**: "Partial observability + coalition voting + schema drift. Most RL envs are single-agent or fully observable. We're neither."
- **On storytelling**: "CrowdStrike is $5.4B in damages. That's real. This environment trains for real incidents."
- **On improvement**: "99 episodes, +24.1% over baseline. Best episode: 0.9484/1.0. That's genuine learning, not luck."
- **On pipeline**: "OpenEnv v0.2.3, HF TRL GRPO, Unsloth, Qwen2.5-1.5B. All production-grade tools."

---

## PRACTICE TIPS

- **Pace**: Conversational, not rushed. ~150 words/min = slower than you think.
- **Emphasis**: Pause after "CrowdStrike" and "partial observability"—these are your differentiators.
- **Eye contact**: Rotate between judges; don't read.
- **Tone**: Confident but humble. You're solving a hard problem; you know it's novel.
- **Time check**: Have a watch visible. At 2:00, pivot to closing.
