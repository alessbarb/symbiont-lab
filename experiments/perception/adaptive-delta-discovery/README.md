# Adaptive Delta Discovery

Asks whether bounded receptor development exposes useful temporal change without evaluator target feedback.

Protocol: `perception.adaptive-delta-discovery`.

Run:

```bash
symbiont-lab experiment run experiments/perception/adaptive-delta-discovery/experiment.toml
```

The evaluator may characterize outputs after they exist, but target labels,
expected roles and acceptance criteria never enter the organism.

No `results.json` is committed until a real execution completes. A negative,
null or convergent outcome remains a valid result.
