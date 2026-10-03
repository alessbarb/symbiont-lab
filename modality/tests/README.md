# Modality tests

## Purpose

Automated checks for signal channels. This suite belongs to the `modality` library and runs as its own pytest session.

## Belongs here

Tests that import only `modality`: signal structure, sampling, receptor adjacency.

## Does not belong here

Anything that needs a body, an organism, an environment or the Lab. Those belong in `lab/tests`.

## Criterion for creating a file

A new file must answer a verifiable software or reproducible-contract question about `modality`. If it has to import another domain library, it is an integration test and goes to `lab/tests`.

## Execution

`pytest modality/tests` from the repository root, or `python scripts/run_tests.py modality`. The default profile excludes tests marked `slow`; add `-o addopts=` to include them.

## Limits

Passing tests show mechanical correctness of the covered contracts. They do not validate scientific hypotheses.
