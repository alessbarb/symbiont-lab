# Neutral temporal mechanism challenge

This preregistration reuses the established organism-private temporal corpus and
held-out outcome targets while removing the assumption that GRU/Transformer are
the only serious temporal mechanisms.

The protocol now reports:

- GRU-v1;
- Transformer-v1;
- stationary variable-order context model;
- decayed variable-order context model.

The context challengers are intentionally named VOMM rather than CTW: this
implementation does not claim exact Context Tree Weighting. Exact CTW/ACTW is a
future challenger only if its alphabet treatment and resource accounting can be
implemented without methodological shortcuts.

Run:

```bash
symbiont-lab experiment run experiments/learning/temporal-mechanism-challenge/experiment.toml
```

No mechanism is promoted into organism cognition from this study. It is an
external comparative falsification gate. ESN is evaluated separately on
continuous streams because forcing continuous sensorimotor values through this
token corpus would bias the comparison toward the existing SLM representation.


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
