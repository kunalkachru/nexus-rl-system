# Reward Hacking Defense (Judge-Facing)

Purpose: provide explicit, testable controls showing NEXUS optimizes operationally correct behavior, not shortcuts.

## Threat model

Primary attacker model: trained IC policy attempts to maximize reward using shortcuts that do not solve the incident.

Critical exploit classes considered:

1. **Hypothesis guessing without evidence**
   - Attack: output plausible root cause text without collecting telemetry.
2. **No-op / low-information looping**
   - Attack: repeat directives to inflate apparent activity while avoiding decisive actions.
3. **Customer-impact gaming**
   - Attack: identify impact but never send actual customer notification.
4. **Coordination spoofing**
   - Attack: repeatedly query the same tools/parameters to appear active.
5. **Premature confidence declarations**
   - Attack: jump to high `resolution_confidence` before hypothesis/runbook evidence chain.
6. **Schema rigidity exploit**
   - Attack: rely on fixed API field assumptions and fail silently under drift.

## Controls implemented in NEXUS

## Reward gating controls

- **Evidence-gated diagnosis** in `server/reward.py`
  - Diagnosis score is low if hypothesis is correct but evidence is missing.
  - Correct mitigation steps materially affect diagnosis score.
- **Proactive notification requirement** in `server/reward.py`
  - Customer score requires action (`notifications_sent > 0`), not passive recognition.
- **Duplicate action penalties** in coordination scoring
  - Repeated identical tool calls reduce coordination score.
- **Oversight compliance penalties**
  - Violations and warnings reduce oversight score.

## Environment-level controls

- **Phase progression constraints** in `server/environment.py`
  - Investigation -> mitigation transition requires hypothesis + runbook evidence, or correct coalition.
- **Episode termination constraints**
  - Requires postmortem phase + high confidence, or max-step termination fallback.
- **Schema drift stress test (INC007)**
  - Runtime schema transition forces adaptation behavior.
- **Role-scoped observability**
  - IC cannot directly observe all specialist internals at once.

## Operational controls

- **Remote contract validation** (`openenv validate --url`) ensures stable API behavior.
- **Regression suite** (`test_hf_space_deployment.py`) catches degraded end-to-end behavior.
- **Human transcript review path** (`/demo/run/INC003`, `/state/{session_id}`) supports manual anti-gaming inspection.

## Verification matrix

| Exploit class | Expected blocked behavior | Verification source |
|---|---|---|
| Guessing without evidence | Low diagnosis despite textual guess | `server/reward.py` diagnosis gating + reward tests |
| No-op loops | Weak phase progression and poor final reward | `server/environment.py` phase logic + step traces |
| No customer action | Customer score remains low | `server/reward.py` customer scoring rules |
| Duplicate tool spam | Coordination penalties applied | `server/reward.py` duplicate-count penalty |
| Early confidence jump | No clean completion without proper progression | `server/environment.py` termination logic |
| Static schema assumptions | INC007 drift forces adaptation | `server/environment.py` drift trigger + incident scenarios |

## Exploit test coverage (explicit)

| Exploit case | Automated check |
|---|---|
| Hypothesis without evidence | `tests/test_reward.py::TestDiagnosisScore::test_hypothesis_without_evidence_low` |
| No proactive notification | `tests/test_reward.py::TestCustomerScore::test_no_notification_low_score` |
| Duplicate metric queries | `tests/test_reward.py::TestCoordinationScore::test_duplicate_queries_penalised` |
| Low-signal no-op acknowledgements | `tests/test_reward.py::TestCoordinationScore::test_low_signal_acknowledgements_penalised` |
| Oversight catches duplicate tool behavior | `tests/test_env.py::TestOversight::test_oversight_flags_duplicate_queries` |
| Schema drift enforcement | `tests/test_env.py::TestSchemaDrift::*` |

## Residual risks and mitigations

1. **Residual risk:** model may learn verbose but shallow assessments to chase depth bonus.
   - **Mitigation:** depth bonus includes minimum content threshold + keyword/context structure checks.
2. **Residual risk:** synthetic metric decomposition in `/training-metrics` can be mistaken for raw logged dimensions.
   - **Mitigation:** explicitly tag as derived dashboard diagnostics; use transcript/state evidence for hard claims.
3. **Residual risk:** long training runs may drift toward repetitive safe strategies.
   - **Mitigation:** periodic transcript audits and expert-criteria rotation to rebalance dimensions.

## Judge-ready statement

NEXUS does not rely on a single scalar reward. It combines evidence-gated correctness, operational action requirements, coordination penalties, oversight compliance, and scenario-level stressors (including schema drift) so shortcut behavior is structurally less optimal than correct incident handling.
