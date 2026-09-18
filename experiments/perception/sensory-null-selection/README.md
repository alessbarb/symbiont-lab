# Sensory Null Selection

When driver and outcome are independent white noise, target-free predictive credit does not create persistent strong sensory specialisation.

Protocol: `perception.sensory-null-selection`.

Run:

```bash
symbiont-lab experiment run experiments/perception/sensory-null-selection/experiment.toml
```

No result is considered positive merely because a useful transform exists.
The organism must select or reject candidates from its own predictive evidence;
the evaluator inspects held-out function only after the choice exists.
