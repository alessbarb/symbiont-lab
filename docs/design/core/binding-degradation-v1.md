# Binding Degradation v1 — invalidation against a binding's own history

Status: **preregistered, not implemented** (owner decision 2026-09-28).
An independent experiment; not part of Revision Coherence Wave 1 defaults.
Kept separate from footprint membership (Footprint Precision v1): no arm
combines the two mechanisms.

## 1. Background

The rule of Revision Coherence §3.9 decision 1 compared a binding's recent
match rate with the rate at which its effect appears **at rest**. It is a
recorded negative result (§3.11): with scarce passive evidence the rest-rate
upper bound is large, so a binding is invalidated after a handful of
failures, and the factorized E6 release gate fails (seed 149 never closes).
Its point-estimate form never fires for effects never seen at rest. It is
kept only as an experimental control arm, off by default.

## 2. Rule under test (arm HIST)

A binding is compared with **its own causal performance in its current
revision**; rest is never used.

- **Reference.** For binding revision `r`, the first `N_REF = 8`
  executions of the competence after the binding became VALID in revision
  `r` form the reference: `k_ref` matches out of `n_ref = 8`. It is frozen
  when complete; a new revision starts a new reference.
- **Degradation evidence.** Only executions after the reference is frozen,
  each a **new commitment** whose causal windows do not overlap the
  reference or each other and whose evidence blocks are not reused (an
  execution is one commitment; its windows are its own evidence). Matches
  do not reset the sample: `k_new` matches out of `n_new` executions,
  cumulative within the revision.
- **Criterion.** Invalidate (INVALIDATED / `EVIDENCE_CONTRADICTED`) when
  `n_new ≥ N_MIN = 8` and the Wilson 99% upper bound of `k_new / n_new`
  is below the Wilson 99% lower bound of `k_ref / n_ref` (z = 2.576): the
  current performance is credibly below the performance the binding was
  confirmed with. Evaluated after each new execution; the 99% level is
  chosen to keep the repeated-evaluation false-alarm rate low, and the
  study measures it directly.
- **Separation.** STALE (surface or embodiment not current, controller
  unavailable) is unchanged and never counts as degradation; executions
  while STALE are not evidence.
- **Trace.** Each invalidation is a binding status transition with a new
  content-addressed provenance event (the revision identity), caused by
  the competence and the commitments of the degradation sample.

Minimum evidence to invalidate is therefore 16 executions (8 reference, 8
new); with `k_ref = 8/8` (lower bound 0.55) about 0/8 new matches suffice;
with `k_ref = 4/8` (lower bound 0.17) roughly 0/33 are needed.

## 3. Study BD-1 (preregistered)

**Arms.** `OFF` (default behaviour, no invalidation) and `HIST` (§2). The
rest-based rule is not an arm.

**Body and ground truth.** E8 body (16 actuators × 4 correlated receptors
+ 32 drifting), factorized effects, 4 000 ticks. At tick 2 000 the body is
switched to `BROKEN_EFFECTOR` (actuator 0 drives nothing). Evaluator-only
ground truth: a binding is **truly degraded** if its competence's
controller uses actuator 0 and it was VALID at tick 2 000; every other
binding VALID at tick 2 000 is **at risk of false invalidation**.

**Seeds.** New seeds not used by any earlier agency or footprint study:
409, 419, 421, 431, 433, 439, 443, 449, 457, 461.

**Metrics.** True detections (truly degraded bindings invalidated after
tick 2 000) and their latency; false invalidations (at-risk bindings
invalidated, at any time); invalidations before the break; spurious
satisfactions (all matched atoms on drifting receptors) and satisfied
intents per arm; executable competences at the end.

**Criteria, fixed now.** HIST qualifies if:

1. false invalidations ≤ 5% of at-risk bindings (pooled);
2. true detections ≥ 50% of truly degraded bindings (pooled) — reported
   as not assessable if fewer than 5 truly degraded bindings exist;
3. spurious satisfactions in HIST ≤ those in OFF (pooled);
4. the E6 release gate (factorized, seeds 101/127/149, no break) passes
   3/3 with HIST.

All four → HIST is proposed as an option (default is an owner decision).
Criterion 1 or 4 fails → rejected. Otherwise reported, not proposed. No
parameter (`N_REF`, `N_MIN`, z) changes after results.

## 4. BD-1 result (2026-09-28) — reported, not proposed

Runs on `ac504417`: OFF `20260928T101601Z-learning-binding-degradation-ac50441-0349`,
HIST `...-f95a`, E6 gate with HIST
`20260928T101601Z-learning-agency-acquisition-reuse-closure-ac50441-1d3a`.

| Criterion | OFF | HIST | Met |
|---|---|---|---|
| 1. False invalidations ≤ 5% of at-risk | 0/197 | 0/197 | yes |
| 2. True detections ≥ 50% of degraded | 0/79 | **0/79** | **no** |
| 3. Spurious satisfactions ≤ OFF | 13 | 13 | yes |
| 4. E6 gate 3/3 with HIST | — | 3/3 | yes |

Criterion 2 fails (79 truly degraded bindings, so it is assessable) while
1 and 4 hold: by the decision rule HIST is **reported, not proposed** and
not rejected. No parameter changes.

The two arms are identical in every metric: HIST never invalidated
anything. Diagnostic (seed 409, same code, not evidence): 600 commitments
ended, 177 on a bound competence, concentrated on six competences (106,
40, 17, 8, 5, 1 executions); only 6 of 61 bindings were ever executed and
only 2 completed their 8-execution reference. **55 of 61 bindings were
never executed**, so no execution-based rule can observe their
degradation. The rule itself is safe (no false invalidation, E6 intact)
but starved of evidence.

Reading: evidence-based invalidation depends on the organism re-executing
its competences. That is the problem Revision Coherence Wave 2
(endogenous epistemic retest) addresses, which in turn is gated on
footprint precision (Footprint Precision v1, where no membership fix has
yet qualified). BD-1 cannot pass until competences are re-exercised; a
retest mechanism would have to be established independently first.
