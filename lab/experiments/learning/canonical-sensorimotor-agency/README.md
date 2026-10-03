# Opaque canonical sensorimotor agency discovery

## Protocol

This is a pre-control gate on the **canonical** Physics3D organism. The
organism starts newborn and uses its existing opaque motor-babbling constitution.
The laboratory only reads completed-tick telemetry. It supplies no semantic
actuator labels, anatomy, reward, target, locomotion objective, or evaluator
measurement to the organism.

The gate requires, for every independent seed:

1. a motor primitive generated from organism-owned exploration;
2. promotion to cognitive eligibility after the learner's independent replay;
3. at least one organism-owned verification/replay tick;
4. controllability above `0.002` and directional consistency at least `0.60`.

This is deliberately **not** a locomotion test. It tests whether the organism
can form an operational body model before being asked to walk.

## Result

Run on 2026-09-21 with seeds `101, 127, 149`, 64 organism ticks per seed and
one PyBullet substep per tick:

| seed | patterns | primitives | cognitive primitives | verification ticks | best controllability | best directional consistency |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 101 | 37 | 16 | 3 | 17 | 0.14472 | 1.00000 |
| 127 | 43 | 16 | 4 | 17 | 0.19334 | 1.00000 |
| 149 | 39 | 16 | 4 | 17 | 0.25459 | 1.00000 |

All three trials passed the pre-control gate (`3/3`). The first cognitive
primitive appeared at tick 11 in every seed. This validates an operational,
opaque sensorimotor-discovery capability in the current canonical runtime.

## Boundary of the result

The result does **not** validate a neural network, locomotion, semantic body
concepts, or goal-directed agency. It also does not prove that cognition can
select a useful primitive in a matched behavioral ablation. Those are separate
experiments. The existing physical intervention study remains relevant as an
apparatus-level causal control, while this protocol establishes that the
organism's own learner can generate and replay a body-dependent competence.


## Purpose

This README defines this location's scope within the experiment hierarchy.

## Belongs here

Protocols, configuration, documentation, and identifiable results from reproducible runs.

## Does not belong here

No pytest-collectable tests, production code, or final scientific interpretation.

## Criterion for creating a file

Add only a file that records a reproducible protocol element, an execution, or a result; mechanical contracts belong in `tests/experiments/`.

## Execution

Use the explicit command documented by the protocol or CLI; do not execute this folder through pytest.

## Limits

The contents are evidence bounded by the protocol and do not demonstrate generalization by themselves.
