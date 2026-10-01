# ADR-0048 — Remove operational granting and use external review

- **Status:** Accepted
- **Date:** 2026-10-01
- **Decision owner:** project owner
- **Supersedes operationally:** ADR-0043 and ADR-0045 grant mechanics
- **Extends:** ADR-0046 and ADR-0047

## Context

ADR-0046 replaced per-commit grants with proportional governance, but the repository
still carried the L0-L4 lattice, grant issuance/consumption, session manifests,
scientific-run grants and self-asserted approval flags. They blocked work without
providing a trustworthy identity boundary when agents share owner credentials.

## Decision

1. Remove grants, authority levels and session manifests from active publication and execution.
2. Preserve the former grant ledger only as immutable historical provenance.
3. `agentctl publish` publishes classified candidates; covered causal equivalence may downgrade SCIENTIFIC to ORDINARY.
4. Only ORDINARY candidates may auto-promote. SCIENTIFIC and CONSTITUTIONAL require external review.
5. CONSTITUTIONAL candidates still require an Accepted ADR recorded in provenance.
6. FROZEN evidence and RUNNING campaign protection remain enforced.
7. `run start` keeps commit pinning, immutable input archival, resource ceilings, concurrency locks and receipts. Evidentiary launches remain explicit owner decisions by policy, without a fake authentication flag.
8. New capabilities inside accepted invariants are not owner gates merely because they are new.

## Consequences

The active control plane is classification, equivalence, CI and promotion policy.
Historical grants remain auditable but cannot block new work. Human approval is
represented where it is real — outside the candidate commit.
