# D1 development

Vision Acquisition v1 (`docs/design/core/vision-acquisition-v1.md`, D1).

## Purpose

Temporal visual structure: arms A (acquisition) and B (Lab plasticity ablation) resume the same State X per seed in `vision-nursery-d1-v1` with the `anthropomorphic-v6-vision` body. Development seeds 101, 127, 149: runner engineering and horizon feasibility only.

## Belongs here

The preregistered `experiment.toml` and this README.

## Does not belong here

Results, run artifacts or interpretation (runs go to `.symbiont/runs/`, the reading goes to the spec), and pytest files (contracts live in `tests/experiments/protocols/`).

## Criterion for creating a file

Only a new preregistered protocol version, committed before its runs.

## Success criteria

None. Development runs never tune a criterion and are reported separately as development (§6).

## Execution

`symbiont-lab experiment run experiments/learning/vision-acquisition-d1-dev/experiment.toml` — strictly sequential, nothing else running (vision body ≈ 0.3–1 s/tick).

## Limits

Measures predictive structure over opaque visual receptors only; no object, persistence or self/external claim (D2/D3). The visual-target mapping is evaluator-side and never enters cognition.
