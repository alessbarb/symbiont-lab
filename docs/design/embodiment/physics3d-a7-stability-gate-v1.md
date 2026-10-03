---
id: design.embodiment.physics3d-a7-stability-gate-v1
title: "Physics3D A7 Stability Gate V1"
document_type: design
domain: embodiment
status: proposed
canonical: false
implementation_status: not_started
migrated_on: 2026-10-03
last_reviewed: null
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

## 3. Required observations

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

## 4. Analysis and result vocabulary

Report every body/condition/arm/seed independently. Preserve the exact code
revision, simulator/library versions, seed, initial state/configuration,
parameter values, horizon, raw artifact paths, and observed maxima/minima.

Allowed outcomes are `pass`, `fail`, `not_testable`, and `inconclusive`.
Missing artifacts, unavailable optional dependencies, or an undefined metric
must not be counted as a pass. Do not replace a failing seed. Do not infer a
biological capability from a mechanical pass.

## 5. Freeze blockers

This proposal is not executable until the owner approves a complete parameter
table that fixes the currently unspecified items below:

| Item | Required before freeze |
|---|---|
| Horizon and solver configuration | Exact simulated duration and solver/substep settings for each condition. |
| Idle and actuation inputs | Exact initial state and per-step input schedule, including amplitudes and phases. |
| Collision fixture | Exact obstacle/body placement, collision geometry, and impact input or initial velocity. |
| Checkpoint/restore | Exact checkpoint tick, restore procedure, continuation horizon, and comparison tolerance. |
| Re-embodiment | Exact source/destination body pairings and physical initialization procedure. |
| Friction baseline | Exact surface/body friction field to perturb and its source value; confirm the `+/-10%` operation respects valid ranges. |
| Mass baseline | Exact body/link mass scope to perturb; confirm the `+/-10%` operation preserves valid inertial properties. |
| Contact/transform limits | Explicit numeric limits for contact explosion, penetration, and rigid-transform validity where no existing normative limit applies. |
| Energy and numerical tolerances | Explicit criteria beyond finiteness where needed; do not infer a conserved-energy contract. |

Use existing normative limits where they directly apply. A limit from one body
or test must not be generalized to other bodies without source evidence and
owner approval. In particular, the existing humanoid actuation test does not
by itself define acceptance thresholds for the other canonical morphologies.

## 6. Authorization and lifecycle

The user approved the campaign basis on 2026-10-03: three fixed seeds with an
identical replay, nominal and `+/-10%` friction/mass arms, and existing
declared tolerances where applicable. This approval does not fill the freeze
blockers above. The design remains **Proposed** and no confirmatory campaign,
held-out run, code change, or organism change is authorized by this document.

Once the owner resolves the freeze blockers, record the exact settings here,
update the design register, and obtain explicit approval to freeze before
execution. Publish results and deviations separately; revise this design only
through an explicit owner decision.
