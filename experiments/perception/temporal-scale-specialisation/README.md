# Temporal Scale Specialisation

Measures whether receptors over one source occupy distinct fast and slow temporal niches.

Protocol: `perception.temporal-scale-specialisation`.

Run:

```bash
symbiont-lab experiment run experiments/perception/temporal-scale-specialisation/experiment.toml
```

The evaluator may characterize outputs after they exist, but target labels,
expected roles and acceptance criteria never enter the organism.

No `results.json` is committed until a real execution completes. A negative,
null or convergent outcome remains a valid result.
