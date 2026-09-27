# E8 v3 arm R (current recall reconciliation)

Factorized Effect Representation v1 (`docs/design/core/factorized-effect-representation-v1.md`, §16).

## Purpose

One arm of the preregistered E8 v3 comparison of intent reconciliation rules in the high-dimensional body.

## Belongs here

The preregistered `experiment.toml` for this arm and this README. E8 body (16 actuators x 4 correlated receptors + 32 drifting), seeds 101-257 (10), 3000 ticks, factorized effects on, `reconciliation = "recall"`; both arms run on one commit and differ only in this field.

## Does not belong here

Results, run artifacts or interpretation (runs go to `.symbiont/runs/`, the
reading goes to §16 of the spec), and pytest files (contracts live in
`tests/experiments/protocols/`).

## Criterion for creating a file

Only a new preregistered protocol version, committed before its runs.

## Success criteria

Evaluated jointly across arms R and AB and the E6 gate, exactly as fixed in §16.3 before any run: improvement (AB >= 2x R satisfied; higher satisfied/terminated in >= 7/10 seeds), safety (spurious satisfactions <= 10% of AB satisfied, else AB rejected) and the E6 gate 3/3.

## Execution

`symbiont-lab experiment run experiments/learning/agency-intent-reconciliation-r/experiment.toml`

## Limits

A synthetic body with evaluator-only ground truth; the result does not by
itself establish behaviour on a physical body or the real host.
