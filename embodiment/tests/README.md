# Embodiment tests

## Purpose

Automated checks for bodies and their contracts. This suite belongs to the `embodiment` library and runs as its own pytest session.

## Belongs here

Tests that import only `embodiment`: body descriptors, receptor and effector contracts, mount points.

## Does not belong here

Anything that needs an organism, a modality, an environment or the Lab. Those belong in `lab/tests`.

## Criterion for creating a file

A new file must answer a verifiable software or reproducible-contract question about `embodiment`. If it has to import another domain library, it is an integration test and goes to `lab/tests`.

## Execution

`pytest embodiment/tests` from the repository root, or `python scripts/run_tests.py embodiment`. The default profile excludes tests marked `slow`; add `-o addopts=` to include them.

## Limits

Passing tests show mechanical correctness of the covered contracts. They do not validate scientific hypotheses.
