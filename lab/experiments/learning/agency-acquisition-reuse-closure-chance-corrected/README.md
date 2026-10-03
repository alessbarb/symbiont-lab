# E6 gate for E8 v3 arm AB

Factorized Effect Representation v1 (`docs/design/core/factorized-effect-representation-v1.md`, §16).

## Purpose

The E6 release gate (factorized effects) rerun with `reconciliation = "chance_corrected"`, so arm AB cannot be adopted if it breaks deliberate reuse closure (§16.3 criterion 3).

## Belongs here

The preregistered `experiment.toml` for this arm and this README. Seeds 101/127/149, 4-actuator `CausalBody`, 3000 ticks, as `agency-acquisition-reuse-closure-factorized`; only `[ablation].reconciliation` differs.

## Does not belong here

Results, run artifacts or interpretation (runs go to `.symbiont/runs/`, the
reading goes to §16 of the spec), and pytest files (contracts live in
`tests/experiments/protocols/`).

## Criterion for creating a file

Only a new preregistered protocol version, committed before its runs.

## Success criteria

The E6 gate unchanged on 3/3 seeds, with the satisfied competence traced to its pulses.

## Execution

`symbiont-lab experiment run experiments/learning/agency-acquisition-reuse-closure-chance-corrected/experiment.toml`

## Limits

A synthetic body with evaluator-only ground truth; the result does not by
itself establish behaviour on a physical body or the real host.
