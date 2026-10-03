# FP-2 arm BH — Benjamini-Hochberg membership at q = 0.05

Footprint Precision v1 (`docs/design/core/footprint-precision-v1.md`, §9).

## Purpose

One arm of FP-2 on new seeds: footprint precision and recall on the E8 body with membership BH (Benjamini-Hochberg membership at q = 0.05). Binding invalidation is off (default).

## Belongs here

The preregistered `experiment.toml` for this arm and this README.

## Does not belong here

Results, run artifacts or interpretation (runs go to `.symbiont/runs/`, the
reading goes to the spec), and pytest files (contracts live in
`tests/experiments/protocols/`).

## Criterion for creating a file

Only a new preregistered protocol version, committed before its runs.

## Success criteria

Preregistered in Footprint Precision v1 §9 (commit e47c4042): an arm
qualifies with pooled precision >= 0.80 at tick 3000, mean recall >= 0.42
and the E6 gate 3/3; among qualifying arms the highest precision is
proposed (ties: M, BH). New seeds, disjoint from those that designed FP-2.

## Execution

`symbiont-lab experiment run experiments/learning/footprint-precision-fp2-bh/experiment.toml`

## Limits

Synthetic body with evaluator-only ground truth; the organism never sees
the classification.
