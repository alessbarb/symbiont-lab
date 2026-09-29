# ADR-0044 — Host-safety and lifecycle invariants in the Constitution

- **Status:** Proposed
- **Date:** 2026-09-29
- **Decision owner:** project owner

## Context

ADR-0043 made [`docs/governance/constitution.md`](../governance/constitution.md) the
single canonical source of permanent invariants. The Constitution states that it
covers "architectural, epistemic, host-safety, lifecycle, heredity, boundedness and
observability invariants", but its numbered sections (1–22) contain only the
architectural and epistemic invariants.

Until 2026-09-29 the roadmap carried two further sets of permanent constraints. They
were dropped when the roadmap was rewritten on that date:

- **Real-host and safety invariants.** The earlier roadmap listed 13 invariants: host
  access explicit, revocable and capability-bounded; learned state never manufacturing
  permissions, commands, code or kernel capabilities; transparent owner-controlled
  residence; no stealth, evasion or exploitation; hard CPU, memory, storage and
  communication ceilings outside learned control; reproduction never meaning covert
  or uncontrolled propagation; descendants only in an authorized habitat.
- **Lifecycle invariants.** Normal restore rejects a `DEAD` identity. Reconstructing or
  cloning from historical artifacts creates a new identity and is not resurrection.
  Organism lifecycle, cognitive topology health and reproductive readiness are separate
  state dimensions.

Today these survive only partially:

- [`governance/decision-gates.md`](../governance/decision-gates.md) § Host and safety
  says which changes need L4 approval plus an ADR. It describes a gate, not what must
  always hold.
- [ADR-0017](ADR-0017-host-least-privilege-and-non-remediation-safety.md) (host least
  privilege, no remediation, no network activity, fail-closed) and
  [ADR-0018](ADR-0018-transparent-resident-lifecycle-supervision.md) (owner-consented,
  transparent, terminable residence) are accepted but are not referenced from the
  Constitution.
- The verbatim earlier text exists only in git history
  (`c00846d3:docs/roadmap.md`, sections "Permanent invariants" and "Birth, identity,
  dormancy and death"). [`history/roadmap-log.md`](../history/roadmap-log.md) does not
  contain it. This ADR reproduces it below.

Because the Constitution now claims to be the single source, a host-safety or
lifecycle invariant that is absent from it has no canonical home.

## Decision (proposed)

After owner acceptance, add two sections to the Constitution. Numbering continues after
the current last invariant.

### 23. Real-host and safety boundaries

The text is the pre-2026-09-29 roadmap list, verbatim:

1. Real-host access remains explicit, revocable and capability-bounded.
2. Learned state cannot manufacture permissions, commands, executable code or new kernel capabilities.
3. Credentials and privilege-escalation mechanisms remain outside the organism's developmental substrate.
4. Residence and persistence remain transparent and owner-controlled.
5. No stealth, concealment or evasion is used to maintain residence or acquire resources.
6. No exploitation is used to acquire capabilities, compute, storage or access.
7. Hard CPU, memory, storage and communication ceilings remain outside learned control.
8. Reproduction never means covert or uncontrolled propagation.
9. Materializing a descendant requires an authorized habitat, carrying-capacity slot and explicit resource allocation.
10. A dead organism identity cannot be normally resumed as though continuity never closed.
11. Experimental ground truth remains outside organism cognition.
12. The laboratory may observe the organism without silently becoming its controller.
13. New write, network, action or reproduction capabilities cross an explicit design and consent gate before implementation.

These invariants do not imply that Symbiont must remain permanently read-only,
non-communicating or non-reproductive. Items 11 and 12 duplicate existing Constitution
sections 2 and 13 and may be replaced by cross-references when the section is applied.
ADR-0017 and ADR-0018 are the accepted operational specifications of items 1–7.

### 24. Lifecycle identity

1. Normal restore rejects a `DEAD` identity.
2. Reconstructing or cloning from historical artifacts, if allowed experimentally,
   creates a new identity and is not resurrection.
3. Organism lifecycle, cognitive topology health and reproductive readiness remain
   separate state dimensions. An organism may simultaneously be `MATURE`, `ADAPTIVE`
   and `REPRODUCTIVELY_READY`.

## Alternatives considered

- **Keep the invariants only in `decision-gates.md`.** Rejected: a decision gate says
  when to stop and ask, not what must always hold. A change that passed the gate could
  still weaken an invariant without violating any written rule.
- **Keep them in the roadmap.** Rejected: ADR-0043 forbids duplicating permanent
  invariants outside the Constitution, and the roadmap changes with priorities.
- **Reference ADR-0017/0018 only.** Rejected as insufficient: those ADRs do not cover
  learned permission manufacture, hard resource ceilings, reproduction/propagation or
  lifecycle identity.

## Consequences

- The Constitution becomes complete for the categories it already claims to cover.
- Applying this ADR requires a separate L4 owner grant for
  `docs/governance/constitution.md` after acceptance, following the Constitution's
  own amendment order (proposal → ADR → acceptance → Constitution update).
- No runtime or test behaviour changes. Existing host tests (ADR-0017/0018 evidence)
  and lifecycle tests remain the enforcement.
