# Generative Cognition multi-step predictive utility

## Purpose

This registered assay covers the first mechanism-level gate for **GC-E1**. It
compares three conditions on the same opaque sequence and initial state:

```text
persistence
one-step rollout
multi-step rollout
```

The evaluator keeps the target token hidden from the model and scores the final
prediction at horizons `1`, `2` and `4`. The generative model advances one
opaque state at a time; generated states remain non-observed and no factual
ledger is used.

## Hypothesis

On an opaque deterministic sequence, a bounded multi-step Generative Cognition rollout will predict the target at horizons 1, 2 and 4 with lower loss than persistence and one-step baselines.

## Belongs here

This directory contains the registered protocol metadata and the instructions
for reproducing this predictive utility assay.

## Does not belong here

Pytest files, reusable study implementation, generated run artifacts and
unreviewed external-world claims do not belong in this directory.

## Criterion for creating a file

Add a file only when it is required to define, reproduce or interpret this
registered protocol. Put reusable code under `src/` and tests under `tests/`.

## Execution

Run it with:

```bash
symbiont-lab study run learning.generative-cognition-predictive-utility
```

## Limits

This gate demonstrates bounded rollout utility on a synthetic sequence. It
does not establish external-world calibration, embodied planning, transfer or
general intelligence. Those require matched environments and independent ablations.
