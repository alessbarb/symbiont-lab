# Executive Outcome Learning v1 — Draft Specification

**Status:** DRAFT for owner review. Not implemented.
**Depends on:** Agency Acquisition & Executive Action v1 (frozen; see
`agency-acquisition-and-executive-action-v1_implementation-audit.md` §0).
**Origin:** owner review of the v1 evidence, 2026-09-27.

---

## 1. Problem

v1 evidence (ten seeds, eight testable):

- Reconciled intents (C) realize more effects at lower energy and switching
  cost than direct proposals (A), but not at a higher per-commitment hit rate
  (0.47 vs 0.49).
- Against unreconciled intents (B), C is better on 4 seeds, equal on 1 and
  worse on 3. §116's causal advantage is not established.

`ActionIntent` already delivers persistence and execution economy. What it
does not do is let a *real* outcome change which competence is admitted
next. `IntentionDomain.recent_outcomes` records SATISFIED / FAILED /
REJECTED / INTERRUPTED / INVALIDATED with reasons, but that history is used
for traceability, not admission.

## 2. Goal

```text
real intent outcome
-> executive outcome evidence
-> modulation of future admission confidence
```

Success is not "C wins". E2 and E5 are rerun with unchanged criteria and
must remain able to fail. If C > B does not appear, the result is that
reconciliation improves persistence and efficiency but not selection.

## 3. Principles

1. **Only real outcomes.** Evidence comes from reconciled lifecycle
   terminations of intents that actually held motor authority. Imagination,
   generative anticipation and rejected proposals never create evidence.
2. **Context-specific.** Evidence is keyed by
   `(competence_id, anticipated_effect_id, context_ref)`; it does not
   generalize across contexts in v1.
3. **Failure-reason aware.** The termination reason decides what an outcome
   says about the competence (§5).
4. **No scalar reward.** Evidence modulates *admission confidence* of one
   afforded competence. It is never folded into a global utility and
   `ProspectivePolicy` is not given a failure penalty term.
5. **Lifecycle stays lifecycle.** `ActionIntent` and `IntentionDomain` keep
   their v1 responsibilities; they do not choose what happens next.

## 4. Entity

`ExecutiveOutcomeEvidence` — a bounded, derived per-key record, owned by the
executive domain (not by `ActionIntent`):

| Field | Meaning |
| --- | --- |
| `satisfactions` | verified satisfactions (`ANTICIPATED_EFFECT_OBSERVED`) |
| `contradicting_failures` | failures where execution contradicted expectation |
| `terminal_failures` | failures that say the competence cannot realize the effect here |
| `last_failure_reason` | most recent failure reason |
| `last_outcome_tick` | tick of the most recent counted outcome |
| `progress_before_failure` | best effect similarity reached before the last failure |
| `mean_prediction_mismatch` | mean mismatch over counted outcomes |
| `suppressed_until_evidence_change` | set by INVALIDATED; see §5 |

`IntentOutcome` gains `context_ref` (the intent already carries it) so the
key is available at the outcome boundary.

Bounds: at most 256 keys, least-recently-updated pruned; counters are
windowed over the most recent 16 counted outcomes per key.

## 5. Outcome classes

| Status / reason | Evidence effect |
| --- | --- |
| SATISFIED (`anticipated_effect_observed`) | raises admission confidence |
| FAILED `controller_terminal_failure`, `commitment_terminal_failure` | terminal: strongly lowers re-admission in equivalent context |
| INVALIDATED `competence_no_longer_executable`, `surface_incompatible`, `required_causal_binding_invalidated`, `embodiment_changed` | suppresses the key until causal or binding evidence for it changes |
| FAILED `repeated_high_mismatch`, `competence_exhausted...`, `stagnation` | contradicting: lowers confidence gradually |
| INTERRUPTED (protection, homeostatic emergency, new motor authority) | neutral |
| REJECTED (never executed) | neutral: says nothing about capability |
| SATISFIED via `commitment_completed_unverified` (B arm only) | neutral: unverified by construction |

"Evidence changes" for suppression means a change in the competence's
executable status, binding, or the controllability/agency estimate of its
anticipated effect since the invalidation tick.

## 6. Admission

`admit_afforded_action` keeps its v1 gate (represented + afforded +
epistemic or homeostatic relevance >= threshold). A new, explicit step
applies executive history to the candidate before the threshold comparison:

```text
affordance exists
+ prospective support (v1 relevance)
+ executive history (this spec)
-> admission
```

Proposed form (to be fixed before implementation, see §9):

```text
executive_confidence = (1 + s) / (2 + s + w_c * c + w_t * t)
admitted_relevance   = relevance * executive_confidence / 0.5
```

with `s`, `c`, `t` the windowed satisfactions, contradicting and terminal
failures; a key with no history has confidence 0.5 and relevance unchanged.
Suppressed keys are not admitted. The modulation is per candidate; no
candidate's score depends on another candidate's history.

## 7. Persistence

`executive_intention` checkpoint section gains an `outcome_evidence` table
(schema bump, bounded as §4). Older checkpoints restore with empty evidence.
No raw telemetry is persisted.

## 8. Tests and studies

Unit / integration:

- REJECTED and INTERRUPTED outcomes create no evidence.
- Terminal failure lowers re-admission for the same key only; another
  context or another effect is unaffected.
- Suppression lifts only when the key's causal/binding evidence changes.
- Unverified completion (B arm) creates no evidence.
- Evidence survives checkpoint/restore; restored and continuous trajectories
  are identical.
- Cognition never reads the evidence table directly; only admission does.

Studies: rerun E2 and E5 (protocol v3, same ten seeds, same criteria and
horizons as the v2 runs), plus an ablation arm with outcome learning
disabled so the effect is attributable.

## 9. Open decisions for the owner

1. Confidence form and weights (`w_c`, `w_t`) — fix before the first run.
2. Window size (16) and key bound (256).
3. Whether INTERRUPTED by *non-protective* supersession should stay neutral.
4. Whether the B arm (unreconciled intents) gets outcome learning from its
   unverified completions (this draft says no, so B stays a control).
