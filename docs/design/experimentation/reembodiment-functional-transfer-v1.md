---
id: design.experimentation.reembodiment-functional-transfer-v1
title: "Re-embodiment Functional Transfer v1 — Preregistration Draft"
document_type: design
domain: experimentation
status: proposed
canonical: false
implementation_status: not-started
date: 2026-10-02
depends_on:
  - docs/design/core/longitudinal-integrity-v1.md
  - docs/design/embodiment/longitudinal-reembodiment-v1.md
language: en
---

# Re-embodiment Functional Transfer v1 — Preregistration Draft

**Status:** preregistration **draft for owner review**. Not approved, not
registered, not scheduled. No `experiments/` entry, protocol or runner exists
for it, and this document authorizes none.

**Roadmap item:** first "evidence follow-up after integrity remediation" —
*functional transfer advantage after re-embodiment*
(Longitudinal Integrity v1 §17).

**Prerequisite:** the owner closes the Longitudinal Integrity v1 acceptance
gate. Until then a positive result could not be separated from an artifact of
restore.

## 1. Scientific question

Longitudinal Integrity v1 establishes that a Symbiont's own state survives a
Body replacement and that current-Body authority is withdrawn. That is
mechanical continuity. It leaves open the question this study asks:

> Does cognition developed in one Body make the same organism adapt faster to a
> new Body than an organism that never had that experience — because of what
> it learned, and not merely because it is older?

## 2. Claims explicitly not made

A positive result would not demonstrate:

- general out-of-distribution re-embodiment robustness;
- that any particular subsystem carries the advantage;
- that the private model, model ancestry or generative cognition contribute
  (those are separate follow-ups and are held fixed here);
- transfer beyond the Body families and horizons declared below;
- anything about usefulness of retained knowledge for tasks other than
  reacclimation.

A negative result would not show that knowledge was lost; preservation is
already established by the continuity tests.

## 3. Evaluator separation

Evaluator truth stays in `symbiont_lab`. The organism never receives the Body
relation, the arm it is in, the milestone thresholds, the ground-truth
actuator-to-receptor mapping, or any score. All outcome measures are read from
checkpoints and telemetry after the fact and are never fed back.

## 4. Design

### 4.1 Arms

Every arm ends in the same fresh **target Body B** and is measured there. Arms
differ only in what the organism experienced before.

| Arm | Before Body B | Controls for |
| --- | --- | --- |
| **T** transfer | Develops `D` ticks in **source Body A**, then is re-embodied into B | — (treatment) |
| **S** sham experience | Develops `D` ticks in **unrelated Body A′**, then is re-embodied into B | age, developmental stage, graph size, metabolic history, and the restore itself, without relevant content |
| **N** naive | Newborn, saved at tick 0 and restored into B | the restore and reacclimation gate alone |

Arm N is saved and restored rather than started fresh. Every restore opens the
organism-owned reacclimation gate, which pauses structural consolidation for
`kernel_limits.reacclimation_ticks`; without this, arms T and S would carry a
handicap that N does not, and the comparison would be biased against transfer.

### 4.2 Body relation (dose)

Body B's relation to Body A is the manipulated dose. Using the synthetic causal
Body, whose actuator-to-receptor mapping is evaluator-controlled:

| Level | Relation of B to A | Preregistered expectation |
| --- | --- | --- |
| **R1** same structure | same contract and same causal mapping, new Body identity | largest advantage of T over S and N |
| **R2** partial | same interface, half of the actuator-to-receptor mapping permuted | smaller advantage |
| **R3** unrelated | same interface, mapping fully permuted | no advantage; negative transfer is a reportable outcome |

Body A′ (arm S) is a Body whose mapping is fully permuted relative to **B** at
every level, so S never has relevant prior content.

A dose-ordered result (R1 > R2 > R3) is evidence that content, not maturity,
carries the effect. An advantage of equal size at all three levels would
indicate a maturity effect and is **not** transfer.

### 4.3 Held fixed across arms

- Runtime class, genome, kernel limits, physiology configuration.
- Session controls: recorded in `runtime_provenance.session_controls`; every
  arm must report `changed_since_restore == []` at the end of the B phase.
- No private-model inference bridge is attached in any arm.
- Body B: same seed, same fresh physiology, same host readings per seed.
- Ticks: `D` development ticks (arms T, S), `H` measurement ticks in B (all).

### 4.4 Seeds

Development seeds, used only to fix `D`, `H` and to check that milestones are
reachable at all, are disjoint from confirmation seeds. Confirmation seeds are
not run until this document is approved and frozen.

- Development: 3 seeds.
- Confirmation: 12 seeds, each run for all three arms at all three relation
  levels (108 runs), paired by seed.

## 5. Outcome measures

Measured in **embodiment ticks since entering Body B**, right-censored at `H`.

Primary:

- **M1** — ticks to the first execution binding that reaches `VALID` in B.

Secondary, using the existing `EmbodimentAdaptation` convergence criteria
unchanged (causal confidence ≥ 0.45, controllability ≥ 0.35, schema uncertainty
≤ 0.35, prediction shock ≤ 0.20):

- **M2** — ticks to reacclimation completion.
- **M3** — ticks to causal confidence ≥ 0.45.

Descriptive only: number of valid bindings at `H`, cumulative metabolic cost in
B, number of Body A competences revalidated versus retired.

## 6. Integrity conditions

A run is **contaminated**, excluded and reported — never repaired — if any of
these fails:

1. At B tick 0 the organism holds no `VALID` execution binding and no active
   commitment.
2. The re-embodied checkpoint verifies its identity and records the
   `re-embodiment` transform.
3. Organism identity and organism time continue across the transform.
4. Symbiont-owned state at B tick 0 equals the state saved in the source Body
   for every field the continuity register marks as preserved.
5. `changed_since_restore` is empty.
6. Observer density does not differ between arms.

If more than 2 of 12 seeds are contaminated at any relation level, that level
is **not assessable** and no claim is made for it.

## 7. Decision rule

Fixed before confirmation runs. For each relation level, on primary measure M1,
paired by seed:

- **Transfer supported** at that level if arm T reaches M1 earlier than **both**
  S and N in at least 10 of 12 seeds (one-sided sign test, p ≈ 0.019 per
  comparison) **and** the median paired reduction relative to S is at least
  20%.
- **Negative transfer** if T reaches M1 later than N in at least 10 of 12
  seeds.
- **No transfer** otherwise. A censored-versus-censored pair is a tie.

Overall claim:

- **Functional transfer established within scope** only if transfer is
  supported at R1 **and** the median paired reduction is ordered R1 ≥ R2 ≥ R3
  **and** transfer is not supported at R3.
- If T beats N but not S at R1, the result is **maturity effect, not transfer**.
- Anything else is reported as no-transfer or not-assessable. No measure,
  threshold, seed or exclusion is added after the confirmation runs start.

Secondary measures are reported alongside and cannot rescue a primary
no-transfer result.

## 8. Draft experiment record

Proposed content, shown here only for review. It is **not** an
`experiment.toml` and registers nothing.

```toml
[experiment]
id = "embodiment.reembodiment-functional-transfer-v1"
protocol = "embodiment.reembodiment-functional-transfer"
protocol_version = 1

[design]
arms = ["transfer", "sham_experience", "naive"]
relations = ["same_structure", "partial", "unrelated"]
development_seeds = "3, fixed at approval"
confirmation_seeds = "12, fixed at approval, disjoint from development"
development_ticks = "D, fixed from development seeds"
measurement_ticks = "H, fixed from development seeds"
naive_arm_is_restored = true
private_model_bridge = false

[metrics]
primary = "ticks_to_first_valid_binding"
causal_confidence_threshold = 0.45
controllability_threshold = 0.35
schema_uncertainty_threshold = 0.35
prediction_shock_threshold = 0.20

[decision]
min_seeds_improved = 10
min_median_paired_reduction = 0.20
max_contaminated_seeds = 2
```

## 9. Relation to existing evidence

- `experiments/embodiment/reembodiment-reacclimation-v1/` (A-B-A) remains the
  regression anchor for same-contract return. It compares an organism with its
  own earlier epoch and has no sham-experience control, so it cannot separate
  transfer from maturity; this study adds that control and the dose.
- The E7 heredity campaign concerns what crosses a generation, not what a
  single organism carries across Bodies. Its no-leak result is unaffected.
- The re-embodiment continuity integration test of Longitudinal Integrity v1
  already runs the mechanical version of arm T on the synthetic causal Body; it
  measures preservation, not benefit.

## 10. Decisions required from the owner

1. Whether to schedule this follow-up at all, and when relative to the other
   three.
2. The apparatus: synthetic causal Body (cheap, mapping exactly controlled) or
   Physics3D (realistic, mapping only approximately controllable). The
   synthetic Body currently offers a normal and a fully permuted mapping; the
   partial level R2 needs a partially permuted condition added to it.
3. The primary measure and the two decision thresholds in §7.
4. Seed counts, and who fixes `D` and `H` from the development seeds.
5. Whether a maturity-only outcome should trigger a follow-up design.

## 11. What approval would start

On approval: freeze this document, add the protocol and `experiment.toml`, add
the runner and its mechanical contract tests under `tests/experiments/`, run the
development seeds, fix `D` and `H`, and only then run the confirmation seeds.
None of that exists or is started by this draft.
