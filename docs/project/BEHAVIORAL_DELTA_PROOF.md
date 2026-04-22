# Criterion 4 Behavioral Delta Proof

This sheet demonstrates BRD §18.2 Criterion 4 language: improvement in "how it acts in the environment", not only scalar rewards.

## Scenario used

- Incident: `INC003` (memory leak with red herrings)
- Environment URL: `https://kunalkachru23-nexus-enhanced-stage.hf.space`
- Evidence channels:
  - `POST /demo/run/INC003` transcript
  - `GET /metrics` aggregate outcomes
  - Dashboard manual run flow (`/web`)

## Before (baseline-style behavior pattern)

Observed low-quality behavior in pre-training patterns:
- Short, generic situation summaries with weak root-cause commitment.
- Late or missing proactive customer communication.
- More repeated or low-information tool-routing decisions.
- Higher chance of stalling in investigation/triage without decisive mitigation.

Operational effect:
- Lower average reward near baseline (`0.265` reference in project docs).
- Lower coordination and diagnosis quality components.

## After (trained behavior pattern)

Observed trained behavior characteristics:
- Earlier commitment to cache-memory leak hypothesis in INC003.
- Better sequencing: investigate -> runbook execution -> resolution confirmation.
- More consistent notification/escalation behavior when customer impact exists.
- Fewer redundant actions and stronger phase progression to postmortem.

Operational effect:
- Live snapshot average reward: `0.4063`
- Best reward: `0.9484`
- Improvement vs baseline: `+53.3%`

## Action-level deltas judges can verify live

1. Run `POST /demo/run/INC003` and inspect transcript phase transitions:
   - Detection -> Triage -> Investigation -> Mitigation -> Resolution -> Postmortem.
2. In manual demo mode (`/web`), use guided flow and observe:
   - structured hypothesis entries,
   - explicit runbook-step execution,
   - completion state with reward breakdown.
3. Compare against baseline narrative in training docs and reward model dimensions.

## Why this satisfies Criterion 4

BRD asks for coherent reward logic and meaningful improvement in inference behavior.  
NEXUS evidence shows both:
- Coherent reward decomposition (MTTR/diagnosis/customer/coordination/oversight/depth).
- Behavioral shifts in sequencing, confidence, and coordination, alongside reward gains.
