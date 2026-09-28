# FP-1 arm TM — time-matched baseline and multiplicity

Footprint Precision v1 (`docs/design/core/footprint-precision-v1.md`, §6).

## Purpose

One arm of FP-1: footprint precision and recall on the E8 body with membership arm TM (time-matched baseline and multiplicity). Same seeds, body and budget as FP-0; only `[ablation].membership` differs.

## Belongs here

The preregistered `experiment.toml` for this arm and this README.

## Does not belong here

Results, run artifacts or interpretation (runs go to `.symbiont/runs/`, the
reading goes to the spec), and pytest files (contracts live in
`tests/experiments/protocols/`).

## Criterion for creating a file

Only a new preregistered protocol version, committed before its runs.

## Success criteria

Preregistered in Footprint Precision v1 §6 (commit 6ae4c7bc): an arm
qualifies with pooled precision >= 0.80 at tick 3000, mean recall >= 0.42
and the E6 gate 3/3; among qualifying arms the highest precision is proposed
(ties: T, M, TM). No threshold changes after results.

## Execution

`symbiont-lab experiment run experiments/learning/footprint-precision-fp1-tm/experiment.toml`

## Limits

Synthetic body with evaluator-only ground truth; the organism never sees
the classification.
