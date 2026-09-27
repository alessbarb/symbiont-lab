# Executive Outcome Learning v1 — Specification

**Status:** FROZEN (owner decisions of 2026-09-27 incorporated).
**Depends on:** Agency Acquisition & Executive Action v1 (frozen; see
`agency-acquisition-and-executive-action-v1_implementation-audit.md` §0).

v1 learned to *try*. EOL v1 learns from *how its attempts turned out*, without
turning that learning into reward, physical causality or a new decision
system.

---

## 1. Problem

v1 evidence (ten seeds, eight testable):

- Reconciled intents (C) realize more effects at lower energy and switching
  cost than direct proposals (A), but not at a higher per-commitment hit rate
  (0.47 vs 0.49).
- Against unreconciled intents (B), C is better on 4 seeds, equal on 1 and
  worse on 3. §116's causal advantage is not established.

`ActionIntent` delivers persistence and execution economy, but a real outcome
never changes which competence is admitted next: `IntentionDomain` keeps
outcomes for traceability only.

## 2. Goal

```text
real intent outcome
-> executive outcome evidence
-> modulation of future admission confidence
```

## 3. Principles

1. **Only real outcomes.** Evidence comes from reconciled lifecycle
   terminations of intents that held motor authority. Imagination, generative
   anticipation and rejected proposals never create evidence.
2. **Context-specific.** Key: `(competence_id, anticipated_effect_id,
   context_ref)`. No generalization across contexts in v1 (declared
   limitation, instrumented in §8).
3. **Failure-reason aware** (§5).
4. **No scalar reward.** Evidence modulates the admission relevance of one
   afforded candidate. No `ProspectivePolicy` utility term, no
   `OutcomeValueLedger` entry.
5. **Lifecycle stays lifecycle.** `ActionIntent` never chooses the next
   intent.
6. **Two epistemologies stay separate.** Physical causal belief ("can C
   cause E?") lives in the causal models; executive experience ("when I
   recently pursued C->E here, did it work?") lives only in EOL. EOL never
   writes causal evidence, controllability, agency or competence evidence.

## 4. Architecture

No new CoreDomain. New module `symbiont/agency/executive_outcome.py`:

- `ExecutiveOutcomeSample` — one counted real outcome: `tick`,
  `outcome_class`, `reason`, `effect_similarity`, `prediction_mismatch`,
  `progress_before_failure`.
- `SuppressionEvidence` — the causal/binding revision state an INVALIDATED
  outcome was judged against: `invalidated_tick`, `reason`,
  `binding_fingerprint`, `executable`, `controllability_revision`,
  `agency_revision`.
- `ExecutiveOutcomeEvidence` — per key: the last 16 samples plus optional
  `SuppressionEvidence`. Aggregates (`satisfactions`,
  `contradicting_failures`, `terminal_failures`, `last_failure_reason`,
  `last_outcome_tick`, `progress_before_failure`, `mean_prediction_mismatch`)
  are *derived* from the samples. No confidence is stored.
- `ExecutiveOutcomeLedger` — bounded map of evidence (256 keys,
  least-recently-updated evicted) with saturation counters.
- `ExecutiveAdmissionModulator` — the policy: evidence -> modulation,
  computed at lookup.

`IntentionDomain` owns the ledger (lifecycle, recent outcomes, ledger);
executive admission consults it:

```text
Affordance candidate
  -> ExecutiveOutcomeLedger.lookup(key)
  -> ExecutiveAdmissionModulator
  -> admission gate
```

## 5. Outcome classes

| Status / reason | Class |
| --- | --- |
| SATISFIED `anticipated_effect_observed` | POSITIVE |
| FAILED `repeated_high_mismatch`, `competence_exhausted...`, `stagnation` | CONTRADICTING |
| FAILED `controller_terminal_failure`, `commitment_terminal_failure` | TERMINAL — only if the competence was executable (valid binding) when its commitment was granted authority; otherwise NEUTRAL |
| INVALIDATED `surface_incompatible`, `competence_no_longer_executable`, `required_causal_binding_invalidated`, `embodiment_changed` | SUPPRESS |
| INTERRUPTED (any reason, protective or not) | NEUTRAL |
| REJECTED (never executed) | NEUTRAL |
| SATISFIED `commitment_completed_unverified` (arm B) | NEUTRAL |

NEUTRAL outcomes create no evidence.

## 6. Admission modulation

With `s`, `c`, `t` the POSITIVE, CONTRADICTING and TERMINAL samples in the
key's window:

```text
Ce = (1 + s) / (2 + s + c + 2t)
executive_factor   = clamp(Ce / 0.5, 0.5, 1.5)
admitted_relevance = relevance * executive_factor
```

No history -> factor 1.0. The v1 gate (represented + afforded + relevance >=
threshold) is applied to `admitted_relevance`; the recorded epistemic and
homeostatic relevances are not altered. A suppressed key is not admitted.
Each candidate's factor depends only on its own key.

The model-based deliberation path (private runtime) applies suppression only:
its utility is not modulated (principle 4).

## 7. Suppression

`INVALIDATED` captures the key's `SuppressionEvidence`. The key is excluded
until a *relevant* revision of that relation advances:

- the competence's binding fingerprint (surface, effect, last binding
  evidence tick) changes;
- its executability changes;
- the competence-level controllability or agency estimate for `(C, E,
  context)` is revised (its `last_updated_tick` advances, which only happens
  when C itself acts).

Elapsed time alone never lifts suppression; revisions of other relations
never do.

## 8. Instrumentation

Reported by the ledger: `keys_created`, `keys_evicted`, `live_keys`,
`single_sample_key_fraction`, `mean_samples_per_key`, `lookups`,
`history_hits`, `history_hit_rate`. High eviction or fragmentation means a
study is not a clean test of learning.

## 9. Persistence

`executive_intention` checkpoint schema 2 adds `outcome_evidence` (samples
and suppression evidence, bounded as §4) and the live intent's reconciliation
trace. Schema 1 restores with empty evidence. No raw telemetry is persisted.
Evidence must round-trip exactly and continuations restored from one
checkpoint must be trajectory-identical. (An uninterrupted run and a restored
one differ from the split because Agency v1 deliberately does not checkpoint
the open ActionAttempt, §82.3; this holds with and without EOL.)

## 10. Tests (release gate, mechanical)

1. A real SATISFIED outcome changes only the matching key's future admission.
2. Real CONTRADICTING/TERMINAL failures change only the matching key.
3. NEUTRAL outcomes (INTERRUPTED, REJECTED, unverified completion,
   terminal failure without valid binding) create no evidence.
4. INVALIDATED suppresses until a relevant revision
   (`test_unrelated_causal_revision_does_not_lift_suppression`).
5. `test_executive_failure_does_not_modify_causal_models`.
6. Evidence round-trips exactly; restored continuations are trajectory-identical.
7. E2 and E5 v3 execute with their preregistered protocols.

The scientific result (D > C, D = C, D < C) is recorded afterwards without
moving the criterion.

## 11. Studies

Arms (E5 v3):

```text
A  direct proposals
B  persistent intent, unreconciled (no EOL, by construction)
C  reconciled intent, EOL disabled
D  reconciled intent, EOL enabled
```

C vs B asks whether reconciling real effects helps; D vs C asks whether using
that reconciliation for future admission helps — the EOL question. E2 v3
compares A, C and D. Same ten seeds, horizons and metrics as v2, plus the §8
instrumentation.

## 12. Results (first runs, preregistered at `f5073a7`)

Runs: `20260927T083750Z-learning-agency-intentional-causal-advantage-f5073a7-f392`
(E5 v3), `20260927T083750Z-learning-agency-executive-bridge-ablation-f5073a7-abea`
(E2 v3), `20260927T083750Z-learning-agency-acquisition-reuse-closure-f5073a7-5194`
(E6 with outcome learning on by default). Ten seeds, eight testable.

- **Release gate (mechanical):** all §10 tests pass; E6 still passes on all
  seeds; full suite shows no failure outside the pre-existing baseline.
- **D vs C:** realized commitments per seed D > C on 0, equal on 7, lower on
  1 (seed 149: 23 vs 24). Means: realized 17.75 vs 17.88, realization rate
  0.469 vs 0.467, energy per realized effect 278 vs 277, switches per realized
  effect 35.3 vs 35.2. E2 v3 gives the same D vs C numbers.
- **Not a clean test of outcome learning (preregistered rule).** History hit
  rate over the horizon is 0.000–0.032 on every testable seed (< 0.10); no key
  was evicted. 91–100% of keys hold a single outcome (mean 1.00–1.09 samples
  per key): the exact `(competence, effect, context_ref)` key fragments
  executive memory so that almost no admission meets its own history. This is
  the limitation §3.2 declared and §8 instrumented; the null D vs C result is
  a consequence of it, not evidence that outcome learning cannot help.
- **A, B, C** reproduce the v2 per-seed numbers exactly (C vs B: 4 better,
  1 equal, 3 worse), confirming the arms are deterministic and that the arm
  semantics did not change.

Next (owner decision): the key granularity. Measuring `context_ref`
cardinality per competence would show whether a coarser key yields reusable
history; changing the key is a new version with its own preregistered run.

## 13. Key-granularity diagnostic (read-only, no protocol run)

Default organism, 5000 ticks, every admission lookup replayed against the
keys that already had real non-neutral outcomes, at three granularities:

| Seed | Lookups | Exact `(C, E, context)` | `(C, E)` | `(C)` | Contexts per competence (median / max) |
| --- | --- | --- | --- | --- | --- |
| 101 | 5974 | 0.002 | 0.984 | 0.986 | 3 / 461 |
| 227 | 1294 | 0.005 | 0.855 | 0.894 | 4 / 524 |
| 149 | 25 | 0.000 | 0.000 | 0.920 | 3 / 3 (almost no activity) |

`context_ref` hashes the surface and *all* active concepts, so a single
competence meets hundreds of distinct contexts; dropping the context from the
key turns an unusable memory into one that almost every admission can use.
Candidate for EOL v1.1 (owner decision, new preregistered run): key
`(competence, anticipated effect)`, keeping context out of v1 as §3.2
already anticipated, and reporting the same §8 saturation metrics.
