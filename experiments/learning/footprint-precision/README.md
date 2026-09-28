# FP-0 — Footprint membership against ground truth

Footprint Precision v1 (`docs/design/core/footprint-precision-v1.md`, §3).

## Purpose

Measure how precise footprint membership is in the high-dimensional E8 body
and which of three preregistered causes (zero-count quiet baseline, small
samples with sequential testing, baseline mismatch) explains the drift
members, to choose the next specification.

## Belongs here

The preregistered `experiment.toml` and this README. E8 body (16 actuators x
4 correlated receptors + 32 drifting), 10 seeds, 3000 ticks, factorized
effects on, snapshots at ticks 500-3000.

## Does not belong here

Results, run artifacts or interpretation (runs go to `.symbiont/runs/`, the
reading goes to the spec), and pytest files (contracts live in
`tests/experiments/protocols/`).

## Criterion for creating a file

Only a new preregistered protocol version, committed before its runs.

## Success criteria

Descriptive; the §3 decision rule selects H1, H2 or H3 from pooled drift and
cross members at tick 3000. Nothing is adopted by this study.

## Execution

`symbiont-lab experiment run experiments/learning/footprint-precision/experiment.toml`

## Limits

Synthetic body with evaluator-only ground truth; the organism never sees the
classification.
