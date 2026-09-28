# E8 — High-dimensional acquisition

Factorized Effect Representation v1
(`docs/design/core/factorized-effect-representation-v1.md`, §10).

## Purpose

Preregistered protocol for `learning.agency-high-dimensional-acquisition`.
The owner's Physics3D organism never formed an intent because whole-state
effects do not recur in a 107-receptor body (agency audit §0.1). E8
reproduces that regime in the deterministic synthetic apparatus.

## Belongs here

Preregistered protocol configurations, manifests, and execution parameters for this study arm.

## Does not belong here

No unit tests, production code, or transient run artifacts.

## Criterion for creating a file

Add only files required for this reproducible protocol definition or its registered gates; mechanical test contracts belong in `tests/experiments/`.

## Hypothesis

In a body whose outputs drive several correlated receptors and whose other
receptors drift on their own, the acquisition -> competence -> binding ->
intent chain engages only if effects recur whenever the same consequence
recurs.

## Design

`CausalBody(actuator_count=16, receptors_per_actuator=4,
drifting_receptor_count=32)`: each output drives four opaque receptors with
decreasing gain, 32 receptors drift independently of action, plus the
distractor (97 receptors). A newborn canonical runtime develops for
`[world].steps` ticks. Nothing about the body reaches the organism.

## Success criteria

Report effect recurrence, dimensions, competences with an effect, executable
competences, bindings, intents terminated and satisfied and the
outcome-learning history hit rate, per seed and summarized. Arm v1
(whole-state identity) runs on the last commit before the factorized
representation; arm v2 on the implementation commit; same seeds and body. No
post-hoc threshold.

Protocol v2 is arm v2: `[ablation].factorized_effects = true` (footprint
grounding with causal probing), same seeds, body and budget as the v1 run;
it additionally reports `footprints` and `footprint_competences`.

## Execution

```bash
symbiont-lab experiment run experiments/learning/agency-high-dimensional-acquisition/experiment.toml
```

Not part of the default pytest loop; `tests/experiments` only checks the
mechanical protocol contract.

## Limits

A synthetic stand-in for a physical body: correlation and drift are
simplified. The Physics3D acceptance run in the specification remains the
real-body check.

## Results

**Arm v1 — whole-state identity** (`20260927T142244Z-learning-agency-high-dimensional-acquisition-38429ca-add9`,
commit `38429ca`, before any factorized code; 10 seeds, 3000 ticks):
the EffectSpace saturates at 512 in every seed; ~1300 distinct effects in
~2200 effectful attempts, only 36% of effectful evidence recurring (support
>= 4); 21.4 action dimensions but 0.1 agentic; 1.9 competences, 1.9 bindings
(0 in two seeds); 95 intents terminated but 1.2 satisfied on average (0 in
seven seeds, 10 in seed 257). The synthetic body reproduces the Physics3D
failure pattern in a milder form. Arm v2 runs on the implementation commit.
