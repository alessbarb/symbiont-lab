# E4 — Causal Revision Sequence

Within-subject sequence:

```text
stable Body A
→ SHAM
→ output permutation
→ restore
→ silent effector failure
→ repair
→ transplant Body B
→ return Body A
```

The Symbiont receives no phase marker, body ID or perturbation label.

Run:

```bash
symbiont-lab experiment run experiments/embodiment/causal-revision-sequence/experiment.toml
```

This study measures whether causal revision is selective to real physical
changes. It does not claim a correct self/world boundary; E1 and E5 already
show that stronger claim fails under matched external correlation.


## Purpose

This README defines this location's scope within the experiment hierarchy.

## Belongs here

Protocols, configuration, documentation, and identifiable results from reproducible runs.

## Does not belong here

No pytest-collectable tests, production code, or final scientific interpretation.

## Criterion for creating a file

Add only a file that records a reproducible protocol element, an execution, or a result; mechanical contracts belong in `tests/experiments/`.

## Execution

Use the explicit command documented by the protocol or CLI; do not execute this folder through pytest.

## Limits

The contents are evidence bounded by the protocol and do not demonstrate generalization by themselves.
