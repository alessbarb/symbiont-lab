# E5 — Intentional causal advantage

Agency Acquisition & Executive Action v1 (`docs/design/core/agency-acquisition-and-executive-action-v1.md`).

## Purpose

Preregistered protocol for `learning.agency-intentional-causal-advantage`.

## Hypothesis

Full ActionIntent with persistence and observed-effect reconciliation (C) is a
causal improvement over direct proposals (A) and over intents without real-effect
reconciliation (B), given the same body, state, experience and competences; and
using reconciled outcomes to modulate future admission (D, Executive Outcome
Learning v1) improves on C.

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
per realized effect for A, B, C and D on matched twins.  C vs B answers whether
reconciling real effects helps; D vs C answers whether using that
reconciliation for future admission helps.

Executive Outcome Learning v1 comparison (arm with outcome learning vs the
same reconciled-intent arm without it): per testable seed, realized
commitments higher / equal / lower, plus mean effect realization rate,
energy per realized effect and switches per realized effect.  The result is
recorded as better, equal or worse without a post-hoc threshold.  Each arm
reports outcome-learning saturation (keys created/evicted, single-sample key
fraction, mean samples per key, history hit rate); if the history hit rate
over the horizon is below 0.10 or any key is evicted, the comparison is
reported as not a clean test of outcome learning.

Protocol v3 arms: A direct proposals, outcome learning disabled; B persistent intent, unreconciled (no
outcome learning by construction); C reconciled intent, outcome learning
disabled (the v2 arm C); D reconciled intent with Executive Outcome Learning v1
(`docs/design/core/executive-outcome-learning-v1.md`). Seeds, warmup and
horizon are unchanged from v2.

## Execution

```bash
symbiont-lab experiment run experiments/learning/agency-intentional-causal-advantage/experiment.toml
```

Not part of the default pytest loop; `tests/experiments` only checks the
mechanical protocol contract.

## Limits

Results are evidence bounded by this synthetic body, these seeds and budgets;
they do not by themselves demonstrate generalization.
