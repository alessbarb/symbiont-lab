# L7.4 — Replay pressure dose-response

This study follows the positive L7.3 endpoint result. L7.3 established that the
maximum replay budget outperformed the minimum on the same causal experience,
but every treatment seed had replay pressure 1.0.

L7.4 therefore evaluates the *interior* of the pressure function.

Within each seed, the study freezes:

- causal experience;
- corpus and temporal holdout;
- tokenizer;
- architecture and objective;
- model seed;
- parameter ceiling.

It then evaluates pressures:

```text
0.00, 0.25, 0.50, 0.75, 1.00
```

using the exact L7.2 budget mapping.

Primary outcome: held-out predictive log loss.

Run:

```bash
symbiont-lab experiment run experiments/learning/replay-pressure-curve/experiment.toml
```

A positive result supports a dose-response interpretation for replay compute. A
non-monotonic result would indicate that the current replay-pressure mapping is
not yet justified, even though L7.3's endpoint comparison remains valid.


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
