# Opaque body-model reorganization after actuator damage

This experiment starts from a canonical replay checkpoint and creates two
matched continuations. The intact twin continues normally. In the damaged twin
the health of exactly one opaque actuator selected from the current replay
pattern is set to zero in the organism checkpoint before execution. No graph,
primitive statistic, objective, reward or semantic label is edited.

The apparatus observes only evaluator-side evidence: loss of delivery on the
damaged channel, divergence of opaque sensory trajectories, and changes in the
set of temporal primitive sequences after continued organism-owned babbling,
verification and learning.

`damaged_novel_primitives` counts primitive identities absent from the initial
checkpoint and `damaged_replayed_novel_primitives` restricts that evidence to
new chunks the damaged organism actually replays. `known_primitives_replayed_damaged`
records reuse of a pre-damage primitive in the changed body.
`model_changed_after_damage`
compares the complete opaque primitive signatures of the matched continuations.
The gate is deliberately strong: a physical perturbation alone is not called
adaptation unless the damaged organism changes its learned model, contains a
multi-effector chunk and reuses at least one newly discovered chunk.

This protocol does not yet establish long-horizon transfer to an unseen task,
explicit anatomy concepts, or multi-effector coordination beyond the temporal
chunks that the canonical learner discovers. Those require separate studies.


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
