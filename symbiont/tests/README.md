# Symbiont tests

## Purpose

Automated checks for the organism. This suite belongs to the `symbiont` library and runs as its own pytest session.

## Belongs here

Tests that import only `symbiont`: cognition, genetics, agency, actuation, sensory, host boundary, runtime, checkpoints.

## Does not belong here

Anything that needs a body, a world, a modality or the Lab. Those are integration tests and belong in `lab/tests`.

## Criterion for creating a file

A new file must answer a verifiable software or reproducible-contract question about `symbiont`. If it has to import another domain library, it is an integration test and goes to `lab/tests`.

## Execution

`pytest symbiont/tests` from the repository root, or `python scripts/run_tests.py symbiont`. The default profile excludes tests marked `slow`; add `-o addopts=` to include them.

## Limits

Passing tests show mechanical correctness of the covered contracts. They do not validate scientific hypotheses.
