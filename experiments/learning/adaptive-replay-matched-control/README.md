# L7.3 — Adaptive replay matched control

This is the first causal study of the L7 replay mechanism.

For every seed, one organism generates a deterministic opaque causal history.
The organism then authors its normal L7.2 training plan. Treatment and control
receive exactly the same:

- causal transitions;
- training corpus and temporal holdout;
- tokenizer;
- GRU-v1 architecture;
- objective;
- parameter ceiling;
- model seed.

The only intervention is replay compute:

- **adaptive arm:** organism-authored L7.2 epochs/steps;
- **control arm:** same request clamped to 2 epochs / 12 steps.

The evaluator reads held-out outcome log loss and accuracy only after both arms
finish. These measurements never feed back into either organism or training
request.

Run:

```bash
symbiont-lab experiment run experiments/learning/adaptive-replay-matched-control/experiment.toml
```

Interpretation:

A positive result supports only the claim that additional organism-requested
replay compute extracts more predictive utility from the same causal
experience under this protocol. It does not by itself establish improved
embodied behavior, locomotion, agency, consciousness, or general intelligence.


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
