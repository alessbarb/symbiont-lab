# Adaptive sensory experiments

These experiments evaluate the post-freeze Adaptive Sensory System. Evaluator
labels, targets and success criteria never feed back into the organism.

```bash
symbiont-lab experiment run experiments/perception/identity-equivalence/experiment.toml
symbiont-lab experiment run experiments/perception/adaptive-delta-discovery/experiment.toml
symbiont-lab experiment run experiments/perception/temporal-scale-specialisation/experiment.toml
symbiont-lab experiment run experiments/perception/modality-specialisation/experiment.toml
symbiont-lab experiment run experiments/perception/sensory-duplication-divergence/experiment.toml
symbiont-lab experiment run experiments/perception/sensory-ablation/experiment.toml
symbiont-lab experiment run experiments/perception/multisource-specialisation/experiment.toml
symbiont-lab experiment run experiments/perception/same-world-phenotype-divergence/experiment.toml
```

Do not create or commit `results.json` before execution. Negative, null or
convergent outcomes are valid evidence.
