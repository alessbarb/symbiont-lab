# Counterfactual intervention on an opaque motor primitive

## Protocol

Each newborn canonical Physics3D organism develops until it is actively
replaying a primitive that has already become cognitively eligible. The study
then saves the completed organism checkpoint and the aligned physical
checkpoint.

Three matched continuations are created from those same checkpoints:

1. normal replay A;
2. normal replay B, which controls determinism;
3. intervention replay, where only the physical effector corresponding to one
   opaque actuator in the current primitive is forced to zero.

The intervention does not edit the cognitive graph, sensorimotor learner,
primitive statistics, motivation, or action request. The changed sensory input
is the physical consequence of the counterfactual, not an evaluator-provided
label or reward.

The target is selected from the primitive's current opaque replay pattern by
maximum quantized activation. It is reported as an opaque ID and is not given
semantic meaning.

## Result

Run on 2026-09-21 with seeds `101, 127, 149`, 64 warmup ticks, 8 matched
continuation ticks and one PyBullet substep per tick:

| seed | checkpoint tick | target delivered ticks | mean sensory divergence | mean physical divergence | normal replay error |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 101 | 17 | 3 | 0.000567 | 0.000542 | 0.0 |
| 127 | 17 | 8 | 0.000323 | 0.000431 | 0.0 |
| 149 | 48 | 3 | 0.148238 | 0.000954 | 0.0 |

All three trials passed the preregistered gate (`3/3`). The result supports a
causal, reusable interpretation of the tested primitives: the same internal
replay from the same initial state is deterministic, while removing one
actually involved physical actuator changes both the opaque sensory trajectory
and the body trajectory.

## Boundary of the result

This is evidence for causal actuator involvement, not a claim that the
organism has an explicit concept such as “arm” or “walking”. It also does not
establish useful whole-body locomotion or long-horizon goal-directed control.
The intervention is one actuator per primitive and eight ticks long; broader
reusability requires repeated interventions across all primitive channels and
held-out body states.


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
