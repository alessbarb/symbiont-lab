# E6 gate for FP-1 arm TM

Footprint Precision v1 (`docs/design/core/footprint-precision-v1.md`, §6).

## Purpose

The factorized E6 release gate rerun with footprint membership arm TM (time-matched baseline and multiplicity), so the arm cannot be proposed if it breaks deliberate reuse closure.

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

`symbiont-lab experiment run experiments/learning/agency-acquisition-reuse-closure-membership-tm/experiment.toml`

## Limits

Synthetic body with evaluator-only ground truth; the organism never sees
the classification.
