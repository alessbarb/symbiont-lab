# Generative Cognition replay utility

## Purpose

This registered assay covers the mechanism-level gate for **GC-E16** and **GC-E17**. It
compares an online-only control with the same opaque model after one factual
episode has been materialized as bounded `REPLAYED` cognition.

The gate requires replay to improve the matched prediction while preserving
the source episode identity, leaving the factual episode count unchanged, and
keeping factual and agenda contamination at zero.

## Hypothesis

With identical factual experience and the same opaque model, bounded replay will improve a matched prediction while retaining zero factual contamination and zero agenda contamination.

## Belongs here

This directory contains the registered protocol metadata and the instructions
for reproducing this replay utility assay.

## Does not belong here

Pytest files, reusable study implementation, generated run artifacts and
unreviewed external-world claims do not belong in this directory.

## Criterion for creating a file

Add a file only when it is required to define, reproduce or interpret this
registered protocol. Put reusable code under `src/` and tests under `tests/`.

## Execution

Run it with:

```bash
symbiont-lab study run learning.generative-cognition-replay-utility
```

## Limits

It is not evidence of general external-world utility or of benefit from replay in every task.
