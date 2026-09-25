# Migration boundaries

## Purpose

This directory contains cross-version migration tests whose source and target
contracts are owned by different modules.

## Belongs here

Tests for deterministic, one-way conversion into active schemas, including
rejection of malformed or ambiguous legacy data.

## Does not belong here

Compatibility aliases in production imports, broad regression tests, or
scientific conclusions.

## Criterion for creating a file

Create a file when a migration spans more than one historical artifact family
or when the boundary itself is the behavior under test. Keep schema-specific
cases in their version directory instead.

## Execution

```bash
pytest tests/compatibility/migrations -q
```

## Limits

Migration tests prove conversion and validation only. They do not replace
current-contract tests or establish scientific equivalence.
