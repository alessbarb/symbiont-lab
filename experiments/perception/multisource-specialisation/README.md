# Multisource Sensory Specialisation

Compares an endogenously formed multisource receptor with single-source and frozen controls.

Protocol: `perception.multisource-specialisation`.

Run:

```bash
symbiont-lab experiment run experiments/perception/multisource-specialisation/experiment.toml
```

The evaluator may characterize outputs after they exist, but target labels,
expected roles and acceptance criteria never enter the organism.

No `results.json` is committed until a real execution completes. A negative,
null or convergent outcome remains a valid result.
