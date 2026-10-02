# Checkpoint v10 compatibility

## Purpose

Runtime checkpoints written by the last schema-10 code (`main@81142a3e`,
software 0.90.0), before checkpoint identity became verifiable in schema 11.
They exist because a schema-10 payload cannot be faked by relabelling a current
one: it lacks every field that schema 11 added, and its lineage identifier
covers only base-runtime fields.

## Belongs here

Real schema-10 payloads and tests that carry them through plain restore and
through every authorized transform (canonical-cognition adoption,
re-embodiment, temporal decontamination).

## Does not belong here

Current-schema round trips, or "legacy" payloads derived from a current
checkpoint. Use `tests/checkpoints.as_legacy` for those and keep them in the
active suites.

## Criterion for creating a file

Add a fixture only when it is produced by the historical code itself and covers
a runtime layer or transform the existing fixtures do not.

## Execution

```bash
pytest tests/compatibility/checkpoint_v10 -q
```

## Limits

The fixtures are small, hand-seeded organisms. Passing here shows that a
schema-10 checkpoint is still restorable and transformable; it does not show
continuation equivalence with the code that wrote it.
