# Host channel tests

## Purpose

Automated checks for `modality.host`: the read-only, aggregate signals of the machine a process runs on.

## Belongs here

Tests that import only `modality.host`: which surfaces a channel offers, that they are opaque and aggregate, and what a sample contains.

## Does not belong here

How an organism discovers, samples or learns from these channels. That is the organism's host machinery (`symbiont/tests/unit/host`), or, when both are involved, `lab/tests`.

## Criterion for creating a file

One file per channel module in `modality.host`.

## Execution

`python scripts/run_tests.py modality`.

## Limits

Readings come from the machine running the tests; assertions are on structure and bounds, not on values.
