# E1 — Agency acquisition ablation

Agency Acquisition & Executive Action v1 (`docs/design/core/agency-acquisition-and-executive-action-v1.md`).

## Purpose

Preregistered protocol for `learning.agency-acquisition-ablation`.

## Belongs here

Preregistered protocol configurations, manifests, and execution parameters for this study arm.

## Does not belong here

No unit tests, production code, or transient run artifacts.

## Criterion for creating a file

Add only files required for this reproducible protocol definition or its registered gates; mechanical test contracts belong in `tests/experiments/`.

## Hypothesis

Counterfactual (no-intervention and alternative-intervention) evidence and the
AgencyModel are both necessary for acquiring causally specific ActionDimensions
and grounding MotorCompetences in an opaque body with inert outputs.

## Design

Newborn canonical `OrganismRuntime` subjects embodied in the opaque
`CausalBody` apparatus (`symbiont_lab.studies.learning.agency_acquisition_body`).
Ground truth — which outputs are physically consequential and how the mapping is
perturbed — stays evaluator-side and never reaches the organism. The Lab never
supplies competence ids, actuators or motor patterns. `[world].steps` is the
developmental tick budget; `[ablation]` holds protocol parameters.

## Success criteria

Report, per arm and seed: ActionDimensions discovered, false-positive
dimensions (grounded only in physically inert outputs, evaluator ground truth),
mean causal specificity/advantage, competences acquired and reproducibility.
Effects are reported per seed without a post-hoc pass direction.

## Execution

```bash
symbiont-lab experiment run experiments/learning/agency-acquisition-ablation/experiment.toml
```

Not part of the default pytest loop; `tests/experiments` only checks the
mechanical protocol contract.

## Limits

Results are evidence bounded by this synthetic body, these seeds and budgets;
they do not by themselves demonstrate generalization.
