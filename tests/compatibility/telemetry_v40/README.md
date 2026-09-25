# Telemetry v4.0 compatibility

## Purpose

This directory documents and tests any telemetry v4.0 artifact that the
project explicitly elects to read through a migration.

## Belongs here

Small historical telemetry payloads and version-specific conversion rules.

## Does not belong here

Current telemetry contracts, live observatory behavior, or physics assertions.

## Criterion for creating a file

Add a file only after identifying a concrete v4.0 artifact and its supported
migration outcome. Do not create compatibility tests for an undocumented
legacy signature.

## Execution

```bash
pytest tests/compatibility/telemetry_v40 -q
```

## Limits

Compatibility coverage is limited to the fields and versions named by the
fixture; it is not a general promise to accept arbitrary old telemetry.
