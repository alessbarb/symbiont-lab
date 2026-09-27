# E2 — Executive bridge ablation

Agency Acquisition & Executive Action v1 (`docs/design/core/agency-acquisition-and-executive-action-v1.md`).

## Purpose

Preregistered protocol for `learning.agency-executive-bridge-ablation`.

## Hypothesis

Routing learned competences through a persistent ActionIntent changes effect
realization, action switching, prediction error and commitment failure relative
to readout/competence -> direct proposal.

## Design

Newborn canonical `OrganismRuntime` subjects embodied in the opaque
`CausalBody` apparatus (`symbiont_lab.studies.learning.agency_acquisition_body`).
Ground truth — which outputs are physically consequential and how the mapping is
perturbed — stays evaluator-side and never reaches the organism. The Lab never
supplies competence ids, actuators or motor patterns. `[world].steps` is the
developmental tick budget; `[ablation]` holds protocol parameters.

## Success criteria

Matched twins from one acquired organism checkpoint and body state. Seeds that
never acquire an executable competence within the warmup budget are reported as
not testable. Report per-arm metrics and differences; no post-hoc threshold.

## Execution

```bash
symbiont-lab experiment run experiments/learning/agency-executive-bridge-ablation/experiment.toml
```

Not part of the default pytest loop; `tests/experiments` only checks the
mechanical protocol contract.

## Limits

Results are evidence bounded by this synthetic body, these seeds and budgets;
they do not by themselves demonstrate generalization.
