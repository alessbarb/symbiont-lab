# E1 — Yoked External Causation

Preregistered falsification study for the operational self/world boundary.

Run:

```bash
symbiont-lab experiment run experiments/embodiment/yoked-external-causation/experiment.toml
```

The protocol compares one genuine intervention-dependent channel with three
external controls: yoked, anti-causal and independent. The primary gates were
frozen before execution:

- mean agency false-positive rate <= 0.10;
- mean true-positive rate >= 0.70;
- deterministic replay.

A failed H1 gate is a valid scientific result. Do not tune `AgencyModel`,
thresholds, seeds or intervention schedules before the first result is frozen
under `research/`.

Normative preregistration:

`research/audits/current/2026-09-embodiment-self-boundary-falsification-v1.md`


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
