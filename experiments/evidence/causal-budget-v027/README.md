# Causal evidence budget v0.27

This experiment unifies two mechanisms that had previously been studied separately:

1. **Causal attention allocation** chooses which events receive scarce additional inspection using only information available at decision time.
2. **Second-look evidence** provides one noisy synthetic auxiliary measurement after selection and updates the event probability.

The total evidence budget is fixed and identical across conditions. Directed selectors (`risk`, `novelty`, `risk_novelty`) are compared with a causal random baseline. Directed conditions additionally reserve exact exploration quotas of 0%, 5%, 10%, or 20% of the budget for unguided sampling.

The central question is not merely whether a selector finds more threats, but whether the complete **selection → evidence → posterior decision** loop improves population-level classification under equal cost.

Primary outcomes include final recall, precision, benign false-positive rate, Brier gain, net correction rate, evidence-selection recall, and stealth recall. Comparisons are paired by seed and world digest. Exploration conditions are compared both against random and against the same directed policy with zero exploration.

The selector runs before second-look evidence is generated. Sensor noise is deterministic per event, so changing a policy or budget cannot change the underlying synthetic world. Ground truth is used only by the laboratory evaluator and synthetic sensor generator, never as a selector input.

Run the canonical experiment with:

```bash
symbiont-lab experiment run experiments/evidence/causal-budget-v027/experiment.toml
```

This remains a simulation-only research protocol: no propagation, persistence, stealth/evasion, OS modification, or real endpoint access is introduced.


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
