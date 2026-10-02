# ADR-0059 — Repository Skills for Scientific and Performance Work

- **Status:** Accepted
- **Date:** 2026-10-02
- **Decision owner:** project owner
- **Relates to:** ADR-0043, ADR-0048, ADR-0049, ADR-0056
- **Scope:** Agent workflow guidance in the four listed repository skills; no runtime, protocol, or constitutional invariant changes

## Context

Scientific documentation, empirical experimentation, scientific investigation,
and performance investigation have distinct evidence requirements. Keeping their
workflows in separate, versioned repository skills makes those boundaries
discoverable and reviewable without treating an agent skill as scientific
authority or as a substitute for repository governance.

The skill bundle being adopted consists of:

- `.agents/skills/scientific-documentation/SKILL.md`
- `.agents/skills/scientific-experiment/SKILL.md`
- `.agents/skills/scientific-investigation/SKILL.md`
- `.agents/skills/performance-investigation/SKILL.md`

These files provide operational guidance to agents. They do not establish
scientific results, approve experiments, authorize held-out or confirmation
data, or change the authority of existing repository documents.

## Decision

Accept and version the four repository skills as the supported workflow guidance
for their respective task types.

The skills remain subordinate to `AGENTS.md`, the Constitution, accepted ADRs,
frozen scientific protocols, owner decisions, and the repository's publication
and validation policies. If a skill conflicts with any higher-authority source,
the higher-authority source governs and the skill must be corrected.

This decision approves the guidance documents for use; it does not approve any
experiment described or initiated by following them, nor does it authorize
changes to organism behavior or scientific protocols.

## Alternatives considered

### Keep the workflows only in generic agent instructions

Rejected because the four task types have materially different evidence and
validation boundaries. A generic instruction set would obscure those
distinctions and make task-specific guidance harder to maintain.

### Combine all four workflows into one skill

Rejected because it would couple documentation, investigation, experiment
execution, and performance measurement despite their different authority and
validation requirements.

### Treat the skills as independent authority

Rejected because repository skills are operational guidance, not a source of
scientific authorization or constitutional authority.

## Consequences

- Agents can discover the appropriate workflow guidance in the repository.
- The four skills can evolve independently while remaining reviewable as one
  coherent package.
- Skill guidance must remain subordinate to the repository's governance and
  scientific authority boundaries.
- Approval of these skills does not approve any related study or execution.
