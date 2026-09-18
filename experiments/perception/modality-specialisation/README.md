# Sensory Modality Specialisation

Characterizes functional niches of structurally different opaque modalities.

Protocol: `perception.modality-specialisation`.

Run:

```bash
symbiont-lab experiment run experiments/perception/modality-specialisation/experiment.toml
```

The evaluator may characterize outputs after they exist, but target labels,
expected roles and acceptance criteria never enter the organism.

No `results.json` is committed until a real execution completes. A negative,
null or convergent outcome remains a valid result.
