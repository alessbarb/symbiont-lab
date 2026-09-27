# E4 — Embodied causal intervention

Agency Acquisition & Executive Action v1 (`docs/design/core/agency-acquisition-and-executive-action-v1.md`).

## Purpose

Preregistered protocol for `learning.agency-embodied-causal-intervention`.

## Hypothesis

After acquisition, permuting outputs or breaking an effector must be revealed
by revision of controllability, agency, ActionDimensions, BodySchema and
affordances, relative to an unperturbed control twin.

## Design

Newborn canonical `OrganismRuntime` subjects embodied in the opaque
`CausalBody` apparatus (`symbiont_lab.studies.learning.agency_acquisition_body`).
Ground truth — which outputs are physically consequential and how the mapping is
perturbed — stays evaluator-side and never reaches the organism. The Lab never
supplies competence ids, actuators or motor patterns. `[world].steps` is the
developmental tick budget; `[ablation]` holds protocol parameters.

## Success criteria

Believed dimension->effect relations are split by apparatus ground truth into
those the perturbation invalidates (the effect involves a receptor the
dimension no longer drives) and those it leaves intact. Report per perturbed
condition the controllability and agency drop, residual controllability and
re-tested fraction of both sets, plus lost agentic dimensions, new dimensions,
body-schema revisions, affordance turnover and intent failures, each contrasted
with the normal twin on the same relation sets. Revision is condition-specific
when invalidated relations drop more in the perturbed twin than in the normal
twin while intact relations do not.

Protocol v3 replaced the v2 "dominant effect of any dimension touching a
perturbed output" relation set, which mixed invalidated and intact relations,
and reads the pre-perturbation state (including derived affordances, which are
never checkpointed) from the source organism rather than a freshly restored
twin.

## Execution

```bash
symbiont-lab experiment run experiments/learning/agency-embodied-causal-intervention/experiment.toml
```

Not part of the default pytest loop; `tests/experiments` only checks the
mechanical protocol contract.

## Limits

Results are evidence bounded by this synthetic body, these seeds and budgets;
they do not by themselves demonstrate generalization.
