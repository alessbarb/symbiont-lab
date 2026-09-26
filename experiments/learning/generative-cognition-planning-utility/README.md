# Generative Cognition planning utility

## Purpose

This registered assay covers the mechanism-level gate for **GC-E2**. It
compares one-step prospection with bounded two-step prospection over the same
opaque actions and factual value ledger. Immediate predictions are identical;
only the deeper rollout distinguishes the evaluator-owned safe terminal.

## Belongs here

This directory contains the registered protocol metadata and the instructions
for reproducing this bounded planning-utility assay.

## Does not belong here

Pytest files, reusable study implementation, generated run artifacts and
unreviewed external-world claims do not belong in this directory.

## Criterion for creating a file

Add a file only when it is required to define, reproduce or interpret this
registered protocol. Put reusable code under `src/` and tests under `tests/`.

## Execution

The gate measures matched action-selection utility while keeping evaluator
targets outside the organism. It is not evidence of embodied planning or
external-world generalisation.

Run it with:

```bash
symbiont-lab study run learning.generative-cognition-planning-utility
```

## Limits

The result is a mechanism gate over opaque synthetic actions. It does not
establish embodied planning, external-world calibration, transfer, or a broad
intelligence advantage. Preserve the recorded commit and run manifest with any
scientific interpretation.
