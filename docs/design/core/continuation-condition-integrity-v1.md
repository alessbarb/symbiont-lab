---
id: design.core.continuation-condition-integrity-v1
title: "Continuation Condition Integrity v1"
document_type: design
domain: core
status: proposed
canonical: false
implementation_status: implemented
date: 2026-10-04
depends_on:
  - docs/governance/constitution.md
  - docs/design/core/longitudinal-integrity-v1.md
---

# Continuation Condition Integrity v1

## 1. Purpose

Protect the apparatus conditions that govern a saved organism's future
continuation without conflating those conditions with organism-state identity.
This closes the gap where a current checkpoint could lose or alter
`runtime_provenance.session_controls` while its organism-state hash remained
unchanged.

## 2. Contract

The checkpoint carries two independent identities:

- `checkpoint_lineage.checkpoint_id` covers organism state;
- `checkpoint_lineage.continuation_condition_hash` covers the canonical JSON
  representation of `runtime_provenance.session_controls`.

Restore rejects a current checkpoint when the controls are missing, malformed,
or differ from their recorded hash. An explicit launcher override remains
permitted: the checkpoint's saved controls are verified first, then the
effective override is reported by `changed_since_restore`.

These unkeyed hashes detect accidental changes and inconsistency. They are not
cryptographic authentication against an editor able to rewrite both data and
hashes.

## 3. Format policy

Checkpoint schema 12 introduces the continuation-condition identity. Schema 11
does not contain it and is rejected; no migration is provided. This preserves
the distinction between readable historical evidence and a checkpoint accepted
as a live continuation.

## 4. Evidence boundary

The contract establishes mechanical detection of missing or changed saved
conditions. It does not prove that the conditions are scientifically optimal,
that continuation is future-trajectory-equivalent, or that any organism
capability is useful.

Focused implementation coverage is in
`symbiont/tests/integration/test_restart_configuration.py`,
`symbiont/tests/unit/host/test_checkpoint.py`, and
`symbiont/tests/unit/host/test_strict_restore.py`.
