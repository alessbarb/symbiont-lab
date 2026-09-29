# ADR-0045 — Owner-root grants, scientific execution authority and validation receipts

- **Status:** Accepted
- **Date:** 2026-09-29
- **Decision owner:** project owner
- **Extends:** ADR-0043

## Context

Adversarial review of the first governance control plane found that commit-range
auditing could collapse to one commit, grant issuance had no explicit root action,
scientific execution was resource-bounded but not permission-bounded, agent/test
configuration could weaken enforcement, and completed studies froze only selected
files.

## Decision

1. Grant issuance is a single-file owner-root administrative commit validated against
   the GitHub actor configured in `owner-root.toml`.
2. CI audits every commit in the declared base..head range and fails closed on missing
   or non-ancestor bases.
3. Evidentiary runs require exact `scientific-run` grants fixing code, argv, scope,
   run id and resource ceilings.
4. Agent hooks/rules, CI, pre-commit, CODEOWNERS, pytest/linter configuration and
   governance tests are L4 control-plane surfaces.
5. A completed experiment directory is frozen as a whole when it contains archived
   `results.json`.
6. Required validation is recorded against the exact staged Git tree before commit.
7. Local scientific locks use Git's common directory so worktrees share the lock.
   POSIX runs receive hard virtual-memory/CPU-time limits and process-group termination.

## Limits

Repository enforcement cannot distinguish the owner from an agent using the same owner
credential. Atomic cross-machine locking and portable storage quotas require external
infrastructure and are not claimed here.
