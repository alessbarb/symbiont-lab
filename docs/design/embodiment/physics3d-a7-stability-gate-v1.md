---
id: design.embodiment.physics3d-a7-stability-gate-v1
title: "Physics3D A7 Stability Gate V1"
document_type: design
domain: embodiment
status: approved
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

## 2. Campaign matrix

Exercise every canonical body in each of these seven A7 condition categories:

1. Idle stability.
2. Actuation stress.
3. Collision stress.
4. Checkpoint and restore.
5. Re-embodiment.
6. Friction perturbation.
7. Mass perturbation.

Idle, actuation, collision, and checkpoint/restore each have one declared
condition per body (16 arms total). To meet the owner's requested 264-run
scope, re-embodiment uses this balanced directed cycle (four transitions):
`anthropomorphic-v6 → anthropomorphic-v6-vision → crawler-v1 → asymmetric-v1
→ anthropomorphic-v6`. Each canonical body occurs exactly once as source and
once as destination. This supersedes the earlier all-pairs proposal; it does
not provide pairwise coverage of all morphologies.
Friction and mass each have three arms per body: nominal, `-10%`, and `+10%`
relative to the declared baseline (24 arms total). The full matrix therefore
contains 44 parameter arms before seed replication.
Perturbations must affect only the named parameter; other settings remain
fixed.

For each parameter arm, the seed set is `[42, 43, 44]`. Repeat each
seed once with the same initial state and conditions to check deterministic
replay. The seed set is a mechanical reproducibility sample, not a population
sample and not evidence that all seeds behave alike.

## 3. Approved condition settings

The owner accepted the exact conditions and settings below on 2026-10-03.
These require a separately frozen revision before campaign execution.

| Condition | Proposed fixed setting | Provenance / limitation |
|---|---|---|
| Runtime | `time_step=1/240 s`, 10 physics substeps per cognition tick, gravity `(0, 0, -9.81) m/s^2`, 120 solver iterations, ERP `0.8`, residual threshold `1e-9`. | Existing Physics3D runtime/solver defaults; record the actual PyBullet version and effective configuration in every run. |
| Horizon | 360 cognition ticks per condition; proposed checkpoint/replay split at tick 180, then continue for 180 ticks. | The 360-tick horizon is owner-accepted; split tick remains a concrete draft setting. Not a normative stability limit. The existing 360-step humanoid test has different substeps and does not validate this horizon for all bodies. |
| Initial state | Fresh body at its descriptor's declared spawn height, origin `(0,0,z)`, identity orientation, zero base velocity and zero joint state; fixed flat ground except for collision stress. | Draft initialization. Must be instantiated from the same pinned body/runtime revision for paired replays. |
| Idle | All effector channels receive zero activation for all 360 ticks. | Draft implementation of the accepted idle condition; no behavioral interpretation. |
| Actuation stress | For effector ordinal `j` and cognition tick `t`, activation is `0.65` when `(t + 7*j) mod 80 < 20`, otherwise `0.0`; apply the same schedule to all four bodies. | Draft schedule for the accepted fixed deterministic actuation condition. Modeled on the existing humanoid pulse test, but is not established as a safe envelope for every body. |
| Collision stress | Use `contact-garden-v1`, the `block` fixture at `(1.8, 1.0, 0.25)` with size `(0.5, 0.7, 0.5)`. Draft: spawn each body at `(1.8, 0, z)` with identity orientation and prescribed base velocity `(0, 2.0, 0) m/s`; zero all joint velocities/actuation. | Fixture is source-defined; exact pose/velocity is a draft proposal for the accepted prescribed-impact condition. Not yet validated to produce a comparable collision for every morphology. A non-contact run must be `not_testable`, not silently repositioned. |
| Re-embodiment | Exercise the four transitions in the balanced directed cycle specified in §2. Preserve the same Symbiont checkpoint; instantiate the destination at its declared fresh-body initial state. | The 264-run scope supersedes the earlier all-pairs proposal. The selected cycle gives each body one incoming and one outgoing transition, but does not assess omitted transitions. Body-specific physical state is not assumed portable. Report identity continuity and physical initialization separately. |
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

## 6. Owner-accepted candidate acceptance criteria

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

The owner accepted the exact proposed settings and the bounded probes below on
2026-10-03. The protocol remains un-frozen pending runner validation.

## 7. Feasibility review and execution artifacts

A bounded source/probe review on 2026-10-03 established the following:

- `PyBulletEmbodimentRuntime.step()` returns per-tick metrics. With
  `capture_physics_trace=True`, raw substeps include base pose/orientation,
  linear/angular velocity, joint position/velocity/commanded torque, and
  contacts. Tick records include work/energy, contact maxima/counts, and
  termination-related state.
- `checkpoint(advance_lineage=False)` and `physical_checkpoint()` expose
  organism and physical-body checkpoint payloads. These are building blocks,
  but A7 checkpoint/replay pair semantics still need runner-level tests.
- Telemetry v4 already emits per-run manifests with seed, timing, effective
  configuration, software identity, end tick and a SHA-256 integrity chain.
  It does not capture A7 arm/outcome, replay-comparison results, nor a campaign
  index.
- No A7 runner exists in `scripts/`. Existing APIs make a headless runner
  feasible without changing organism code, but new orchestration code and
  tests are required. Runner feasibility is therefore **conditional**, not
  validated, and blocks protocol freeze.

The runner must produce one immutable directory per execution, keyed by
`body/condition/arm/seed/repeat`. Each directory must contain a manifest
(repository commit, Python/PyBullet/package versions, condition and arm,
configuration, seed, initial state, horizon, repeat and outcome), raw per-tick
records and physics substeps, checkpoint/body-state artifacts where relevant,
a validation summary with observed extrema and criterion results, and SHA-256
hashes for every artifact. A campaign index must enumerate all 264 planned
executions and reference each manifest. Missing artifacts are `inconclusive`,
never `pass`.

Replay is same-host and uses the same revision, software/runtime versions,
seed, initial state and settings. At matched cognition ticks compare base
position/orientation and velocities; ordered joint position/velocity/commanded
torque; contacts (body/link IDs, positions, normal, distance, normal force,
lateral friction); actuator work/energy; contact counts/maxima. Maximum
absolute numeric difference is `<=1e-9`; identities and discrete fields must
match exactly. Canonicalize contact order by IDs and numeric coordinates.
Non-finite values fail before tolerance comparison. Record host and the exact
field list; make no cross-platform determinism claim.

The DIRECT-mode feasibility probe used PyBullet 3.2.7 and the current generated
apparatus/fixture. It observed friction `1.045` read back exactly after
`changeDynamics`, and first fixture contact at step 78 for both humanoid
variants, 65 for crawler and 73 for asymmetric. It did not run organism ticks,
campaign arms, seeds, or the 360-tick horizon; contact occurrence does not
establish comparable impact severity.

Remaining prerequisite before freeze:

| Item | Required before freeze |
|---|---|
| Runner implementation and validation | Implement the external runner, artifact contract, mass/inertia verification and replay/checkpoint tests; verify complete manifests/artifacts before campaign launch. No organism change is permitted. |

Use existing normative limits where they directly apply. A limit from one body
or test must not be generalized to other bodies without source evidence and
owner approval. In particular, the existing humanoid actuation test does not
by itself define acceptance thresholds for the other canonical morphologies.

## 8. Authorization and lifecycle

The owner approved the concrete protocol and acceptance criteria on 2026-10-03.
The design is **Approved**, not **Frozen**; runner implementation/validation is
the remaining prerequisite. No campaign, held-out run, or organism change is
authorized. After runner tests and artifact validation pass, obtain explicit
owner freeze confirmation before launching the campaign. Publish results and
deviations separately; revise this design only through an explicit owner
decision.
