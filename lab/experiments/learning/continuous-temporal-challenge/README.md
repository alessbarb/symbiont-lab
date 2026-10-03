# Continuous temporal mechanism challenge

This study evaluates the sparse ESN + NLMS challenger on a bounded continuous
stream with a deterministic regime shift.

It is intentionally separate from the token-based private-model study. The
purpose is to avoid giving the ESN an artificial discrete representation or
forcing GRU/Transformer token assumptions onto continuous dynamics.

Metrics include pre-shift gain, early post-shift damage, late post-shift gain,
adaptation recovery, and learned/fixed parameter counts.

No result from this study automatically grants the ESN any privileged role in
the organism.


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
