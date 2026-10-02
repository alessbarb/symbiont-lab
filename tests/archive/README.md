# Archived tests

## Purpose

Tests that assert behavior which no longer applies to the canonical organism or
its launchers, kept as a historical record. They are **not** part of the
canonical test run. The norm that governs this folder is in `tests/README.md`
("Superseded tests").

## Belongs here

A test whose asserted behavior is obsolete, marked
`@pytest.mark.superseded(by="tests/...::test_...", reason="...")`, where `by` names
the canonical test that now covers the concern, and listed in the index below.

## Does not belong here

A test of a mechanism that still exists: migrate it to the canonical organism
instead. A test of a closed experiment's study: it stays canonical, bound to the
profile version the experiment ran under. A test without a valid replacement.

## Criterion for creating a file

Move the obsolete test here in the same change that made it obsolete, with its
marker and an index row. Keep the original module helpers it needs in the same
file.

## Execution

`pyproject.toml` excludes this folder from collection, so `pytest` never runs it.
Run it explicitly with `pytest tests/archive` to inspect historical behavior;
archived tests are not required to pass on current code.
`tests/docs/test_test_archive.py` checks markers, replacements and the index.

## Limits

An archived test is evidence of what the code once did, not of what it does now.

## Index

| Archived file | Superseded by | Reason |
| --- | --- | --- |
| `test_w02_retry_experiment.py` | `tests/unit/lab/world/test_persistence.py::test_checkpoint_replay_matches_the_first_causal_tick` | The frozen W02 retry runner passes options World no longer accepts (ADR-0062). |
| `test_semantic_bootstrap_aliasing.py` | `tests/unit/core/test_semantic_bootstrap_aliasing.py::test_without_semantic_bootstrap_the_example_graph_stays_legitimately_disconnected` | Semantic sense bootstrap is not part of profile v1. |
| `test_resident_semantic_alias.py` | same as above | Asserts the semantic alias of a hand-labelled sense. |
| `test_resident_semantic_bootstrap_flag.py` | `tests/experimental_integrity/test_canonical_organism_profile.py::test_no_launcher_deviates_without_declaring_it` | The `--semantic-bootstrap` launcher flag was removed. |
