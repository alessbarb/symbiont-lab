# Structural producer fairness stress

This protocol tests the scheduler in isolation from embodied learning.

Four continuously active opaque producers compete for structural admission. One
producer attempts to expose 1,000 simultaneous hypotheses. Backpressure must
collapse that multiplicity to one global nominee.

The test records the exact service schedule and verifies a hard fairness bound:
with P continuously active producers, no producer may wait more than P-1
completed arbitration rounds between opportunities.

This is an infrastructure property, not a cognitive utility test. It does not
claim that proposals deserve to survive after admission.


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
