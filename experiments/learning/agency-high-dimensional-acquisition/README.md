# E8 — High-dimensional acquisition

Factorized Effect Representation v1
(`docs/design/core/factorized-effect-representation-v1.md`, §10).

## Purpose

Preregistered protocol for `learning.agency-high-dimensional-acquisition`.
The owner's Physics3D organism never formed an intent because whole-state
effects do not recur in a 107-receptor body (agency audit §0.1). E8
reproduces that regime in the deterministic synthetic apparatus.

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
