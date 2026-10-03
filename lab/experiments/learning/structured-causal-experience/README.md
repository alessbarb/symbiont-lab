# L7.9 — Structured causal experience

This gate compares two encodings of the same synthetic motor history.

Legacy:
- whole motor vector becomes one high-cardinality opaque action token;
- no reusable per-channel action structure.

Structured:
- one stable `action.motor.composite` marker;
- opaque per-channel requested/delivered classes remain in context;
- training and private validation optimize only causal outcome targets.

Both arms use the same seeds, causal dynamics, GRU family, 1M parameter ceiling,
48 replay-step ceiling and held-out promotion evaluation.

Run:

```bash
symbiont-lab experiment run experiments/learning/structured-causal-experience/experiment.toml
```


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
