# E6 — Acquisition to deliberate reuse closure (release gate)

Agency Acquisition & Executive Action v1 (`docs/design/core/agency-acquisition-and-executive-action-v1.md`).

## Purpose

Preregistered protocol for `learning.agency-acquisition-reuse-closure`.

## Hypothesis

One fresh organism, never reset and never given a competence id, actuator or
motor pattern by the Lab, first acquires agency (attempts -> signatures ->
dimensions -> effects -> agency -> competence) and then deliberately reuses a
competence it discovered itself to produce the anticipated real effect.

## Design

Newborn canonical `OrganismRuntime` subjects embodied in the opaque
`CausalBody` apparatus (`symbiont_lab.studies.learning.agency_acquisition_body`).
Ground truth — which outputs are physically consequential and how the mapping is
perturbed — stays evaluator-side and never reaches the organism. The Lab never
supplies competence ids, actuators or motor patterns. `[world].steps` is the
developmental tick budget; `[ablation]` holds protocol parameters.

## Success criteria

Release gate: for every seed the milestones occur in developmental order, an
ActionIntent formed from an afforded, self-acquired competence is SATISFIED by
the observed effect, and the reused competence's authority is grounded in the
organism's own exploration evidence. The satisfied-intent trace is recorded.

## Execution

```bash
symbiont-lab experiment run experiments/learning/agency-acquisition-reuse-closure/experiment.toml
```

Not part of the default pytest loop; `tests/experiments` only checks the
mechanical protocol contract.

## Limits

Results are evidence bounded by this synthetic body, these seeds and budgets;
they do not by themselves demonstrate generalization.
