# L7.5 — Replay marginal compute efficiency

L7.3 established that maximum replay outperforms minimum replay on identical
experience. L7.4 established a monotonic held-out loss curve across replay
pressure.

L7.5 asks the next question: **how much predictive improvement is obtained per
additional replay step?**

For each consecutive pressure interval the study computes:

```text
gain_per_step =
    (loss_before - loss_after) / additional_replay_steps
```

The study reuses the exact L7.4 matched design. It does not change the organism
or feed evaluator metrics back into learning.

Run:

```bash
symbiont-lab experiment run experiments/learning/replay-efficiency/experiment.toml
```

A diminishing-return result would justify the next engineering step: an
organism-owned stopping rule based on its own prediction improvement versus
compute/metabolic opportunity cost. The evaluator loss in this study may
characterize that frontier but must never become the organism-side stopping
signal.


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
