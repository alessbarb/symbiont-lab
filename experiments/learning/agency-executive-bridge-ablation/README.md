# E2 — Executive bridge ablation

Agency Acquisition & Executive Action v1 (`docs/design/core/agency-acquisition-and-executive-action-v1.md`).

## Purpose

Preregistered protocol for `learning.agency-executive-bridge-ablation`.

## Hypothesis

Routing learned competences through a persistent ActionIntent changes effect
realization, action switching, prediction error and commitment failure relative
to readout/competence -> direct proposal; letting real intent outcomes modulate
future admission (Executive Outcome Learning v1) changes them further.

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

Executive Outcome Learning v1 comparison (arm with outcome learning vs the
same reconciled-intent arm without it): per testable seed, realized
commitments higher / equal / lower, plus mean effect realization rate,
energy per realized effect and switches per realized effect.  The result is
recorded as better, equal or worse without a post-hoc threshold.  Each arm
reports outcome-learning saturation (keys created/evicted, single-sample key
fraction, mean samples per key, history hit rate); if the history hit rate
over the horizon is below 0.10 or any key is evicted, the comparison is
reported as not a clean test of outcome learning.

Protocol v3 arms: `direct_proposal` (outcome learning disabled); `action_intent` (reconciled intent,
outcome learning disabled — the v2 intent arm); `action_intent_outcome_learning`
(reconciled intent with Executive Outcome Learning v1,
`docs/design/core/executive-outcome-learning-v1.md`). Seeds, warmup and horizon
are unchanged from v2.

Protocol v4 reruns the v3 arms and criteria unchanged with Executive Outcome
Learning v1.1, whose evidence is keyed by (competence, anticipated effect)
instead of (competence, anticipated effect, context); v3 was not a clean test
because the context key fragmented executive memory (spec §12-§14).

## Execution

```bash
symbiont-lab experiment run experiments/learning/agency-executive-bridge-ablation/experiment.toml
```

Not part of the default pytest loop; `tests/experiments` only checks the
mechanical protocol contract.

## Limits

Results are evidence bounded by this synthetic body, these seeds and budgets;
they do not by themselves demonstrate generalization.
