# Tests

## Purpose

Repository-wide checks: governance tooling, documentation integrity, and scans of the source layout and of the boundaries between domains. Tests of one library live beside that library (`symbiont/tests`, `embodiment/tests`, `modality/tests`, `environment/tests`); tests that compose libraries live in `lab/tests`.

## Belongs here

Deterministic pytest checks that concern the repository as a whole or read source across several domains: `governance/`, `docs/`, the architecture and boundary scans in `experimental_integrity/`, and the few tests that drive `scripts/`.

## Does not belong here

Tests of a single library, integration tests, full scientific campaigns, run results, research fixtures, or evidence interpretation.

## Criterion for creating a file

A new file must answer a question about the repository as a whole. If it imports exactly one domain library and nothing repository-wide, it belongs in that library's suite; if it imports the Lab or two libraries, in `lab/tests`.

## Execution

`pytest tests` runs this suite. `python scripts/run_tests.py` runs every suite, one pytest session each (several directories are named `tests`, so they cannot share a session). The default profile excludes tests marked `slow`; pass `-o addopts=` to include them.

## Superseded tests (norm)

The canonical test run describes the organism and laboratory as they are now
(ADR-0062). Every change that makes a test obsolete cleans it in the same change.

1. **Migrate or archive, never weaken.** If the mechanism the test checks still
   exists, migrate the test to the canonical organism (canonical profile; a
   deterministic Body from `symbiont/tests/bodies.py` instead of the real host). If the
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
