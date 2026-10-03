# Sensory Regime Reversal

When the world changes from a fast-change regime to a slow-integrative regime, organism-side sensory preference changes from the previously useful receptor to the newly useful receptor without evaluator intervention.

Protocol: `perception.sensory-regime-reversal`.

Run:

```bash
symbiont-lab experiment run experiments/perception/sensory-regime-reversal/experiment.toml
```

No result is considered positive merely because a useful transform exists.
The organism must select or reject candidates from its own predictive evidence;
the evaluator inspects held-out function only after the choice exists.


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
