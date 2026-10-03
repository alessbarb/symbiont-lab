# Embodied intervention

This protocol follows the failed predictive shadow test with a narrower causal
question. A deterministic opaque effector sequence is replayed from the same
settled physical state. From tick 48 onward, one opaque effector slot is zeroed
in the intervention replay. A second unmodified replay measures apparatus
determinism. No organism runtime or neural controller is involved.

The gate is:

- the unmodified replay must be deterministic;
- every tested opaque effector intervention must produce mean post-intervention
  receptor divergence above `1e-4`.

Run used seeds `101,127,149`, 128 ticks, 2 physics substeps and opaque slots
`0,7,14,21`.

Result:

```text
replay_deterministic = true
all_interventions_detectable = true
mean_post_intervention_divergence = 0.0259195
```

All 12 seed/slot interventions were detectable. Mean divergences by seed were:

```text
101: 0.001264, 0.029911, 0.037813, 0.010285
127: 0.018616, 0.022566, 0.023998, 0.018855
149: 0.035476, 0.029341, 0.034551, 0.048356
```

This validates that the physical opaque interface contains action-dependent
causal signal. It does not validate a neural predictor or justify integration:
the previous prediction gate remains failed. The next valid test is to train a
shadow predictor on this stronger intervention regime, still without motor
output, and require held-out counterfactual discrimination.


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
