# Autonomous Sensory Selection

Given a fixed candidate receptor set and no evaluator target feedback, organism-side predictive credit selects the receptor with best held-out functional information more often than preregistered frozen/random controls.

Protocol: `perception.autonomous-sensory-selection`.

Run:

```bash
symbiont-lab experiment run experiments/perception/autonomous-sensory-selection/experiment.toml
```

No result is considered positive merely because a useful transform exists.
The organism must select or reject candidates from its own predictive evidence;
the evaluator inspects held-out function only after the choice exists.
