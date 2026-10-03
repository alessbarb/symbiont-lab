# E5 — Somatic Correlation Trap

Preregistered falsification study for the inferred body boundary.

Run:

```bash
symbiont-lab experiment run experiments/embodiment/somatic-correlation-trap/experiment.toml
```

The protocol compares:
- one genuinely self-caused input;
- one genuine somatic-correlated input;
- one matched external-correlated input;
- one external independent control.

Primary gates:
- true somatic detection >= 0.70;
- external correlated assimilation <= 0.10;
- deterministic replay.

A failed H1 gate is a valid negative result. Do not tune
`InferredBodySchema`, thresholds, seeds or signal generation before the
first result is frozen under `research/`.


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
