# E6 gate for BD-1 arm HIST

Binding Degradation v1 (`docs/design/core/binding-degradation-v1.md`, §3).

## Purpose

The factorized E6 release gate rerun with binding invalidation against the binding history, so HIST cannot be proposed if it breaks deliberate reuse closure (as the rest-based rule did).

## Belongs here

The preregistered `experiment.toml` for this arm and this README.

## Does not belong here

Results, run artifacts or interpretation (runs go to `.symbiont/runs/`, the
reading goes to the spec), and pytest files (contracts live in
`tests/experiments/protocols/`).

## Criterion for creating a file

Only a new preregistered protocol version, committed before its runs.

## Success criteria

The E6 gate unchanged on 3/3 seeds.

## Execution

`symbiont-lab experiment run experiments/learning/agency-acquisition-reuse-closure-binding-history/experiment.toml`

## Limits

Synthetic body with evaluator-only ground truth (a broken effector); the
organism never sees which bindings are truly degraded. Footprint membership
is the default in both arms (no combination with FP studies).
