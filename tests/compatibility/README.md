# Compatibility tests

## Purpose

This tree verifies explicitly supported historical payloads and their isolated
migrations into the current contracts. It is not part of the operational test
surface.

## Belongs here

Tests for versioned genome, checkpoint, telemetry, and migration boundaries
that intentionally mention a retired schema.

## Does not belong here

Current Genome v2 behavior, normal runtime tests, scientific campaigns, or
tests that preserve an obsolete alias in the live API.

## Criterion for creating a file

Create a file only when a historical artifact has a documented support or
rejection policy and the migration result can be asserted independently. If a
test describes current behavior, place it under the relevant `tests/` layer.

## Execution

```bash
pytest tests/compatibility -q
```

## Limits

Passing a migration test proves only that the selected historical artifact is
handled as specified. It does not prove that the historical runtime or a full
scientific result can be reproduced.
