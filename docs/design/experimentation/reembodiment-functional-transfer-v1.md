---
id: design.experimentation.reembodiment-functional-transfer-v1
title: "Re-embodiment Functional Transfer v1 — Frozen Preregistration"
document_type: design
domain: experimentation
status: approved
canonical: false
implementation_status: in-progress
date: 2026-10-02
depends_on:
  - docs/design/core/longitudinal-integrity-v1.md
  - docs/design/embodiment/longitudinal-reembodiment-v1.md
language: en
---

# Re-embodiment Functional Transfer v1 — Frozen Preregistration

**Status:** **approved and frozen (r8, 2026-10-03)**. The owner approved the
synthetic causal Body, the proposed numbers and the confirmation seeds (r5), the
subject configuration (r6), the family rule and development seeds (r7), and
`D_max = 2000` (r8, §10.2). Regime: **confirmatory**. The r5, r6 and r7
development stages are superseded; **no r8 development or confirmation seed has
been run**.

**Acceptance test.** The owner requires that an organism re-embodied in a new
Body manages it sooner than a newborn (canonical organism profile register,
§6). This experiment is the acceptance test of that requirement. A negative
result is recorded as a finding that the organism does not yet meet it; it never
leads to a change of this protocol.
Nothing in this document may change after the first confirmation run starts;
any change before then is a new revision.

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
| **R2** partial | same interface, exactly half of the actuator-to-receptor pairs shared with B | smaller advantage |
| **R3** unrelated | same interface, no pair shared with B | no advantage; negative transfer is a reportable outcome |

A dose-ordered result (R1 > R2 > R3) is evidence that content, not maturity,
carries the effect. An advantage of equal size at all three levels would
indicate a maturity effect and is **not** transfer.

### 4.2.1 Balanced construction of A, A′ and B

A difference in how hard two Bodies are to learn would look like transfer. The
three Bodies are therefore members of one family and differ only in *which*
mapping they realise:

- identical actuator count, receptor count, receptors per actuator, inert
  actuators and drifting receptors;
- every mapping is a bijection between actuators and driven receptors, so
  fan-in and fan-out are 1 for every Body;
- the relation to B is defined by the number of shared actuator-to-receptor
  pairs `k` out of `n`, with `n` even: R1 `k = n`, R2 `k = n / 2`, R3 `k = 0`;
- Body A′ (arm S) always shares `k = 0` pairs with B, at every level;
- at R3, Body A also shares `k = 0` pairs with B. Arms T and S are then
  exchangeable by construction, which makes R3 a negative control: any
  systematic T–S difference there is an apparatus asymmetry, not transfer;
- which of two `k = 0` mappings plays A and which plays A′ at R3 is swapped on
  alternate confirmation seeds.

Learning difficulty is checked, not assumed. On the development seeds a naive
organism is run in A, A′ and B as stand-alone Bodies; if the median ticks to
the first `VALID` binding differ by more than 15% between any two of them, the
family is rejected and rebuilt before any confirmation seed is run.

**Family rule (r7).** The family is not chosen by hand. On the development
seeds, the median naive ticks to a first `VALID` binding is measured for the
target and for every candidate: the six mappings sharing exactly two pairs with
B (partial) and the nine sharing none (unrelated). The family is the partial
candidate and the pair of distinct unrelated candidates whose four medians,
with the target's, have the smallest spread (max − min over the median of the
four); ties go to the lexicographically smallest (partial, unrelated 1,
unrelated 2). If that smallest spread exceeds 15%, or a candidate set is empty
because no development organism binds by `D_max`, the study is not runnable.
The chosen family is written to `horizons.json` and the confirmation stage
reads it from there.

The synthetic Body currently offers a normal and a fully permuted mapping; a
mapping with a chosen number of shared pairs must be added to it.

**One identity space (r4).** "Shared pair" is only meaningful if the two Bodies
name actuators and receptors identically. The synthetic Body derives its opaque
receptor identifiers, its distractor schedule and its drift from its
construction seed, and its actuator identifiers and contract fingerprint from
its shape. Bodies A, A′ and B are therefore built with the **same construction
seed and the same shape**, and differ **only** in the actuator-to-receptor
mapping, which must be a parameter independent of the seed. Two Bodies built
with different seeds share no signal identifier, so nothing learned in one can
refer to anything in the other: R1 would equal R3 by construction and the dose
would mean nothing.

"New Body identity" at R1 consequently means a new embodiment epoch entered
through the re-embodiment transform, not new signal identifiers. The three
Bodies have the same contract fingerprint.

The mapping parameter must leave the existing `NORMAL`, `PERMUTED` and
`BROKEN_EFFECTOR` conditions byte-identical in readings and ground truth, pinned
by a regression test: ten recorded agency-acquisition experiments use this Body.

### 4.3 Held fixed across arms

- Organism configuration: the canonical organism profile `v1` (ADR-0062) in
  every arm, so factorized effects are off. A restored organism keeps the profile
  it was born with; the post-restore reacclimation gate holds concepts and
  connections, not receptors (r6).
- Runtime class, genome, kernel limits, physiology configuration.
- Session controls: recorded in `runtime_provenance.session_controls`; every
  arm must report `changed_since_restore == []` at the end of the B phase.
- No private-model inference bridge is attached in any arm.
- Body B: same seed, same fresh physiology, same host readings per seed.
- Ticks: `D` development ticks (arms T, S), `H` measurement ticks in B (all),
  both fixed by the rule in §4.5.

### 4.4 Seeds

Seeds are fixed in this document and are not chosen after any run.

- Development: `101, 103, 107, 109, 113, 131, 137, 139, 149` (r7; nine seeds so
  that the difficulty medians of §4.2.1 are not decided by three values). Seed
  127 was used for the exploratory observation of §10.1.1 and is excluded from
  both lists (r5).
- Confirmation: `173, 211, 257, 307, 353, 401, 457, 503, 557, 601, 653, 701`.

Each confirmation seed is run for all three arms at all three relation levels
(108 runs), paired by seed. Confirmation seeds are not run until this document
is approved and frozen. Development seeds are used only for §4.2.1 and §4.5.

### 4.5 Fixing `D` and `H`

Both horizons are computed by rule from the development seeds. Nobody chooses
them, and neither rule looks at arm T.

- **`D`** — the smallest multiple of 100 ticks, up to `D_max = 2000` (r8; 1000
  before), at which
  every development organism holds at least one `VALID` execution binding in
  every source Body of the family (the R1, R2 and R3 sources and the sham
  Body). If that does not happen by `D_max`, the study is **not runnable** and
  is reported as such.
- **`H`** — equal to `D` (r5). The earlier rule tied `H` to the naive arm, which
  would right-censor a slower treatment arm and hide how much slower it is.

`D`, `H`, the Body family and the swap order of §4.2.1 are written into the
experiment record before the first confirmation run and are not revised.

## 5. Outcome measures

Measured in **embodiment ticks since entering Body B**, right-censored at `H`.

Primary:

- **M1** — ticks to the first execution binding that reaches `VALID` in B.

A binding counts for M1 only if it is evidence acquired in B:

- its `surface_fingerprint` is Body B's contract fingerprint (within the
  balanced family of §4.2.1 all three Bodies share one fingerprint, so this
  sub-criterion cannot discriminate there; it is kept as a guard against a
  mis-built family, and the two conditions below carry the weight);
- its `valid_from_tick` is later than the tick of entry into B;
- every one of its `evidence_refs` was produced after entry into B.

Integrity condition 1 already requires zero `VALID` bindings at B tick 0, so a
preserved structure cannot satisfy M1 by being carried over. Arm S controls for
the alternative that a larger or older graph validates faster.

**Activity guard.** A binding could also be reached sooner merely by acting
more. For each run, let

```text
actuations = number of (tick, actuator) pairs with a non-zero requested
             activation, from entry into B up to and including the M1 tick
             (up to H for a censored run)
rate       = actuations / M1          (actuations / H for a censored run)
```

and for each seed let `rho = rate(T) / rate(S)`. There is an **activity
excess** at a level if the median of `rho` over the 12 seeds is greater than
`1.20`. An advantage with an activity excess is reported as **activity, not
transfer** and does not support the claim. The 1.20 margin is fixed here and is
not revisited after the confirmation runs.

Secondary measures M2 (ticks to reacclimation completion) and M3 (ticks to
causal confidence ≥ 0.45) were defined on `EmbodimentAdaptation`, which is
tracked by the `EmbodimentEpisode` of the Physics3D apparatus. The synthetic
causal Body has no such episode, so **M2 and M3 are not measured in this
experiment (r5)**. They were secondary and could neither rescue nor strengthen
the confirmatory claim; nothing replaces them.

Descriptive only: number of valid bindings at `H`, actuations before M1,
cumulative metabolic cost in B, number of Body A competences revalidated versus
retired.

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
6. **Observer schedule is identical across the three arms of a seed.** The
   apparatus is deterministic, so this is exact equality, not a tolerance: the
   same number of observer reads (`checkpoint(advance_lineage=False)`,
   `state_hash()`, telemetry snapshots) at the same embodiment ticks.
7. **Body B is the same Body across the three arms of a seed**: same
   construction seed, same mapping and same evaluator ground-truth hash. The
   Body is closed-loop, so the reading *streams* legitimately differ through
   each organism's own actuations; what must be identical is the Body and the
   response of every receptor that no actuator drives, which is compared by
   hash.

If more than 2 of 12 seeds are contaminated at any relation level, that level
is **not assessable** and no claim is made for it.

## 7. Decision rule

Fixed before confirmation runs. All comparisons are on primary measure M1,
paired by seed. A censored-versus-censored pair is a tie.

### 7.1 Per-level outcomes

These are components of one claim, not separate claims.

- **Advantage** at a level: let `W` be the set of seeds in which, **in that same
  seed**, `M1(T) < M1(S)` and `M1(T) < M1(N)`. There is an advantage if
  `|W| ≥ 10` of 12 **and** the median over seeds of
  `(M1(S) − M1(T)) / M1(S)` is at least `0.20`. This is one count over one set
  of seeds, not two separate 10-of-12 comparisons. Under no effect a seed is in
  `W` with probability at most 0.5, so the one-sided sign test bound
  `P(|W| ≥ 10) ≤ 0.019` holds for the joint condition.
- **Meets the practical-null criterion** at a level: the median over seeds of
  `(M1(S) − M1(T)) / M1(S)` lies within `±0.10` **and** neither T nor S is
  earlier in 10 or more of 12 seeds. This is a preregistered criterion of
  practical irrelevance. It is not a statistical equivalence test and is not
  reported as one.
- **Negative transfer** at a level: T reaches M1 later than N in at least 10 of
  12 seeds.
- **Inconclusive** otherwise.

Meeting the practical-null criterion is a positive finding with its own margin.
Failing to show an advantage is not the same thing and is recorded as
inconclusive.

### 7.2 The single confirmatory claim

There is one confirmatory claim, a conjunction, so there is no multiplicity to
correct for:

> **Functional transfer established within scope** if and only if there is an
> advantage at R1, **and** the median paired reduction is ordered
> R1 ≥ R2 ≥ R3, **and** R3 meets the practical-null criterion, **and** there is
> no activity excess at R1 (§5).

Other preregistered outcomes:

- T beats N but not S at R1 → **maturity effect, not transfer**.
- Advantage at R1 but R3 inconclusive → **advantage at R1, dose pattern not
  established**. No transfer claim.
- Advantage at R1 with an activity excess → **activity, not transfer**.
- Advantage at R3 → **apparatus asymmetry**; the study is invalid, because T
  and S are exchangeable there by construction.
- Anything else → no-transfer or not-assessable.

R2 contributes only to the ordering. Secondary measures M2 and M3 are reported
alongside and cannot rescue or strengthen the confirmatory claim. No measure,
threshold, margin, seed or exclusion is added after the confirmation runs
start.

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
shared_pairs_fraction = { same_structure = 1.0, partial = 0.5, unrelated = 0.0 }
sham_shared_pairs_fraction = 0.0
swap_unrelated_source_on_alternate_seeds = true
development_seeds = [101, 127, 149]
confirmation_seeds = [173, 211, 257, 307, 353, 401, 457, 503, 557, 601, 653, 701]
naive_arm_is_restored = true
private_model_bridge = false

[horizons]
development_ticks_rule = "smallest multiple of 100 <= 1000 with a VALID binding and reacclimation complete on all development seeds"
measurement_ticks_rule = "2 x median naive M1 at same_structure, rounded up to 50, capped at development_ticks"
max_body_difficulty_spread = 0.15

[metrics]
primary = "ticks_to_first_valid_binding"
primary_requires_target_body_evidence = true
causal_confidence_threshold = 0.45
controllability_threshold = 0.35
schema_uncertainty_threshold = 0.35
prediction_shock_threshold = 0.20

[decision]
min_seeds_improved = 10
min_median_paired_reduction = 0.20
practical_null_margin = 0.10
max_activity_rate_ratio = 1.20
advantage_requires_same_seed_win_over_both_controls = true
max_contaminated_seeds = 2
confirmatory_claim = "advantage at same_structure AND ordered reductions AND unrelated meets practical-null criterion AND no activity excess at same_structure"
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
2. The apparatus. **Proposed default: the synthetic causal Body**, because the
   question is whether learned content causes the advantage and only that
   apparatus controls the mapping exactly. A Physics3D replication for external
   validity would follow a positive result and would be its own preregistration.
3. The numbers proposed in this draft: the 20% reduction, the ±10%
   practical-null margin, the 1.20 activity-rate ratio, the 15% Body-difficulty
   spread, `D_max`, and the 10-of-12 criterion. Of these the 15% spread is the
   least grounded and is the one the development runs should be used to justify
   or tighten before the freeze.
4. The seed lists in §4.4. Seed 127 is a development seed and was used for the
   exploratory observation of §10.1.1; whether it stays in the development list
   is part of this decision.
5. Whether a maturity-only outcome should trigger a follow-up design.
6. Whether the horizon rule for `H` should stay as written given §10.1.1: with
   `H` tied to the naive arm, a slower treatment arm is right-censored, which
   the paired comparison handles (a censored T against an uncensored control is
   a loss for T) but which hides *how much* slower it is.

## 10.1 Apparatus note on `D_max`

To check that `D_max = 1000` is not short for the existing apparatus, a naive
organism was run in the current synthetic causal Body (4 actuators) on three
seeds that appear in neither list of §4.4 (7, 11, 13). The first `VALID`
binding appeared at ticks 189, 245 and 253. `D_max` is therefore about four
times the observed time to a first valid binding. This is an order-of-magnitude
check of the apparatus, not a development run, and it fixes nothing.

### 10.1.1 Apparatus facts checked for r4

Checked on the existing code, without running any development or confirmation
seed and without the mapping parameter (so only the R1-like case, a Body
identical to the source, could be built):

- Re-embodiment into a Body of the same shape and construction seed yields the
  same contract fingerprint and the same receptor identifiers.
- The transform empties the execution bindings regardless of whether the
  fingerprint changed: at B tick 0 there are no bindings and no active
  commitment, and the lifecycle epoch advances. Integrity condition 1 therefore
  holds for the balanced family.
- A single exploratory observation, on seed 127, outside both seed lists' use
  and outside the protocol (the naive organism was not saved and restored, no
  sham arm, one seed): the organism re-embodied into the identical Body after
  400 ticks reached its first `VALID` binding 363 ticks after entry; a newborn
  in the same Body reached it at tick 114. This is not a result and fixes
  nothing. It is recorded because it shows that **negative transfer is a live
  possibility** for this apparatus, which the decision rule already names as an
  outcome, and that `H = 2 × median naive M1` capped at `D` may censor arm T.

## 10.2 Revision history

- **r8, 2026-10-03 — approved and frozen.** The r7 development stage chose a
  family with no difficulty spread but did not reach `D` by `D_max = 1000`: a few
  slow development organisms did not hold a valid binding at the same cut. An
  exploratory diagnostic on the development seeds found all 36 holding one at
  1500 ticks, and Competence Establishment Evidence v1 showed that a stricter
  competence gate does not help (no change). Owner decision: `D_max` becomes
  2000; the rule for `D` is unchanged. Execution only: the confirmation stage
  may run its 108 arm runs in up to four processes and rewrites a progress file
  after every run. No threshold, seed, arm, relation or decision rule changes.
  The r7 development outputs are kept under `development-r7/`.

- **r7, 2026-10-03 — approved and frozen.** The r6 development stage found the
  hand-built family outside the 15% spread (medians 87/73/73/93, spread 0.25):
  with the canonical organism, which adapts its receptors from the first tick,
  the mapping changes how fast a newborn first binds. By §4.2.1 the family is
  rejected and rebuilt. Owner decisions: the family is fixed by rule over every
  candidate mapping on the development seeds (§4.2.1), and the development seeds
  grow from three to nine (§4.4). No threshold, confirmation seed, arm,
  relation or decision rule changes; the 15% limit is unchanged. The r6
  development outputs are kept under `development-r6/`.

- **r6, 2026-10-03 — approved and frozen.** Protocol deviation found in r5 and
  corrected before any confirmation seed: the r5 apparatus built every subject
  with factorized effects enabled, a non-default mechanism on hold that the
  protocol never declared, and the r5 development stage ran that way. Owner
  decisions: the subject is the canonical organism profile `v1` (§4.3), so
  factorized effects are off; reacclimation does not hold receptors; the
  experiment is the acceptance test of the re-embodiment requirement (status
  line). Consequence: the r5 development stage (`D = H = 400`) is superseded and
  kept under `development-r5/` as history; `D` and `H` are fixed again by the
  unchanged rule of §4.5 on the unchanged development seeds. No number,
  threshold, seed list or decision rule changes.

- **r5, 2026-10-02 — approved and frozen.** Owner decisions: apparatus is the
  synthetic causal Body; the proposed numbers stand (20% reduction, ±10%
  practical-null margin, 1.20 activity-rate ratio, 15% Body-difficulty spread,
  `D_max = 1000`, 10 of 12); development seed 127 is replaced by 131; `H = D`.
  Forced by the approved apparatus and recorded before any run: M2 and M3 are
  not measured (§5); the `D` rule requires a `VALID` binding in every source
  Body and no longer refers to reacclimation-completion criteria (§4.5); the
  Body family is realised with four actuators as the identity mapping (target),
  a mapping sharing two pairs, and two mappings sharing none (§4.2.1). The draft
  record of §8 is superseded by
  `experiments/embodiment/reembodiment-functional-transfer-v1/experiment.toml`.

- **r4, 2026-10-02.** Apparatus facts checked against the code: Bodies A, A′
  and B must share one construction seed and shape and differ only in a
  seed-independent mapping; the fingerprint sub-criterion of M1 is vacuous
  inside that family; integrity condition 1 holds because the transform empties
  bindings unconditionally. One exploratory observation is recorded in §10.1.1.
  No seed of §4.4 was run.

- **r3, 2026-10-02.** After a second external review: the activity guard is a
  defined rate ratio with a fixed margin; the 10-of-12 advantage criterion is
  stated as one count over the same seeds against both controls; the R3
  criterion is named a practical-null criterion and explicitly not a
  statistical equivalence test; an apparatus note supports `D_max`.

- **r2, 2026-10-02.** After external review: `D` and `H` are computed by rule
  instead of chosen; seeds are listed; R3 requires a practically-null finding
  with its own margin instead of a mere failure to show an advantage; Bodies A,
  A′ and B are constructed as a balanced family with a difficulty check and R3
  as a negative control; observer-schedule and same-Body conditions are defined
  exactly; M1 must rest on evidence acquired in the target Body and is guarded
  against an activity explanation; one conjunctive confirmatory claim replaces
  per-level claims.

## 10.3 Known property of the practical-null criterion

Recorded while writing the contract tests, before any run: the criterion of §7.1
is stated on the median paired reduction and on seed counts. A level in which
half the seeds are much earlier and half much later therefore has a median
reduction near zero, neither arm wins ten seeds, and it is classified as
practically null although the per-seed effects are large and opposite. The rule
is not changed. If a level shows that pattern, the report must say so and show
the per-seed values next to the classification.

## 11. Execution

Implemented: `symbiont_lab.studies.embodiment.reembodiment_functional_transfer`,
the experiment record, and the contract tests in
`tests/experiments/protocols/test_reembodiment_functional_transfer_protocol.py`.

Order, each step a governed run through `agentctl run start`:

1. development stage on seeds 101, 131 and 149: Body-difficulty check and the
   rule for `D`; the result is committed as `horizons.json`. If the family is
   outside the 15% spread or `D` is not reached, the study is not runnable and
   that is the recorded result;
2. confirmation stage on the twelve confirmation seeds, three relation levels,
   three arms (108 runs);
3. the preregistered decision rule is applied as implemented; no measure,
   threshold, margin, seed or exclusion is added.
