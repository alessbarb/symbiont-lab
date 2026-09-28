# Lab Server Unit Tests

## Purpose

Unit tests for the Symbiont Lab server and API endpoints under `tests/unit/lab/server`.

## Belongs here

Isolated unit tests validating server endpoints, protocol message dispatch, serialization, and stream lifecycle contracts.

## Does not belong here

Full live browser integration tests, distributed multi-node setups, long-running simulator campaigns, or full UI visual assertions.

## Criterion for creating a file

Create a file only when testing a distinct server protocol, route group, or endpoint handler that cannot be covered in an existing unit test.

## Execution

```bash
pytest tests/unit/lab/server
```

## Limits

Tests mock internal bus and WebSocket connections; passing this layer does not guarantee cross-browser visual fidelity or external network stability.
