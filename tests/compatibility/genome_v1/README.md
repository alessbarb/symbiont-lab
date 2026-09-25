# Genome v1 compatibility

## Purpose

This directory contains focused tests for converting the retired Genome v1
payload into the active Genome v2 representation.

## Belongs here

Minimal v1 payloads, migration validation, and assertions that removed fields
do not enter the live Genome object.

## Does not belong here

New Genome v2 fixtures or runtime code paths that silently accept v1.

## Criterion for creating a file

Add a file only for a distinct historical payload shape or migration rule.
Prefer one representative fixture over duplicating the active v2 suite.

## Execution

```bash
pytest tests/compatibility/genome_v1 -q
```

## Limits

These tests do not establish that v1 and v2 have identical semantics; the
migration deliberately drops fields with no active v2 meaning.
