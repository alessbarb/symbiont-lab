# L7.6 — Internal learning-progress validity

This study validates the signal that the organism is allowed to use for replay
stopping.

For each replay dose, the trainer exposes two strictly separated measurements:

- **private validation loss** — computed from the organism's own observed causal
  experience reserved from replay updates; this may be returned to the organism;
- **evaluator test loss** — computed from the untouched test split and never
  exposed to the organism.

The study asks whether *changes* in the private validation loss predict changes
in evaluator test loss across replay doses.

Run:

```bash
symbiont-lab experiment run experiments/learning/internal-learning-progress/experiment.toml
```

A positive result licenses private validation progress as an internal stopping
signal. It does not license exposing test loss or evaluator decisions.


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
