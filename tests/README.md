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

## Superseded tests (norm)

The canonical test run describes the organism and laboratory as they are now
(ADR-0062). Every change that makes a test obsolete cleans it in the same change.

1. **Migrate or archive, never weaken.** If the mechanism the test checks still
   exists, migrate the test to the canonical organism (canonical profile; a
   deterministic Body from `tests/bodies.py` instead of the real host). If the
   behavior it asserts no longer applies, archive it. Do not skip it, loosen its
   assertion until it passes, or leave it failing.
2. **Archive with a replacement.** Move the test to `tests/archive/` and mark it
   `@pytest.mark.superseded(by="tests/...::test_...", reason="...")`. `by` names
   the canonical test that now covers the concern; a test with no valid
   replacement cannot be archived, so write the replacement first.
3. **Index it.** Add a row to the index in `tests/archive/README.md`.
4. **Out of the canonical run.** `pyproject.toml` excludes `tests/archive/` from
   collection; archived tests are not required to pass and are run only explicitly
   (`pytest tests/archive`) to inspect historical behavior.
5. **Closed experiments are not obsolete.** A study of a closed experiment stays
   bound to the profile version it ran under, and its tests stay canonical.

`tests/docs/test_test_archive.py` enforces rules 2–4.

## Limits

Passing pytest does not demonstrate a scientific conclusion, organism generalization, or equivalence between campaigns. Real runs must start through an explicit CLI and preserve manifests and results.

## Decision rule

1. Does it verify software? `tests/`. 2. Does it verify a runner or protocol? `tests/experiments/`. 3. Does it run a campaign? `experiments/`. 4. Does it interpret results? `research/`.
