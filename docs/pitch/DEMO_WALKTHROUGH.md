# NEXUS Enhanced — Judge Demo Walkthrough (2 min)

Goal: show live environment quality, observable training gains, and behavior change in under 2 minutes.

---

## Setup (before judges arrive)

```bash
curl -s https://kunalkachru23-nexus-enhanced-stage.hf.space/learning-curve | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Episodes: {len(d[\"rewards\"])}')
print(f'Avg: {d[\"current_avg\"]:.4f}')
print(f'Best: {max(d[\"rewards\"]) if d[\"rewards\"] else 0:.4f}')
print(f'Improvement: +{d[\"improvement\"]*100:.1f}%')
"
```

Canonical frozen reference (for narration consistency):
- `docs/project/snapshots/submission_snapshot_20260424T164826Z.md`

---

## [0:00-0:20] Context

Say:
"NEXUS is a multi-agent, partially observable incident-command environment on HF Space. The IC coordinates 5 specialist roles across escalating incidents, including schema drift and personalized delegation tasks."

---

## [0:20-0:45] Observable training improvement

Show dashboard training tab (`/web`) headline metrics and curve.

Say:
"Against baseline 0.265, our latest frozen snapshot is avg 0.4634, best 1.0032, +74.9% improvement with 387 completed episodes."

---

## [0:45-1:20] Behavioral evidence

Switch to **Validation** tab:
1. Click **Run auto-demo (INC003)**.
2. Let transcript complete.
3. Highlight:
   - phase progression to completion,
   - sparse step rewards,
   - final episode total reward,
   - better sequencing and fewer redundant actions.

Say:
"This is the key point: behavior changes, not just the chart."

---

## [1:20-1:50] Manual controllability

Still in Validation tab:
1. Select `INC008`.
2. Click **Start Test**.
3. Run one **Guided: fill + execute** step.

Say:
"INC008 demonstrates personalized conflict/delegation behavior on the same environment mechanics."

---

## [1:50-2:00] Close

Say:
"We satisfy OpenEnv validation requirements, show live reward improvement, and can directly inspect behavior delta in the running environment."

---

## Fast fallback branches

### If UI is slow

```bash
curl -s https://kunalkachru23-nexus-enhanced-stage.hf.space/metrics
curl -s https://kunalkachru23-nexus-enhanced-stage.hf.space/learning-curve
curl -s -X POST https://kunalkachru23-nexus-enhanced-stage.hf.space/demo/run/INC003
```

### If metrics shift during demo

Use frozen docs for spoken numbers:
- `docs/project/snapshots/submission_snapshot_20260424T164826Z.md`
- `docs/project/snapshots/component_metrics_20260424T164826Z.md`

---

## Q&A anchors (short)

1. Why multi-agent?  
   Real incidents require distributed expertise and belief/incentive modeling under partial observability.

2. Why sparse reward?  
   Prevents shortcut gaming; completion quality is scored at episode end.

3. What proves learning?  
   Reward curve trend + baseline comparison + transcript-level behavioral delta.

4. Can judges rerun?  
   Yes: HF Space URL, OpenEnv validation, and Colab notebook path are all documented.
