# Generative Cognition recombination construction

## Purpose

This registered assay covers the resident boundary of **GC-E14** and **GC-E15**. It supplies
two opaque, organism-owned fragments with one shared compatibility relation and
checks that the resident creates one `imagined` state with both source episode
and source state identifiers preserved. A matched fresh resident is the
no-construction control. A second pair with no shared compatibility relation
must be rejected without creating a workspace.

The evaluator scores construction, provenance, rejection and contamination
only. It supplies no external outcome or correctness label.

## Hypothesis

The resident Generative Cognition boundary will construct a bounded imagined state from two organism-owned compatible fragments while strictly rejecting incompatible pairs without contamination.

## Belongs here

This directory contains the registered protocol metadata and the instructions
for reproducing this recombination construction assay.

## Does not belong here

Pytest files, reusable study implementation, generated run artifacts and
unreviewed external-world claims do not belong in this directory.

## Criterion for creating a file

Add a file only when it is required to define, reproduce or interpret this
registered protocol. Put reusable code under `src/` and tests under `tests/`.

## Execution

Run it with:

```bash
symbiont-lab study run learning.generative-cognition-recombination-construction
```

## Limits

This assay does not demonstrate recombination utility, planning benefit or general
intelligence. Autonomous multi-source scheduling and utility experiments remain separate work.
