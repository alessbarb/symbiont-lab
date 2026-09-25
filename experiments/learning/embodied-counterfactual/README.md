# Embodied frozen counterfactual

This protocol evaluates a fixed set of opaque one-lag predictors against
paired Physics3D replays. Predictors are fitted only on the baseline prefix,
then frozen. The apparatus repeats the same action sequence from the same
settled state and zeros one opaque effector after the intervention tick. No
candidate is selected using the intervention suffix and no result enters
`symbiont`.

The implementation is in
`symbiont_lab.studies.learning.embodied_counterfactual`:

```python
run_embodied_counterfactual(
    seeds=(101, 127, 149),
    ticks=128,
    intervention_tick=48,
    target_effectors=(0, 7, 14, 21),
    target_receptors=(0, 7, 14, 21),
    physics_substeps_per_tick=2,
)
```

The candidate set is the fixed Cartesian product of the four selected opaque
effectors and four selected opaque receptors: 16 candidates per intervention.
The evaluator reports the normal prediction loss and the mean observed and
predicted intervention deltas. It intentionally does not convert these values
into an organism reward or motor command.

## First run

Configuration: seeds `101,127,149`, 128 ticks, intervention at tick `48`, 2
physics substeps, four effectors and four receptors. The intervention suffix
results were:

| seed | effector | observed delta | predicted delta | absolute error |
|---:|---:|---:|---:|---:|
| 101 | 0  | +0.001015 | -0.016940 | 0.017958 |
| 101 | 7  | +0.033068 | -0.020462 | 0.070395 |
| 101 | 14 | -0.010662 | -0.021113 | 0.040562 |
| 101 | 21 | +0.031412 | -0.015950 | 0.048224 |
| 127 | 0  | -0.001489 | -0.040169 | 0.045605 |
| 127 | 7  | +0.044829 | -0.024847 | 0.069955 |
| 127 | 14 | -0.017648 | -0.016635 | 0.025459 |
| 127 | 21 | -0.001375 | -0.020152 | 0.022546 |
| 149 | 0  | -0.000899 | -0.033410 | 0.036167 |
| 149 | 7  | +0.030737 | -0.018416 | 0.052441 |
| 149 | 14 | -0.044325 | -0.023351 | 0.046446 |
| 149 | 21 | +0.039823 | -0.033981 | 0.099382 |

The fixed one-lag predictor did not reproduce the direction or magnitude of
the intervention response. This is a negative result for this model and
protocol. It does not contradict the separate apparatus finding that physical
interventions alter opaque receptor trajectories; it shows that the current
frozen predictor does not explain those changes.

## Decision gate

The next experiment must not add model capacity yet. Before trying a recurrent
network again, the protocol needs a better state representation and an
explicit null model for intervention deltas. The predictor remains
shadow-only, and no canonical Symbiont integration is justified.


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
