# E3 — Intent persistence

Agency Acquisition & Executive Action v1 (`docs/design/core/agency-acquisition-and-executive-action-v1.md`).

## Purpose

Preregistered protocol for `learning.agency-intent-persistence`.

## Hypothesis

A persistent ActionIntent yields less movement fragmentation and fewer
commitment interruptions than re-deciding every tick.

## Design

Newborn canonical `OrganismRuntime` subjects embodied in the opaque
`CausalBody` apparatus (`symbiont_lab.studies.learning.agency_acquisition_body`).
Ground truth — which outputs are physically consequential and how the mapping is
perturbed — stays evaluator-side and never reaches the organism. The Lab never
supplies competence ids, actuators or motor patterns. `[world].steps` is the
developmental tick budget; `[ablation]` holds protocol parameters.

## Success criteria

Matched twins; report successful effect realization, fragmentation (mean
competence-commitment ticks, switches), interruptions, controller completion and
energy per arm and seed.

## Execution

```bash
symbiont-lab experiment run experiments/learning/agency-intent-persistence/experiment.toml
```

Not part of the default pytest loop; `tests/experiments` only checks the
mechanical protocol contract.

## Limits

Results are evidence bounded by this synthetic body, these seeds and budgets;
they do not by themselves demonstrate generalization.
