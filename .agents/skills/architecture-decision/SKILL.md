---
name: architecture-decision
description: Analyze, formulate, record, review, and supersede durable architectural decisions for Symbiont with explicit context, constraints, alternatives, consequences, evidence, and decision boundaries.
---

# Symbiont Architecture Decision Skill

## Purpose

Formulate and preserve durable architectural decisions in Symbiont.

The objective is not to generate ADR-shaped Markdown.

The objective is to ensure that important architectural choices can be understood later without reconstructing the entire discussion, repository history or implementation context.

A good architecture decision must explain:

- what problem required a decision;
- what the system actually looked like when the decision was made;
- which constraints governed the choice;
- which alternatives were genuinely available;
- what was decided;
- what was explicitly not decided;
- what consequences follow;
- what risks remain;
- how the decision relates to existing architecture, governance and scientific invariants;
- when the decision should be reconsidered or superseded.

An ADR records a decision.

It must not manufacture one.

---

# Operating Contract

When this skill is active, the agent MUST:

1. **Determine whether the subject actually requires an architectural decision record.**

2. **Reconstruct the current architectural reality before proposing a decision.**

3. **Distinguish facts, constraints, preferences, assumptions and unresolved questions.**

4. **Identify the decision drivers explicitly.**

5. **Check applicable constitutional, scientific, governance and architectural invariants.**

6. **Identify plausible alternatives rather than constructing artificial strawman options.**

7. **Compare alternatives against the same relevant decision drivers.**

8. **State one explicit architectural decision when the ADR is accepted.**

9. **Define the decision boundary: what is decided and what remains outside scope.**

10. **Record positive and negative consequences honestly.**

11. **Separate architectural decision from implementation specification.**

12. **Link related ADRs, specifications, experiments and documentation where relevant.**

13. **Preserve historical uncertainty when reconstructing an undocumented past decision.**

14. **Define supersession or reconsideration conditions where useful.**

The agent MUST NOT:

- create an ADR merely because a change is large;
- create an ADR for trivial implementation details;
- invent historical motivations;
- present an unresolved proposal as an accepted decision;
- describe one reasonable option and several obviously inferior strawmen;
- hide costs or risks of the selected option;
- turn an ADR into an implementation plan;
- turn an ADR into a scientific preregistration;
- turn an ADR into exhaustive reference documentation;
- silently override an existing accepted ADR;
- assume current implementation proves the original architectural rationale;
- declare constitutional compatibility without checking the relevant invariant.

---

# Normative Language

## MUST / MUST NOT

Mandatory decision-record invariant.

## SHOULD / SHOULD NOT

Default architectural practice.

Deviation requires a concrete reason.

## MAY

Optional technique or ADR section where useful.

---

# Use This Skill When

Use this skill when the task involves a durable architectural decision such as:

- changing responsibilities between architectural domains;
- introducing or removing a canonical authority;
- changing ownership of important state;
- changing lifecycle or persistence semantics;
- changing provenance guarantees;
- changing contracts between major components;
- introducing a new execution model;
- changing governance architecture;
- changing experimental infrastructure architecture;
- changing checkpoint or restore semantics;
- changing re-embodiment architecture;
- introducing a new canonical representation;
- replacing one architectural mechanism with another;
- deciding among multiple viable long-term technical strategies;
- establishing a policy future agents must understand;
- accepting a significant architectural trade-off.

---

# Do Not Use This Skill When

Do not use this skill as the primary workflow for:

- local bug fixes;
- mechanical refactors;
- renames;
- formatting changes;
- routine dependency updates;
- small performance optimizations;
- implementation details already dictated by an accepted ADR or specification;
- scientific hypothesis testing — use `scientific-experiment`;
- empirical root-cause analysis — use `scientific-investigation`;
- performance attribution — use `performance-investigation`;
- canonical scientific explanation — use `scientific-documentation`;
- general governance enforcement — handled by `agentctl`, `AGENTS.md` and repository governance.

If implementation work reveals that an accepted architectural assumption is no longer valid, an ADR review MAY become appropriate.

---

# ADR vs. Other Artifacts

Keep decision records distinct from neighboring artifacts.

## ADR

Answers:

> What architectural choice are we making, and why?

It records:

- context;
- decision;
- alternatives;
- consequences;
- architectural constraints.

## Specification

Answers:

> Exactly what behavior or contract must exist?

It defines:

- schemas;
- invariants;
- interfaces;
- algorithms;
- required behavior;
- acceptance conditions.

## Implementation Plan

Answers:

> How will we implement the decision?

It contains:

- tasks;
- migration sequence;
- file changes;
- rollout order;
- engineering steps.

## Scientific Experiment

Answers:

> How will we empirically test a scientific hypothesis?

It contains:

- hypotheses;
- controls;
- seeds;
- horizons;
- falsification criteria.

## Scientific Documentation

Answers:

> How does the system actually work?

It reconstructs:

- phenomena;
- mechanisms;
- state;
- evidence;
- causality.

Do not collapse these artifact types.

---

# ADR Qualification Test

Before creating an ADR, ask:

1. Does more than one reasonable architectural option exist?
2. Will the choice constrain future implementation?
3. Does the decision affect important boundaries, ownership or lifecycle semantics?
4. Will future maintainers or agents need to know why this choice exists?
5. Would removing the surrounding discussion make the code alone insufficient to understand the choice?
6. Does the decision have meaningful trade-offs or consequences?
7. Is the decision expected to remain relevant beyond one implementation task?

If most answers are no, an ADR is probably unnecessary.

Prefer a specification, issue, code comment or normal documentation instead.

---

# Architecture Decision Workflow

```text
IDENTIFY DECISION
        ↓
RECONSTRUCT CURRENT REALITY
        ↓
IDENTIFY CONSTRAINTS
        ↓
DEFINE DECISION DRIVERS
        ↓
IDENTIFY REAL ALTERNATIVES
        ↓
COMPARE CONSEQUENCES
        ↓
CHECK INVARIANTS
        ↓
FORMULATE DECISION
        ↓
DEFINE SCOPE / NON-GOALS
        ↓
RECORD CONSEQUENCES
        ↓
LINK RELATED ARTIFACTS
        ↓
ACCEPT / REJECT / DEFER
```

---

# Phase 1: Identify the Decision

Begin with the decision that actually needs to be made.

Avoid beginning with a preferred implementation.

Poor:

> ADR: Add `ProtocolGeneratedSnapshotSource`.

Better:

> How should governed scientific runs represent protocols whose initial state is generated deterministically rather than loaded from an archived snapshot?

The first formulation starts from a solution.

The second identifies the architectural decision.

A decision statement SHOULD be understandable without knowing the proposed implementation.

---

# Phase 2: Reconstruct Current Reality

Before proposing a new architecture, establish what currently exists.

Inspect where relevant:

- current implementation;
- accepted ADRs;
- Constitution;
- AGENTS.md;
- scientific specifications;
- schemas;
- persistence formats;
- lifecycle rules;
- tests;
- experiments;
- current consumers;
- migration constraints.

Distinguish:

```text
CURRENT IMPLEMENTATION
```

from:

```text
DOCUMENTED INTENTION
```

from:

```text
HISTORICAL DESIGN
```

from:

```text
PROPOSED FUTURE STATE
```

Do not write an ADR from stale documentation alone.

---

# Phase 3: Identify Constraints

Constraints are conditions the decision must respect.

Possible sources include:

## Constitutional constraints

Examples:

- epistemic separation;
- organism autonomy;
- evaluator non-leakage;
- observer passivity;
- persistence invariants.

## Architectural constraints

Examples:

- domain ownership;
- canonical source of truth;
- API compatibility;
- serialization compatibility;
- lifecycle semantics.

## Scientific constraints

Examples:

- reproducibility;
- held-out isolation;
- provenance;
- falsifiability;
- comparability across revisions.

## Governance constraints

Examples:

- frozen artifacts;
- agentctl lifecycle;
- scientific-run provenance;
- migration rules.

## Operational constraints

Examples:

- backwards compatibility;
- platform support;
- runtime cost;
- deployment model.

Do not confuse constraints with preferences.

---

# Constraints vs. Preferences

Label the distinction internally.

Example:

```text
CONSTRAINT:
A scientific run must preserve reproducible provenance.

PREFERENCE:
The CLI should remain simple.

CONSTRAINT:
World must not import organism cognition.

PREFERENCE:
Avoid adding another adapter layer.
```

Preferences may influence the decision.

Constraints bound it.

Do not reject a viable architecture merely because it violates a preference.

Do not accept an architecture that violates a mandatory constraint.

---

# Phase 4: Decision Drivers

Decision drivers explain what matters most when comparing alternatives.

Possible drivers include:

- constitutional compatibility;
- scientific integrity;
- provenance;
- conceptual simplicity;
- ownership clarity;
- reversibility;
- migration cost;
- runtime performance;
- observability;
- testability;
- extensibility;
- backwards compatibility;
- operational burden;
- failure containment.

Use only drivers relevant to the decision.

Do not create a generic scoring framework for every ADR.

---

# Phase 5: Identify Real Alternatives

Consider plausible architectural alternatives.

A useful alternative must be something a competent engineer or researcher could reasonably choose.

Avoid:

```text
Option A — correct design
Option B — obviously unsafe design
Option C — do nothing and accept everything breaking
```

Prefer genuine alternatives such as:

```text
A. Extend the existing abstraction.
B. Introduce a new first-class abstraction.
C. Keep separate mechanisms with an explicit adapter.
D. Preserve current architecture and constrain the new use case.
```

The current architecture is often a legitimate alternative.

Include it when relevant.

---

# No Strawman Rule

Every alternative included in an ADR SHOULD receive a fair description.

For each material option, state where relevant:

- how it works;
- what it preserves;
- what it simplifies;
- what it complicates;
- what risks it introduces;
- what migration it requires.

Do not exaggerate weaknesses of rejected options merely to justify the chosen one.

---

# Phase 6: Compare Alternatives

Compare alternatives using the same relevant drivers.

A concise table MAY be useful.

Example:

```text
                       A       B       C
Provenance             strong  strong  weak
Migration cost         low     medium  none
Conceptual clarity     medium  strong  weak
Compatibility          strong  medium  strong
```

Do not assign arbitrary numerical scores unless quantitative scoring is genuinely meaningful.

The objective is understanding trade-offs, not producing a pseudo-objective winner.

---

# Phase 7: Check Architectural and Scientific Invariants

Before accepting a decision, determine whether it affects:

```text
World
Body
Embodiment
Symbiont
Lab
Observatory
```

or other architectural domains discovered in the current system.

Check for:

- ownership inversion;
- semantic leakage;
- ground-truth leakage;
- duplicated authority;
- hidden lifecycle coupling;
- persistence ambiguity;
- provenance loss;
- observability becoming causal;
- evaluator influence on subject behavior.

An ADR must not normalize a constitutional violation merely because implementation would be convenient.

---

# Phase 8: Formulate the Decision

The accepted decision SHOULD be short and unambiguous.

A useful decision statement answers:

```text
We will...
```

or:

```text
The system will treat...
```

or:

```text
X becomes the canonical authority for...
```

Avoid vague decisions such as:

> Improve support for generated protocols.

Prefer:

> Governed scientific runs will support two explicit initial-state provenance modes: archived snapshot and protocol-generated state. Both modes must produce equivalent provenance metadata at the run boundary.

The details belong in specifications and implementation.

---

# Decision Boundary

Every ADR SHOULD make clear what is decided and what is not.

## In scope

Examples:

- ownership;
- canonical representation;
- provenance model;
- lifecycle semantics;
- architectural boundary.

## Out of scope

Examples:

- exact CLI syntax;
- internal helper names;
- optimization strategy;
- UI presentation;
- experiment thresholds.

This prevents an ADR from accidentally freezing implementation details that were never intended as architectural commitments.

---

# Non-Goals

Use a `Non-goals` section when readers could reasonably misinterpret the scope.

Examples:

```text
This ADR does not define the manifest schema.
This ADR does not choose a serialization library.
This ADR does not change organism checkpoint semantics.
```

Do not add non-goals mechanically when the decision boundary is already obvious.

---

# Phase 9: Consequences

Record consequences honestly.

## Positive consequences

Examples:

- clearer authority;
- reduced duplication;
- stronger provenance;
- simpler lifecycle;
- better extensibility.

## Negative consequences

Examples:

- migration cost;
- additional abstraction;
- more explicit metadata;
- temporary compatibility layer;
- additional tests.

## Neutral consequences

Some effects are simply architectural facts.

Example:

> Existing snapshot-based runs remain supported.

Do not write consequences as marketing.

Every durable architectural choice has costs.

---

# Risks

Record material risks that remain after the decision.

Examples:

- migration may lose provenance;
- two representations may drift;
- compatibility code may become permanent;
- abstraction may be generalized prematurely;
- new ownership may create hidden coupling.

Where useful, include mitigations.

Do not turn the ADR into a full risk register.

---

# Reversibility

Determine how difficult the decision is to reverse.

Possible classifications:

```text
easy to reverse
moderately reversible
expensive to reverse
effectively irreversible after persisted data exists
```

This classification is descriptive.

It is not mandatory for trivial decisions.

For expensive-to-reverse decisions, require stronger justification.

---

# Migration and Compatibility

When the decision changes an existing architecture, determine:

- what existing state exists;
- what remains compatible;
- what requires migration;
- whether dual-read or dual-write periods exist;
- how old persisted artifacts are handled;
- when compatibility code may be removed.

Do not hide migration consequences in implementation tickets.

An ADR should state the architectural migration commitment even if the exact implementation belongs elsewhere.

---

# Prospective vs. Retrospective ADRs

## Prospective ADR

Records a decision before or during implementation.

This is the preferred case.

The ADR may state:

```text
Status: Proposed
```

and later:

```text
Status: Accepted
```

## Retrospective ADR

Use when an important architectural decision already exists in implementation but was never formally recorded.

A retrospective ADR MUST distinguish:

- what can be demonstrated from history;
- what is inferred;
- what motivation is unknown.

Do not invent the original reasoning.

Example:

```text
The architecture has used X since at least revision Y.

The original motivation is not recoverable from available evidence.

This ADR records X as the current accepted architecture because...
```

The present-day reason for retaining an architecture is not necessarily the original reason it was introduced.

---

# Historical Honesty

Do not rewrite project history to make architecture appear more deliberate than it was.

If the system evolved incrementally, say so.

If two mechanisms coexist because of historical accumulation rather than deliberate design, say so.

If the original decision cannot be reconstructed, say so.

An ADR exists to preserve understanding, not to manufacture architectural mythology.

---

# ADR Status Model

Use the repository's canonical status model.

A useful default model is:

## Proposed

Decision is under review.

No architectural commitment exists yet.

## Accepted

Decision is authoritative.

Implementation should align with it.

## Rejected

Proposal was considered and explicitly not adopted.

## Superseded

A later ADR replaces the decision.

Reference the superseding ADR.

## Deprecated

The decision remains historically valid but should no longer guide new implementation.

## Historical

Use only when the repository recognizes this state.

It may describe a past architectural reality without asserting current authority.

Do not invent new status values when canonical statuses already exist.

---

# Unresolved Decisions

Do not mark an ADR `Accepted` when key architectural questions remain unresolved.

Possible outcomes include:

```text
Proposed
Deferred
Rejected
```

if those statuses exist in the repository.

A decision record may document unresolved questions.

It must not disguise them as settled.

---

# Supersession

Architectural decisions evolve.

When a new ADR replaces an earlier one:

1. reference the previous ADR;
2. state exactly what is superseded;
3. preserve historical reasoning;
4. update the old ADR status;
5. link both directions where repository conventions allow.

Do not silently edit an accepted historical ADR to make it match the new architecture.

Preserve the decision history.

---

# Partial Supersession

A later decision may replace only part of an earlier ADR.

State the boundary explicitly.

Example:

```text
ADR-0061 supersedes ADR-0048 only for scientific-run input provenance.
ADR-0048 remains authoritative for frozen artifact immutability.
```

Avoid declaring entire ADRs obsolete when only one decision clause changed.

---

# ADR Relationship Types

Where useful, record relationships such as:

```text
supersedes
superseded_by
extends
depends_on
constrains
implements
clarifies
related_to
```

Use repository conventions where defined.

Do not invent relationship types merely for stylistic variety.

---

# Evidence and Claims

An ADR may reference:

- source code;
- existing ADRs;
- experiments;
- benchmark results;
- incidents;
- scientific findings;
- documentation.

Understand the role of that evidence.

Evidence may establish:

```text
current architecture
observed limitation
measured cost
scientific constraint
```

It does not automatically determine the architectural choice.

The decision remains a design decision informed by evidence.

---

# Architecture Decisions and Scientific Evidence

Scientific results may motivate architecture.

Do not rewrite scientific findings into architectural facts.

Example:

```text
Experiment:
Candidate promotion showed measurable churn.

Architectural decision:
Promotion policy will require margin-aware evaluation.
```

The ADR may cite the result.

It must preserve the distinction between:

```text
observed evidence
```

and:

```text
chosen architectural response
```

---

# Avoid Premature Generalization

Do not create abstractions for hypothetical futures without evidence of need.

Before choosing a generalized architecture, ask:

- is there more than one real use case?
- does current architecture genuinely block extension?
- is the abstraction boundary stable?
- are we generalizing a mechanism or merely renaming it?

Prefer the smallest architecture that resolves the real decision while preserving legitimate future extension.

---

# Validation Plan

An ADR SHOULD explain how implementation conformance will be validated when this is architecturally important.

Examples:

- contract tests;
- migration tests;
- equivalence suite;
- architectural import checks;
- schema validation;
- provenance assertions;
- persistence round-trip tests.

Do not turn this section into a complete test plan.

State only the validation properties that make the architectural decision enforceable.

---

# ADR Structure

Use the repository's canonical ADR template if one exists.

Otherwise, a substantial ADR SHOULD contain:

```markdown
# ADR-XXXX — [Decision title]

- Status:
- Date:
- Decision owner:
- Relates to:

## Context

Describe the architectural problem and current reality.

## Decision Drivers

List the constraints and considerations that matter.

## Constraints and Invariants

Record mandatory boundaries.

## Alternatives Considered

Describe real alternatives fairly.

## Decision

State the architectural choice explicitly.

## Scope

Clarify what the decision covers.

## Non-goals

Clarify likely misunderstandings where useful.

## Consequences

### Positive

### Negative

### Neutral

## Risks

Record material risks that remain after the decision.

## Migration and Compatibility

Describe architectural migration commitments where relevant.

## Validation

State how conformance will be demonstrated.

## Relationships

Record supersedes / depends_on / related ADRs or specifications.

## Reconsideration Conditions

State what future evidence or system change would justify reopening the decision.
```

Not every ADR needs every section.

Remove empty sections rather than filling them with boilerplate.

---

# ADR Title Discipline

The title SHOULD describe the decision, not the implementation task.

Poor:

```text
ADR-0054 — Update agentctl
```

Better:

```text
ADR-0054 — Support protocol-generated scientific run inputs
```

Poor:

```text
ADR-0061 — Refactor persistence
```

Better:

```text
ADR-0061 — Make organism bundles the canonical persistence boundary
```

Titles should remain meaningful when implementation details change.

---

# Reconsideration Conditions

Where useful, state what would justify reopening the decision.

Examples:

```text
Reconsider if protocol-generated runs require external mutable state.
```

```text
Reconsider if checkpoint format no longer preserves organism lineage.
```

```text
Reconsider if observability becomes distributed across multiple processes.
```

This is especially useful for decisions based on current constraints that may change.

Do not add arbitrary review dates unless the decision is genuinely time-sensitive.

---

# ADR Review Workflow

When reviewing a proposed ADR:

1. verify that an architectural decision actually exists;
2. verify current-state claims against repository evidence;
3. identify hidden assumptions;
4. inspect relevant accepted ADRs;
5. check constitutional and scientific invariants;
6. verify that alternatives are real;
7. look for strawman comparisons;
8. inspect whether implementation detail is being accidentally frozen;
9. inspect negative consequences;
10. inspect migration implications;
11. check whether the decision duplicates or contradicts existing authority;
12. determine whether the status is appropriate.

Do not approve an ADR merely because the proposed implementation seems reasonable.

---

# Decision Quality Gate

Before considering an ADR complete, ask:

- What exact architectural decision is being made?
- Why does it require an ADR?
- What is the current architecture?
- Which claims about the current system are demonstrated?
- What constraints are mandatory?
- Which concerns are only preferences?
- What are the decision drivers?
- Were plausible alternatives considered?
- Were alternatives described fairly?
- Does the decision violate any constitutional invariant?
- Is ownership clear?
- Is canonical authority clear?
- Are lifecycle effects clear?
- Are persistence and provenance effects clear where relevant?
- Is the decision distinct from its implementation?
- Are non-goals clear where ambiguity is likely?
- Are negative consequences recorded?
- Are migration obligations visible?
- Does another ADR already govern this question?
- Is supersession handled explicitly?
- Is the status honest?
- Could a future agent understand why this architecture exists?

If important answers are missing, the decision record is incomplete.

---

# Completion Report

After creating or revising an ADR, report concisely:

## Decision

The architectural choice recorded.

## Status

Proposed, Accepted, Rejected, Superseded or other canonical state.

## Alternatives

Material alternatives considered.

## Constraints

Important invariants affecting the decision.

## Consequences

The most important positive and negative consequences.

## Relationships

Related or superseded ADRs/specifications.

## Open Questions

Only questions genuinely outside the accepted decision.

Do not restate the entire ADR.

---

# Final Principle

An ADR is institutional memory for a decision.

It should allow a future engineer, researcher or agent to answer:

```text
What problem existed?
        ↓
What was true at the time?
        ↓
What constraints applied?
        ↓
What alternatives existed?
        ↓
What did we decide?
        ↓
Why did we choose it?
        ↓
What did we deliberately not decide?
        ↓
What consequences did we accept?
        ↓
What would cause us to reconsider?
```

The objective is not architectural perfection.

The objective is durable clarity.

Do not invent history.

Do not hide trade-offs.

Do not confuse decision with implementation.

Do not turn proposals into facts.

Record the decision that actually exists, at exactly the scope that was actually decided.
