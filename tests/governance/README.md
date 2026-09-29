# Governance tests

## Purpose

Verify repository authority, canonical agent-contract synchronisation, owner grants,
scientific-run admission, completed-experiment freezing and machine-readable project
state.

## Belongs here

Mechanical tests of governance metadata, path authority, grant ancestry, run admission
and control-plane invariants.

## Does not belong here

Scientific outcomes, ordinary organism behaviour, UI assertions or experiment results.

## Criterion for creating a file

Create a governance test when an authority rule can regress silently and can be checked
without turning a contingent scientific outcome into a software invariant.

## Execution

```bash
pytest tests/governance -q
python scripts/agentctl.py verify
```

## Limits

These tests cannot prove the human identity behind a shared GitHub credential and
cannot provide atomic distributed locking across unrelated clones or machines.
