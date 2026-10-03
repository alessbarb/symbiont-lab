# Lab tests

## Purpose

Automated checks for composition and integration. This suite belongs to the `lab` library and runs as its own pytest session.

## Belongs here

Tests that import `lab`, or two or more domain libraries: studies, experiment mechanics, Physics3D runtime, integration adapters, CLI, server, workbench.

## Does not belong here

Tests of a single domain library on its own (they live beside that library), and repository-wide checks such as governance, documentation and source-layout scans (root `tests/`).

## Criterion for creating a file

A new file must answer a verifiable software or reproducible-contract question about `lab`. If it has to import another domain library, it is an integration test and goes to `lab/tests`.

## Execution

`pytest lab/tests` from the repository root, or `python scripts/run_tests.py lab`. The default profile excludes tests marked `slow`; add `-o addopts=` to include them.

## Limits

Passing tests show mechanical correctness of the covered contracts. They do not validate scientific hypotheses.
