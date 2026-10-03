# Generative Cognition depth calibration

## Purpose

This registered assay covers the mechanism-level gate for **GC-E8** and **GC-E9**. It runs
the same opaque model at bounded rollout depths `1`, `2` and `4`, records the
model's declared uncertainty, and compares each final prediction with an
evaluator-owned factual target.

The gate checks that uncertainty and observed error increase in the declared
direction, that every comparison is paired with a prior prediction, and that
generated states remain non-observed. It is not a universal calibration curve
or evidence of external-world generalisation.

## Hypothesis

For a bounded opaque sequence model, declared uncertainty and later observed prediction error will increase monotonically with rollout depth.

## Belongs here

This directory contains the registered protocol metadata and the instructions
for reproducing this depth calibration assay.

## Does not belong here

Pytest files, reusable study implementation, generated run artifacts and
unreviewed external-world claims do not belong in this directory.

## Criterion for creating a file

Add a file only when it is required to define, reproduce or interpret this
registered protocol. Put reusable code under `src/` and tests under `tests/`.

## Execution

Run it with:

```bash
symbiont-lab study run learning.generative-cognition-depth-calibration
```

## Limits

The result is a mechanism gate over opaque sequence rollouts. It does not
establish universal calibration curves or general external-world validity.
