# Sensory Causal Ablation

Tests causal contribution by comparing intact and ablated receptor paths.

Protocol: `perception.sensory-ablation`.

Run:

```bash
symbiont-lab experiment run experiments/perception/sensory-ablation/experiment.toml
```

The evaluator may characterize outputs after they exist, but target labels,
expected roles and acceptance criteria never enter the organism.

No `results.json` is committed until a real execution completes. A negative,
null or convergent outcome remains a valid result.
