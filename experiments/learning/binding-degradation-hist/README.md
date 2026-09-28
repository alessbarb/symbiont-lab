# BD-1 arm HIST

Binding Degradation v1 (`docs/design/core/binding-degradation-v1.md`, §3).

## Purpose

One arm of BD-1: the E8 body loses actuator 0 at tick 2000; arm HIST (invalidation against the binding history).

## Belongs here

The preregistered `experiment.toml` for this arm and this README.

## Does not belong here

Results, run artifacts or interpretation (runs go to `.symbiont/runs/`, the
reading goes to the spec), and pytest files (contracts live in
`tests/experiments/protocols/`).

## Criterion for creating a file

Only a new preregistered protocol version, committed before its runs.

## Success criteria

Preregistered in Binding Degradation v1 §3 (commit e47c4042): HIST
qualifies with false invalidations <= 5% of at-risk bindings, true
detections >= 50% of truly degraded bindings (not assessable below 5),
spurious satisfactions no higher than OFF, and the E6 gate 3/3 with HIST.
Criterion 1 or 4 failing rejects HIST. No parameter changes after results.

## Execution

`symbiont-lab experiment run experiments/learning/binding-degradation-hist/experiment.toml`

## Limits

Synthetic body with evaluator-only ground truth (a broken effector); the
organism never sees which bindings are truly degraded. Footprint membership
is the default in both arms (no combination with FP studies).
