# Generative Cognition model correction

## Purpose

This registered assay covers the mechanism-level gate for **GC-E6** and **GC-E7**. It
starts with an opaque model prediction, supplies a changed evaluator-owned
factual outcome, reconciles the contradiction, applies the model adapter's
explicit factual-learning hook, and evaluates the next prediction.

The assay requires:

```text
wrong generated prediction
→ factual contradiction
→ corrected generated prediction
```

Generated states remain non-observed and neither the generated prediction nor
the learning hook writes factual evidence.

## Hypothesis

After a factual outcome contradicts an opaque generated prediction, an explicitly factual-learning model adapter will prioritize modifying the relevant generative parameters to reduce future error.

## Belongs here

This directory contains the registered protocol metadata and the instructions
for reproducing this model correction assay.

## Does not belong here

Pytest files, reusable study implementation, generated run artifacts and
unreviewed external-world claims do not belong in this directory.

## Criterion for creating a file

Add a file only when it is required to define, reproduce or interpret this
registered protocol. Put reusable code under `src/` and tests under `tests/`.

## Execution

Run it with:

```bash
symbiont-lab study run learning.generative-cognition-model-correction
```

## Limits

This is not evidence of broad intelligence, external-world utility, or autonomous model learning; those
claims require matched environment studies and independent ablations.
