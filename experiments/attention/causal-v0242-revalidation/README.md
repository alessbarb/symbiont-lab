# Corrected Causal Attention Revalidation

## Protocol

`attention.replicated` (version 3)

## Purpose

Revalidate causal directed attention allocation against random attention baseline across fixed inspection budgets (5, 12, 20 per 1000 events) after fixing startup eligibility bias (ADR-0007).


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
