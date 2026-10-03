---
id: design.embodiment.physics3d-a7-stability-gate-v1
title: "Physics3D A7 Stability Gate V1"
document_type: design
domain: embodiment
status: proposed
canonical: false
implementation_status: not_started
migrated_on: 2026-10-03
last_reviewed: 2026-10-03
language: en
---
# Physics3D A7 Stability Gate v1

**Lifecycle:** proposed protocol; not frozen. No campaign has been authorized or
run under this document.

## 1. Purpose and boundary

This proposal defines a bounded apparatus-validation campaign for A7 in the
[research programme](../../methodology/research-programme.md). It tests
numerical and mechanical invariants of the Physics3D apparatus. It does not
test organism learning, competence, biological robustness, or universal
physical correctness.

The campaign must keep three claims separate:

1. **Mechanical contract:** the selected checks execute and reject invalid or
   out-of-contract states.
2. **Protocol validity:** the declared body, scenario, seed, parameter,
   checkpoint, and replay conditions were actually exercised.
3. **Scientific result:** only a future, separately authorized study could
   support claims about biological or behavioral robustness.

The current source registry names four canonical bodies: `anthropomorphic-v6`,
`anthropomorphic-v6-vision`, `crawler-v1`, and `asymmetric-v1`.

## 2. Proposed campaign matrix

Exercise every canonical body in each of these seven A7 condition categories:

1. Idle stability.
2. Actuation stress.
3. Collision stress.
4. Checkpoint and restore.
5. Re-embodiment.
6. Friction perturbation.
7. Mass perturbation.

The first five categories have one declared condition per body. Friction and
mass each have three arms per body: nominal, `-10%`, and `+10%` relative to the
declared baseline. This yields 28 body/category cells and 44 parameter arms
before seed replication. Perturbations must affect only the named parameter;
other settings remain fixed.

For each parameter arm, the proposed seed set is `[42, 43, 44]`. Repeat each
seed once with the same initial state and conditions to check deterministic
replay. The seed set is a mechanical reproducibility sample, not a population
sample and not evidence that all seeds behave alike.

## 3. Candidate condition settings

The owner accepted the high-level design choices on 2026-10-03: the 360-tick
horizon, fixed deterministic actuation, a prescribed collision input using
the fixed fixture, all six directed re-embodiment pairs, and the friction/mass
perturbation scopes. The more specific schedule, pose and velocity values
below are concrete draft settings for review; only their high-level form has
been accepted. No setting authorizes execution until all criteria are reviewed
and the protocol is explicitly frozen.

| Condition | Proposed fixed setting | Provenance / limitation |
|---|---|---|
| Runtime | `time_step=1/240 s`, 10 physics substeps per cognition tick, gravity `(0, 0, -9.81) m/s^2`, 120 solver iterations, ERP `0.8`, residual threshold `1e-9`. | Existing Physics3D runtime/solver defaults; record the actual PyBullet version and effective configuration in every run. |
| Horizon | 360 cognition ticks per condition; proposed checkpoint/replay split at tick 180, then continue for 180 ticks. | The 360-tick horizon is owner-accepted; split tick remains a concrete draft setting. Not a normative stability limit. The existing 360-step humanoid test has different substeps and does not validate this horizon for all bodies. |
| Initial state | Fresh body at its descriptor's declared spawn height, origin `(0,0,z)`, identity orientation, zero base velocity and zero joint state; fixed flat ground except for collision stress. | Draft initialization. Must be instantiated from the same pinned body/runtime revision for paired replays. |
| Idle | All effector channels receive zero activation for all 360 ticks. | Draft implementation of the accepted idle condition; no behavioral interpretation. |
| Actuation stress | For effector ordinal `j` and cognition tick `t`, activation is `0.65` when `(t + 7*j) mod 80 < 20`, otherwise `0.0`; apply the same schedule to all four bodies. | Draft schedule for the accepted fixed deterministic actuation condition. Modeled on the existing humanoid pulse test, but is not established as a safe envelope for every body. |
| Collision stress | Use `contact-garden-v1`, the `block` fixture at `(1.8, 1.0, 0.25)` with size `(0.5, 0.7, 0.5)`. Draft: spawn each body at `(1.8, 0, z)` with identity orientation and prescribed base velocity `(0, 2.0, 0) m/s`; zero all joint velocities/actuation. | Fixture is source-defined; exact pose/velocity is a draft proposal for the accepted prescribed-impact condition. Not yet validated to produce a comparable collision for every morphology. A non-contact run must be `not_testable`, not silently repositioned. |
| Re-embodiment | Exercise all six directed source/destination pairs among the four canonical bodies (`A→B` and `B→A` for each unordered pair). Preserve the same Symbiont checkpoint; instantiate the destination at its declared fresh-body initial state. | Six directed pairs are owner-accepted. Body-specific physical state is not assumed portable. Report identity continuity and physical initialization separately. |
| Friction | Perturb only the flat ground plane's `lateralFriction` from the existing ground baseline `0.95` to `0.855` and `1.045`; hold other material fields fixed. | Scope and ±10% arms are owner-accepted. The `+10%` value exceeds 1.0; verify it is accepted by the pinned simulator and is not clamped before any run. |
| Mass | Scale every positive-mass base/link segment in the selected body's generated model by `0.9`, `1.0`, or `1.1`; retain geometry and scale each associated principal inertia component by the same factor. | Scope and operation are owner-accepted. Harness must verify resulting mass/inertia values before execution; changes to code require separate authorization. |

The matrix therefore contains 44 arms and, with three seeds each run twice,
264 executions. This is the planned workload, not evidence that any arm has
been executed.

## 4. Required observations

Capture enough per-step state to assess the following for each arm:

- finite base positions, orientations, linear/angular velocities, joint states,
  applied actuator values, contact measurements, and energy/work fields;
- valid rigid transforms, including finite coordinates and a valid orientation;
- joint positions within the body's declared anatomical limits plus its
  declared solver tolerance, and velocities within the body's declared limits;
- contact count, penetration, contact forces, and any runtime safety/termination
  event;
- coherent physical state at checkpoint boundaries and after restore;
- the declared initial and final embodiment identities for re-embodiment cases.

Actuation and perturbation conditions must be deterministic and externally
specified. They must not adapt after observing a failure. Energy is required
to remain finite; this gate does not impose conservation or monotonicity on an
actively actuated, dissipative system.

## 5. Analysis and result vocabulary

Report every body/condition/arm/seed independently. Preserve the exact code
revision, simulator/library versions, seed, initial state/configuration,
parameter values, horizon, raw artifact paths, and observed maxima/minima.

Allowed outcomes are `pass`, `fail`, `not_testable`, and `inconclusive`.
Missing artifacts, unavailable optional dependencies, or an undefined metric
must not be counted as a pass. Do not replace a failing seed. Do not infer a
biological capability from a mechanical pass.

## 6. Owner-accepted candidate acceptance criteria and remaining review

The owner accepted the following candidate thresholds on 2026-10-03. They are
operational screening limits, not existing constitutional or biological
contracts. They become the protocol's pass/fail criteria only when recorded in
an explicitly frozen revision; acceptance here does not authorize execution:

| Metric | Candidate criterion | Status / rationale |
|---|---|---|
| Rigid transform | All coordinates and quaternion components finite; quaternion norm within `1e-6` of 1.0. | Owner-accepted candidate numerical-validity tolerance; confirm the emitted representation is measured correctly. |
| Contact count | No more than 100 simultaneous body-ground/fixture contact points for any one body. | Owner-accepted candidate explosion screen; not a universal physical or constitutional maximum. |
| Penetration | No contact penetration deeper than `0.02 m`. | Owner-accepted candidate geometry-tolerance screen; not a universal physical or constitutional maximum. |
| Normal force | No individual normal contact force above `10,000 N`. | Owner-accepted candidate explosion screen; not a universal physical or constitutional maximum. |
| Replay | Maximum absolute difference `<=1e-9` for numeric physical-state fields at matched ticks; identities and discrete fields exactly equal. | Owner-accepted same-host repeat tolerance; no cross-platform bit-exact claim. |
| Energy/work | Every recorded energy/work value finite. | Owner-accepted finiteness requirement; no conservation or monotonicity requirement. |

The following items still require exact confirmation before freeze:

| Item | Required before freeze |
|---|---|
| Collision comparability | Confirm that the fixed pose/velocity produces a collision in each body; otherwise specify a preregistered body-specific geometry/pose rule before freeze. |
| Friction validity | Verify simulator behavior for lateral friction `1.045`; do not accept silent clamping. |
| Mass implementation | Verify mass/inertia scaling is available without changing geometry or other model parameters. If not, stop for a design/code decision. |
| Replay procedure | Freeze artifact capture, same-host repeat environment, and exactly which physical fields participate in the `1e-9` comparison. |
| Run feasibility | Confirm the runner can instantiate all settings and preserve per-run manifests/artifacts without an unapproved code change. |

Use existing normative limits where they directly apply. A limit from one body
or test must not be generalized to other bodies without source evidence and
owner approval. In particular, the existing humanoid actuation test does not
by itself define acceptance thresholds for the other canonical morphologies.

## 7. Authorization and lifecycle

The owner approved the high-level campaign basis on 2026-10-03: three fixed
seeds with an identical replay, nominal and `+/-10%` friction/mass arms,
360-tick horizon, fixed deterministic actuation, prescribed impact, six
directed re-embodiment pairs, and the broad perturbation scopes. Exact schedule,
impact and replay-split details in section 3 remain draft proposals. Numeric
candidate acceptance thresholds in section 6 were accepted by the owner on
2026-10-03; they are not yet frozen. The design remains **Proposed**. No
confirmatory campaign, held-out run, code change, or organism change is
authorized by this document.

Once the owner resolves the freeze blockers, record the exact settings here,
update the design register, and obtain explicit approval to freeze before
execution. Publish results and deviations separately; revise this design only
through an explicit owner decision.
