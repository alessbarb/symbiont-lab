# FP-3 arm BHB — block-replicated Benjamini-Hochberg

Footprint Precision v1 (`docs/design/core/footprint-precision-v1.md`, §12).

## Purpose

One arm of FP-3 on new seeds: footprint precision and recall on the E8 body with membership BHB (block-replicated Benjamini-Hochberg).

## Belongs here

The preregistered `experiment.toml` for this arm and this README.

## Does not belong here

Results, run artifacts or interpretation (runs go to `.symbiont/runs/`, the
reading goes to the spec), and pytest files (contracts live in
`tests/experiments/protocols/`).

## Criterion for creating a file

Only a new preregistered protocol version, committed before its runs.

## Success criteria

Preregistered in Footprint Precision v1 §12 (commit 5b510f31): an arm
qualifies with pooled precision >= 0.80 at tick 3000, mean recall >= 0.42
and the E6 gate 3/3; among qualifying arms the highest precision is
proposed (ties: BH, BHB). New seeds, never used by earlier studies.

## Execution

`symbiont-lab experiment run experiments/learning/footprint-precision-fp3-bhb/experiment.toml`

## Limits

Synthetic body with evaluator-only ground truth; the organism never sees
the classification. Binding invalidation is off (default).
