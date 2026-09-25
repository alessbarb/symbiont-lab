# Checkpoint v1 compatibility

## Purpose

This directory is reserved for historical checkpoints whose genome section
requires the explicit checkpoint migration boundary.

## Belongs here

Versioned checkpoint fixtures and tests for hash handling, migration, and
rejection of corrupted historical data.

## Does not belong here

Current checkpoint round trips or replay determinism tests. Those belong in
the active unit or integration suites.

## Criterion for creating a file

Create a file only when it covers a supported historical checkpoint shape that
cannot be represented by a current fixture.

## Execution

```bash
pytest tests/compatibility/checkpoint_v1 -q
```

## Limits

A successful migration does not prove continuation equivalence. Replay
equivalence requires a separate deterministic trajectory test.
