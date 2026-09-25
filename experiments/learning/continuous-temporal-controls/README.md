# Continuous temporal causal controls

This protocol tests the sparse ESN + NLMS challenger against causal controls.

A continuous state evolves according to previous state, an opaque signed action
and bounded noise. Three conditions share the same target trajectory:

- causal action identity;
- shuffled action identity;
- no action input.

Training occurs only on the first 70% of the trajectory. During held-out
evaluation the reservoir continues to update its recurrent state, but the
readout is frozen.

The test asks whether action-conditioned temporal structure matters. It does
not assign ESN a motor role or promote it into resident cognition.


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
