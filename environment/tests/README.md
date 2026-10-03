# Environment tests

## Purpose

Automated checks for worlds, laws and ground truth. This suite belongs to the `environment` library and runs as its own pytest session.

## Belongs here

Tests that import only `environment`: topology, laws, state, genesis, checkpoints, fixtures.

## Does not belong here

Anything that needs an organism, a body, a modality or the Lab. Those belong in `lab/tests`.

## Criterion for creating a file

A new file must answer a verifiable software or reproducible-contract question about `environment`. If it has to import another domain library, it is an integration test and goes to `lab/tests`.

## Execution

`pytest environment/tests` from the repository root, or `python scripts/run_tests.py environment`. The default profile excludes tests marked `slow`; add `-o addopts=` to include them.

## Limits

Passing tests show mechanical correctness of the covered contracts. They do not validate scientific hypotheses.
