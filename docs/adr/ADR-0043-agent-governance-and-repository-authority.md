# ADR-0043 — Agent governance and repository authority control plane

- **Status:** Accepted
- **Date:** 2026-09-29
- **Decision owner:** project owner

## Context

Symbiont Lab is routinely modified by capable coding agents, sometimes concurrently.
Repository access alone must not imply authority to change scientific direction,
frozen protocols, claims, host-safety boundaries or the governance system itself.

Documentation-only instructions are insufficient because an agent can misunderstand,
omit or accidentally weaken them.

## Decision

Adopt a repository governance control plane with:

1. authority levels L0-L4;
2. the Constitution as the single canonical source of permanent invariants;
3. machine-readable project state, active work, frozen artefacts and validation rules;
4. parent-commit owner grants for L2-L4 changes;
5. commit ancestry auditing so a grant edited in the same commit cannot authorise that
   commit;
6. L4 protection for the governance control plane itself;
7. automatic freezing of a protocol once archived results exist beside it;
8. one-long-scientific-run default concurrency, with a governed launcher and tracked
   exceptions for already-running external campaigns;
9. append-only treatment of historical scientific results;
10. CODEOWNERS/CI/pre-commit as additional enforcement layers.

## Grant model

A grant is issued in a dedicated owner commit and records the commit immediately
preceding grant issuance. The grant is valid only for the direct child implementation
commit. This makes it single-use without requiring the implementation commit hash in
advance.

The implementation commit records:

```text
Authority-Grant: <grant-id>
```

`agentctl` evaluates the grant and frozen/active-work metadata from the parent
revision, never from the candidate working tree.

## Root of trust

Repository-side enforcement cannot distinguish a malicious process that possesses the
same GitHub credentials as the owner from the owner. Server-side protected-branch
review remains desirable where the hosting plan permits it.

The local/CI control plane therefore prevents self-authorisation within repository
history, detects unauthorized protected changes and narrows normal agent workflows,
but does not claim to be a cryptographic substitute for external identity and branch
protection.

## Consequences

- L1 remains available for ordinary non-semantic maintenance.
- L2-L4 work requires an explicit prior owner grant.
- Governance changes cannot authorize themselves.
- Completed experiment protocols are frozen automatically.
- Scientific campaigns must use the governed launcher unless an owner-recorded external
  exception exists.
- CI smoke studies are mechanical verification only and do not create scientific
  evidence or elevate claims.
