# Adaptive sensory experiments

These experiments evaluate the post-freeze Adaptive Sensory System. Evaluator
labels, targets and success criteria never feed back into the organism.

Protocols 01–08 characterize the v1 sensory substrate. Protocols 09–12 are the
autonomous-selection phase added after the frozen multisource control showed
that useful transforms can exist without being learned or selected.

```bash
symbiont-lab experiment run experiments/perception/identity-equivalence/experiment.toml
symbiont-lab experiment run experiments/perception/adaptive-delta-discovery/experiment.toml
symbiont-lab experiment run experiments/perception/temporal-scale-specialisation/experiment.toml
symbiont-lab experiment run experiments/perception/modality-specialisation/experiment.toml
symbiont-lab experiment run experiments/perception/sensory-duplication-divergence/experiment.toml
symbiont-lab experiment run experiments/perception/sensory-ablation/experiment.toml
symbiont-lab experiment run experiments/perception/multisource-specialisation/experiment.toml
symbiont-lab experiment run experiments/perception/same-world-phenotype-divergence/experiment.toml
symbiont-lab experiment run experiments/perception/autonomous-sensory-selection/experiment.toml
symbiont-lab experiment run experiments/perception/sensory-regime-reversal/experiment.toml
symbiont-lab experiment run experiments/perception/sensory-null-selection/experiment.toml
symbiont-lab experiment run experiments/perception/experience-conditioned-phenotype/experiment.toml
```

Do not create or commit `results.json` before execution. Negative, null or
convergent outcomes are valid evidence.


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
