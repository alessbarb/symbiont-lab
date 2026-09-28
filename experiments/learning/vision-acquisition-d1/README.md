# D1 held-out

Vision Acquisition v1 (`docs/design/core/vision-acquisition-v1.md`, D1).

## Purpose

Temporal visual structure: arms A (acquisition) and B (Lab plasticity ablation) resume the same State X per seed in `vision-nursery-d1-v1` with the `anthropomorphic-v6-vision` body. Held-out seeds 613, 617, 619, each run once.

## Belongs here

The preregistered `experiment.toml` and this README.

## Does not belong here

Results, run artifacts or interpretation (runs go to `.symbiont/runs/`, the reading goes to the spec), and pytest files (contracts live in `tests/experiments/protocols/`).

## Criterion for creating a file

Only a new preregistered protocol version, committed before its runs.

## Success criteria

Preregistered in Vision Acquisition v1 §7: on every assessable held-out seed (>= 8 visual targets with predictors in A; D1 needs >= 2 assessable seeds) arm A beats persistence and running-mean baselines (median prequential Huber gain > 0), no visual predictors existed at X, and arm B either lacks >= 8 predicted visual targets or gains less than A. Criterion 2 or 3 failing rejects D1. Runs only after owner approval of the criteria; no parameter changes after results.

## Execution

`symbiont-lab experiment run experiments/learning/vision-acquisition-d1/experiment.toml` — strictly sequential, nothing else running (vision body ≈ 0.3–1 s/tick).

## Limits

Measures predictive structure over opaque visual receptors only; no object, persistence or self/external claim (D2/D3). The visual-target mapping is evaluator-side and never enters cognition.
