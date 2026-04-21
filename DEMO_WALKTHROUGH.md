# NEXUS Enhanced — Judge Demo Walkthrough (2 min)

**Goal:** Show judges the live system, training results, and multi-agent coordination in action.

---

## SETUP (Before judges arrive)

```bash
# Terminal 1: Keep this visible
curl -s https://kunalkachru23-nexus-enhanced.hf.space/learning-curve | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Episodes: {len(data[\"rewards\"])}')
print(f'Avg: {data[\"current_avg\"]:.4f}')
print(f'Best: {max(data[\"rewards\"]):.4f}')
print(f'Improvement: +{data[\"improvement\"]*100:.1f}%')
"

# Terminal 2: Ready to show episode data
curl -s https://kunalkachru23-nexus-enhanced.hf.space/learning-curve > /tmp/curve.json
```

---

## [0:00–0:15] CONTEXT SETTING

**Say:**
"Let me show you NEXUS in action. This is a real-time incident response environment running on HuggingFace Spaces. We've trained a Qwen2.5-1.5B model on it using GRPO. Right now, it's solved 99 incidents."

---

## [0:15–0:45] LIVE METRICS

**Show Terminal 1 output:**

```
Episodes: 99
Avg: 0.5060
Best: 0.9484
Improvement: +24.1%
```

**Say:**
"This is live data from our `/learning-curve` API endpoint. The untrained baseline is 0.265. We're now at 0.506 average—that's a 24% improvement in just 99 episodes.

The best episode hit 0.9484. That means on some incidents, the IC got nearly everything right: diagnosed the root cause, notified customers proactively, executed the mitigation flawlessly."

**[Optional] Show the raw JSON:**
```bash
curl -s https://kunalkachru23-nexus-enhanced.hf.space/learning-curve | head -20
```

---

## [0:45–1:15] THE ENVIRONMENT STRUCTURE

**Say:**
"NEXUS simulates 7 incident cases. Let me walk you through how one works: **INC003 — Memory Leak in Production.**

[Open browser to dashboard]

The environment has 6 phases:
1. **Detection** — alert fires (memory spike)
2. **Triage** — is it real or noisy?
3. **Investigation** — which service? root cause?
4. **Mitigation** — fix it (heap profiling, cache eviction)
5. **Resolution** — verify it's fixed
6. **Postmortem** — document what happened

The IC coordinates 5 specialists during this flow. None of them can see everything. The engineer sees logs; the manager sees SLA impact; support sees customer complaints."

---

## [1:15–1:45] MULTI-AGENT COORDINATION IN ACTION

**Say:**
"Here's what makes this different from typical single-agent RL:

The IC **doesn't see raw data**. When it wants to investigate, it asks the L2 Engineer:
- 'Query Datadog for memory metrics on the recommendation-service'
- Engineer responds: 'Memory at 96%, GC pauses 4.2s'

Then the IC asks the SRE:
- 'Is there a heap profile runbook?'
- SRE responds: 'Yes, rb_heap_profile'

The IC's job is to **route information between specialists** and synthesize decisions.

We penalize duplicate queries (coordination score), so the IC learns to be efficient. And we only give rewards at the end—if the IC spams queries or fakes a quick resolution, the final reward is 0."

---

## [1:45–2:00] THE TRAINING SIGNAL

**Say:**
"Our reward model has 6 dimensions:

| Dimension | What It Rewards |
|---|---|
| **MTTR** (30%) | Speed to resolution |
| **Diagnosis** (25%) | Root cause accuracy |
| **Customer** (20%) | Proactive notification |
| **Coordination** (15%) | Multi-agent synergy |
| **Oversight** (5%) | No compliance violations |
| **Depth** (uncapped) | Reasoning quality |

The model learned that querying Datadog + notifying customers + executing the right runbook steps = high reward.

That's observable learning. The model didn't hard-code incident response; it learned the behavior from the reward signal."

---

## [CLOSING — If they ask: "Can we see it train live?"]

**Say:**
"Training runs in Colab using HuggingFace TRL's GRPO algorithm with Unsloth 4-bit QLoRA. It takes ~1-2 hours per 60-episode batch on a T4 GPU.

We can show you the notebook: [open grpo_colab_v2.ipynb]

Here's the reward function—it runs full episodes until completion, then returns the sparse reward. And here's the training loop—GRPO generates new actions, evaluates them in the environment, and updates the model based on the reward signal."

---

## [If they ask: "What about the CrowdStrike scenario?"]

**Say:**
"INC007 is our nightmare-difficulty case. It simulates a CrowdStrike-scale global failure:

- 8.5M machines affected
- Cascading failures across multiple regions
- **Schema drift** — at step 18, the API changes field names and adds new compliance requirements

The IC must adapt on the fly. This isn't easy. It's why we test on escalating difficulty—the model learns to handle complexity."

---

## [If they ask about partial observability]

**Say:**
"This is the key innovation. Normally, RL agents get the full state. Here:

- The engineer sees: `{metrics, logs, database_health}`
- The manager sees: `{sla_status, revenue_impact, customer_count_affected}`
- Support sees: `{notification_status, customer_messages}`

The IC sees only what they report. It's like being on a real incident call—you don't get raw data; you get a conference bridge with experts reporting to you.

This forces genuine multi-agent interaction. The IC can't just brute-force solve it alone."

---

## FALLBACK: If the dashboard is broken

**Say:**
"The web UI has a rendering issue we're debugging, but the backend is solid. Let me show you the API directly:"

```bash
# Show raw JSON
curl -s https://kunalkachru23-nexus-enhanced.hf.space/learning-curve | python3 -m json.tool | head -30
```

"This is the real training data. 99 episodes, each one evaluated by the full 6-dimensional reward model. The data is there; the visualization is just cosmetic."

---

## POST-DEMO Q&A PREP

**Likely questions:**

1. **"Why not just use single-agent RL?"**
   - Answer: "Single agents can't handle distributed expertise. Real incidents need coordination. We're incentivizing the model to work *with* specialists, not replace them."

2. **"How does this compare to existing incident management?"**
   - Answer: "Existing systems are rule-based runbooks or human judgment. We're training a model to *choose* the right runbook and coordinate its execution. It learns from reward, not from hand-coded rules."

3. **"What's the hardest part?"**
   - Answer: "Getting the reward signal right. If you incentivize speed, the model takes shortcuts. We use sparse rewards—zero until the incident is actually resolved—to force substantive solutions."

4. **"Can this scale to real production incidents?"**
   - Answer: "NEXUS is a sandbox. Real deployment would need safety constraints, human-in-the-loop approval, and extensive validation. But the core learning algorithm is sound."

---

## FINAL NOTE

If judges ask to see the notebook, open:
```
notebooks/grpo_colab_v2.ipynb
```

Walk them through:
1. Cell 1: OpenEnv validation
2. Cell 6: Reward function (shows the 6 dimensions)
3. Cell 10: GRPO training (shows 60 prompts × GRPO loop)
4. Cell 11: Results visualization (shows the learning curve)

**Time:** You can do all of this in <2 minutes if you're familiar with the code.
