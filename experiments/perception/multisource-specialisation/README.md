# Multisource Sensory Specialisation

Compares an endogenously formed multisource receptor with single-source and frozen controls.

Protocol: `perception.multisource-specialisation`.

Run:

```bash
symbiont-lab experiment run experiments/perception/multisource-specialisation/experiment.toml
```

The evaluator may characterize outputs after they exist, but target labels,
expected roles and acceptance criteria never enter the organism.

No `results.json` is committed until a real execution completes. A negative,
null or convergent outcome remains a valid result.


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
