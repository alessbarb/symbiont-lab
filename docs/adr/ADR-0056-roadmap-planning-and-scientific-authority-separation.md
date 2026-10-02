# ADR-0056 — Separate Project Roadmap Tracking from Scientific Authority

- **Status:** Accepted
- **Date:** 2026-10-02
- **Decision owner:** project owner
- **Relates to:** ADR-0054, `docs/roadmap.md`, and `docs/governance/change-surfaces.toml`

## Context

`docs/roadmap.md` is currently described as the canonical active scientific
roadmap. ADR-0054 also assigns it authority over scientific direction,
priority, milestone acceptance, experiment gates, and authorization. As a
result, any roadmap edit is classified `SCIENTIFIC`, including routine project
tracking and sequencing updates.

That classification conflates two different things:

- project planning and progress tracking, which should not itself constitute
  scientific evidence or a scientific decision; and
- binding research direction, protocol, acceptance criteria, and authorization,
  which must retain their scientific governance and review requirements.

Simply changing the path classification to `ORDINARY` would be unsafe while
the roadmap remains authoritative for scientific decisions. The authority and
content model must therefore be clarified before changing the classifier.

## Decision proposal

1. Reclassify `docs/roadmap.md` as an **ORDINARY project-planning and progress
   index**. It may describe workstreams, implementation dependencies, owners,
   status, and links to governing artifacts. Its edits alone do not define
   scientific truth, protocol, gates, acceptance, or authorization.
2. Keep binding scientific decisions in their appropriate governed artifacts:
   experiment protocols and preregistrations under `experiments/`, scientific
   methods under `docs/methodology/`, and accepted architecture/design
   decisions under their governed ADR/design records. Those sources remain
   `SCIENTIFIC`, `CONSTITUTIONAL`, or otherwise classified by their existing
   policy; this ADR does not lower their classification.
3. Amend ADR-0054 narrowly: the roadmap may summarize and link to scientific
   direction and gates, but it is not their authoritative source. Authority
   remains with the explicit owner-approved protocol, methodology, ADR, or
   other designated governed record. A roadmap entry cannot create or amend
   scientific authorization.
4. Before changing the path rule, audit the current roadmap for normative
   scientific content. For each such item, establish or identify its governed
   canonical source and replace the roadmap text with a concise summary and
   link. Do not alter experimental meaning, criteria, or evidence as part of
   this migration.
5. After that migration, remove `docs/roadmap.md` from the
   `scientific-direction` path rule while retaining `docs/methodology/**` and
   all other protected scientific paths. Update governance tests to establish
   both that roadmap-only planning edits classify as `ORDINARY` and that
   protected scientific artifacts remain `SCIENTIFIC`.

## Constraints

- `ORDINARY` means only that a planning/status edit is not by itself a
  scientific decision. It does not authorize changing a protocol, scientific
  result, acceptance criterion, or owner decision through an indirect roadmap
  edit.
- Do not use content heuristics or informal reviewer interpretation as a
  substitute for explicit canonical ownership of scientific decisions.
- Existing experiment records, frozen evidence, and active RUNNING work remain
  unchanged unless their owners authorize a separate change.
- This proposal does not implement the content migration, policy change, or
  governance-test changes before explicit owner acceptance.

## Consequences

- Routine roadmap maintenance can use the `ORDINARY` publication path after
  this decision is accepted and implemented.
- Scientific authority becomes more explicit and resides in purpose-built,
  governed records rather than a mixed planning document.
- The initial migration requires a careful audit because the current roadmap
  contains scientific direction and summaries of permanent invariants.
- A roadmap edit that attempts to change scientific meaning remains a
  governance violation even if its file classification is `ORDINARY`.

## Acceptance criteria

- [x] Project owner explicitly accepts this ADR on 2026-10-02.
- [x] ADR-0054's roadmap-authority clause is amended consistently with this
  decision.
- [x] Normative scientific roadmap content is preserved in a canonical governed
  source without changing its meaning or evidence.
- [x] `docs/roadmap.md` is reduced to planning/status and links, with no
  independent protocol, gate, acceptance, or authorization authority.
- [x] `change-surfaces.toml` classifies roadmap-only changes as `ORDINARY`
  while methodology and other protected scientific paths remain protected.
- [x] Governance tests verify both sides of that classification boundary.
- [x] Classifier behavior is validated against trusted `main` policy, with the
  policy-transition behavior and any required follow-up candidate documented.

## Decision

Accepted by the project owner on 2026-10-02. This authorizes separating the
project-planning index from scientific authority as described above. It does
not authorize changes to scientific meaning, protocols, results, criteria, or
experimental authorization. During the transition, classification against
trusted `main` continues to treat roadmap edits as `SCIENTIFIC`; the candidate
policy explicitly sets roadmap-only changes to `ORDINARY`, and retains
`SCIENTIFIC` classification for methodology. The roadmap's legacy
`external-review-required` artifact entry was removed so it does not override
the new ordinary planning classification. Follow-up roadmap changes become
`ORDINARY` only after this candidate is integrated.
