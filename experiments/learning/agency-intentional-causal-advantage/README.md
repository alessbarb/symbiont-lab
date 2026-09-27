# E5 — Intentional causal advantage

Agency Acquisition & Executive Action v1 (`docs/design/core/agency-acquisition-and-executive-action-v1.md`).

## Purpose

Preregistered protocol for `learning.agency-intentional-causal-advantage`.

## Hypothesis

Full ActionIntent with persistence and observed-effect reconciliation (C) is a
causal improvement over direct proposals (A) and over intents without real-effect
reconciliation (B), given the same body, state, experience and competences.

## Design

Newborn canonical `OrganismRuntime` subjects embodied in the opaque
`CausalBody` apparatus (`symbiont_lab.studies.learning.agency_acquisition_body`).
Ground truth — which outputs are physically consequential and how the mapping is
perturbed — stays evaluator-side and never reaches the organism. The Lab never
supplies competence ids, actuators or motor patterns. `[world].steps` is the
developmental tick budget; `[ablation]` holds protocol parameters.

## Success criteria

Report effect realization rate, switches per successful effect, prediction
error, failed commitments, mean intent duration, intent satisfaction and energy
per realized effect for A, B and C on matched twins.

## Execution

```bash
symbiont-lab experiment run experiments/learning/agency-intentional-causal-advantage/experiment.toml
```

Not part of the default pytest loop; `tests/experiments` only checks the
mechanical protocol contract.

## Limits

Results are evidence bounded by this synthetic body, these seeds and budgets;
they do not by themselves demonstrate generalization.
