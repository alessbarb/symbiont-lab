# Tests

## Purpose

This folder contains automated checks for software, contracts, and experimental boundaries. Its documentation is part of the repository organization contract.

## Belongs here

Deterministic pytest tests for implementation, integration, documentation, regressions, smoke checks, and mechanical runner contracts.

## Does not belong here

No full scientific campaigns, run results, research fixtures, or evidence interpretation. Those belong in `experiments/` or `research/`.

## Criterion for creating a file

A new file must answer a verifiable software or reproducible-contract question. If it needs a campaign, many seeds, or produces scientific evidence, put the campaign in `experiments/` and keep only its mechanical contract here.

## Execution

The default `pytest` profile excludes tests marked `slow`. Run layers explicitly, for example `pytest tests/unit tests/docs tests/smoke`, `pytest tests/integration tests/experimental_integrity`, or `pytest tests/experiments`. Run the scientific suite explicitly with `pytest -o addopts='' tests/integration/studies` or select it with `pytest -o addopts='' -m slow`.

## Limits

Passing pytest does not demonstrate a scientific conclusion, organism generalization, or equivalence between campaigns. Real runs must start through an explicit CLI and preserve manifests and results.

## Decision rule

1. Does it verify software? `tests/`. 2. Does it verify a runner or protocol? `tests/experiments/`. 3. Does it run a campaign? `experiments/`. 4. Does it interpret results? `research/`.
