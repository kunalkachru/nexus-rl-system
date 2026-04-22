# YouTube Recording Script (Owner-Recorded)

Target length: 1:45 to 2:00 (meets "<2 minute video" guidance).  
Style: clear, confident, outcome-first.

## Shot plan and narration

## 0:00-0:12 — Hook (camera or title slide)

Say:

"Most incident-response AI demos are single-agent and unrealistic. NEXUS Enhanced is a multi-agent OpenEnv environment where an Incident Commander coordinates specialists under partial observability, business constraints, and schema drift."

Visual:
- Title card: NEXUS Enhanced + stage URL + team name.

## 0:12-0:35 — What you built

Say:

"We built seven incident scenarios, from easier outages to a nightmare schema-drift incident. The system runs through OpenEnv-compatible endpoints and is deployed on Hugging Face Spaces. The training path uses TRL GRPO with Unsloth in Colab."

Visual:
- Brief pan over architecture section in `README.md`.
- Show `/health` and `/metadata` in browser or terminal.

## 0:35-1:05 — Measurable improvement

Say:

"This is live evidence from the deployed environment. In the current snapshot, we have 120 completed episodes, average reward 0.4063 versus baseline 0.265, and best episode reward 0.9484. That's a 53.3% uplift over baseline."

Visual:
- Open `/metrics` or dashboard metrics panel.
- Show `docs/images/training_reward_curve.png`.

## 1:05-1:35 — Behavioral improvement (not only scalar)

Say:

"Our key claim is behavioral improvement. In INC003, the trained policy commits earlier to the memory-leak hypothesis, executes runbook steps in a better order, sends proactive customer notifications, and reaches postmortem with fewer redundant actions."

Visual:
- Trigger `POST /demo/run/INC003` or show the transcript output.
- Highlight phase progression and reward breakdown.

## 1:35-1:55 — Safeguards and close

Say:

"To reduce reward hacking, diagnosis is evidence-gated, customer score requires actual notification actions, coordination penalizes duplicate tool calls, and oversight violations reduce final score. NEXUS combines innovation, measurable improvement, and reproducible deployment for real incident-management RL."

Visual:
- Briefly show `docs/project/REWARD_HACKING_DEFENSE.md` and evidence index.

## 1:55-2:00 — End card

Say:

"Thanks for watching. Links to the live Space, repository, and evidence pack are in the submission."

Visual:
- End card with:
  - GitHub repo URL
  - Stage URL
  - Evidence index path

## Recording checklist

- Use one canonical metrics set from latest frozen snapshot.
- Current frozen reference: `docs/project/snapshots/submission_snapshot_20260422T172511Z.md`.
- Record at 1080p; zoom text enough for judge readability.
- Keep terminal font large and avoid rapid window switching.
- If live UI lags, use frozen snapshots and continue smoothly.
