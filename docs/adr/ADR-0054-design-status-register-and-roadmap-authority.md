# ADR-0054: Design Status Register and Roadmap Authority

- **Status:** Accepted
- **Date:** 2026-10-01
- **Decision owner:** project owner
- **Decision scope:** Documentation lifecycle and status tracking only

## Context

The repository contains many design documents at different stages: proposals,
reviewed designs, owner-approved work, frozen or closed programmes, and
references. Without a single status authority, pending designs can be forgotten
or mistaken for approved and scheduled work. The roadmap has a distinct role:
it governs scientific direction, priority, gates, and authorization.

The initial documentary triage identified 57 active, non-archived design
documents. This inventory is intended to make their recorded status discoverable;
it is not a blanket technical, scientific, or implementation review.

## Decision

1. `docs/design/register.md` is the canonical authority for each active design's
   lifecycle and implementation status. Every non-archived design under
   `docs/design/` must have one register entry.
2. The register is required reading before creating, reviewing, approving,
   implementing, or reporting completion of a design. A status change must be
   reflected in the same change as its supporting decision or implementation
   evidence.
3. The register does not replace the roadmap. The roadmap remains authoritative
   for research direction, priority, milestone acceptance, experiment gates,
   and authorization. It may reference a design or its register entry without
   changing those authorities.
4. Statuses must not be inferred from document age, title, related code, or a
   roadmap mention. In particular, `Reviewed` is not `Approved`, approval is
   not scheduling, and implementation status does not imply scientific
   acceptance.
5. An entry in the register does not authorize implementation, experiments, or
   reopening work that is frozen, paused, or unscheduled under separate
   governance.
6. Archived designs are excluded from the active register. `docs/design/README.md`
   remains a navigation page and must point readers to the register for status.

## Consequences

- The initial triage records the most conservative status supported by each
  design document, explicit owner decision, roadmap, and bounded implementation
  evidence. It does not claim fresh validation of every design.
- New designs and status transitions have an explicit place to be tracked;
  roadmap changes are not required merely to record a design's lifecycle.
- Proposals such as `Passive Runtime Audit Trace v1` remain proposals until
  separately approved and scheduled. This ADR does not authorize their
  implementation or alter A9 priority or acceptance.
- Existing FROZEN, PAUSED, CLOSED, and UNSCHEDULED boundaries remain unchanged.

## Acceptance criteria

- [x] A canonical register defines lifecycle and implementation states.
- [x] All active, non-archived design documents have a register entry.
- [x] Agent instructions require the register to be read for design-related
  work.
- [x] The design index identifies the register as the status authority.
- [x] The roadmap retains scientific direction and priority authority and only
  references the proposal without changing its gate.
- [x] Focused documentation link and register consistency tests pass.

## Decision

Accepted by the project owner on 2026-10-01. This decision establishes design
status tracking and mandatory reading. It does not accept every listed design,
authorize implementation or experimentation, change the scientific roadmap,
or reopen any frozen, paused, or unscheduled work.
