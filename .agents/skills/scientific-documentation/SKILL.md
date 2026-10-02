---
name: scientific-documentation
description: Reconstruct, maintain and validate the scientifically useful, self-contained and human-readable documentation of Symbiont from implementation and evidence.
---

# Symbiont Scientific Documentation Skill

## Purpose

Maintain a scientifically useful, self-contained and human-readable body of documentation for Symbiont.

The objective is not to document the repository as a collection of files, classes, functions or APIs.

The objective is to reconstruct, explain and preserve how Symbiont actually works so that a future researcher can study the organism without needing its original authors to explain the system.

Documentation must allow a reader to move from an observed phenomenon to its causal mechanisms, state, evidence and implementation — and back again.

The methodology must remain useful as Symbiont evolves and develops mechanisms, processes, domains, representations and phenomena that do not exist today.

---

# Operating contract

When this skill is active, the agent MUST:

1. establish the scope of the documentation task;
2. inspect relevant existing documentation before writing;
3. identify canonical terminology and existing documentation authority;
4. inspect the current implementation relevant to the subject;
5. inspect available tests and scientific evidence where they can materially support the explanation;
6. reconstruct the phenomenon from human meaning to implementation;
7. distinguish intention, implementation, tested behavior, observed behavior, inference and uncertainty;
8. preserve architectural, semantic, temporal and ownership boundaries;
9. integrate knowledge into the existing canonical documentation rather than creating unnecessary competing explanations;
10. preserve contradictions when the available evidence disagrees;
11. validate the resulting documentation after modification;
12. report unresolved uncertainty and meaningful scientific findings.

The agent MUST NOT:

- infer behavior solely from class, function, variable, file or module names;
- present intended behavior as implemented behavior;
- present implemented behavior as runtime-observed behavior without runtime evidence;
- present one execution as a universal property;
- invent missing mechanisms, states, causal relationships or semantics;
- silently reconcile contradictory evidence;
- attribute developer or UI semantics to Symbiont without evidence that the organism itself possesses the corresponding information;
- create parallel canonical explanations without an explicit reason;
- change production behavior unless the task explicitly requests implementation work.

Documentation is not complete merely because text has been written.

---

# Normative language

This skill uses the following terms deliberately.

## MUST / MUST NOT

Mandatory invariant.

Deviation is not allowed unless the task itself explicitly overrides the requirement.

## SHOULD / SHOULD NOT

Default behavior.

Deviation is allowed only when there is a concrete reason grounded in the repository, evidence or documentation structure.

## MAY

Optional technique that can be used when useful.

## Examples

Examples illustrate possible forms.

They do not define exhaustive taxonomies, mandatory categories or architectural constraints.

Symbiont may contain mechanisms not anticipated by this skill.

Discover first.

Classify afterwards.

---

# Use this skill when

Use this skill when the primary task involves one or more of the following:

- documenting how Symbiont works;
- reconstructing behavior from code, tests, runtime evidence or experiments;
- explaining a process from macro to micro;
- discovering undocumented phenomena, processes or causal chains;
- updating scientific documentation after implementation changes;
- documenting cognitive, physical, sensorimotor, developmental or architectural mechanisms;
- tracing how an observed phenomenon is produced;
- tracing how state is created, transformed, consumed, persisted, restored or lost;
- documenting causal provenance;
- documenting system boundaries and domain ownership;
- creating or maintaining scientific anatomies;
- creating evidence-based runtime journeys;
- maintaining the scientific atlas or conceptual graph;
- reconciling discrepancies between documentation, implementation, tests, persisted state, runtime evidence or experiments;
- reorganizing scientific documentation when its current structure obscures understanding;
- translating or restructuring scientific documentation without changing its meaning;
- auditing documentation for scientific completeness, consistency or canonicality;
- preparing the repository so that future researchers can understand it independently.

---

# Do not use this skill when

Do not use this skill as the primary workflow for:

- implementing application logic;
- fixing runtime bugs;
- changing algorithms;
- modifying organism behavior;
- refactoring production code;
- changing CI/CD;
- modifying infrastructure;
- ordinary repository maintenance;
- writing product requirements;
- writing implementation specifications;
- writing release notes;
- running test suites solely to validate unrelated code changes;
- correcting trivial code typos that do not affect scientific documentation.

If documentation work reveals a defect, architectural inconsistency, provenance problem or missing behavior, record the finding.

Do not silently repair the implementation unless the task explicitly requests implementation work.

---

# Work modes

Before beginning substantial work, determine which mode best describes the task.

## 1. Reconstruction

Use when a phenomenon is missing, poorly documented, scientifically ambiguous or insufficiently understood.

Start from the phenomenon and current implementation.

Investigate evidence rather than assuming existing documentation is correct.

Typical direction:

```text
phenomenon
→ runtime path
→ state
→ transformations
→ consequences
→ implementation
→ evidence
```

## 2. Incremental update

Use when implementation has changed and existing scientific documentation may now be stale.

Start from the change.

Determine:

```text
changed implementation
→ affected mechanism
→ affected phenomenon
→ affected state or causality
→ affected documentation
```

Update only what the change actually invalidates or extends.

Do not regenerate unrelated documentation.

## 3. Documentation audit

Use when evaluating the scientific quality, consistency, organization or completeness of the documentation corpus.

Investigate:

- missing explanations;
- duplicate authority;
- stale claims;
- contradictions;
- terminology drift;
- broken causal chains;
- unsupported assertions;
- missing implementation traceability;
- missing evidence;
- structural ambiguity.

Do not change implementation during a documentation audit unless separately instructed.

## 4. Translation or restructuring

Use when existing scientific content must be translated, reorganized or reformatted without altering its scientific meaning.

Preserve claims, uncertainty, terminology, causal meaning, code, equations and document purpose.

Translation is not permission to improve or reinterpret scientific claims.

---

# Primary reader

Write for a future researcher who:

- has never spoken with the original authors;
- does not know the history of the project;
- does not know the internal terminology;
- does not know where the relevant implementation lives;
- cannot ask anyone what an ambiguous sentence means;
- must determine what the organism does;
- must determine how it does it;
- must determine under which conditions it does it;
- must determine what evidence supports that interpretation.

The documentation must stand on its own.

---

# Core scientific principle

The fundamental unit of scientific documentation is the phenomenon, not the file.

A phenomenon may be:

- a perception;
- an action;
- a prediction;
- a learning event;
- a memory change;
- a structural change;
- an interaction;
- a decision;
- a state transition;
- an embodiment event;
- an information transformation;
- a temporal transition;
- a causal dependency;
- a developmental event;
- or a form of behavior not yet known.

Do not assume that the currently known phenomena form a complete taxonomy.

A useful documentation path is:

```text
phenomenon
↓
process
↓
mechanism
↓
state
↓
algorithm
↓
implementation
```

The reverse direction must also be possible:

```text
implementation
↓
mechanism
↓
process
↓
observable consequence
↓
role in the organism
```

Important code must have interpretable scientific meaning.

Important scientific claims must have traceable evidence.

---

# Canonical documentation rule

Before creating a new document, determine whether the subject already has a canonical home.

Prefer, in order:

1. extending an existing canonical document;
2. correcting an existing canonical document;
3. adding a specialized document linked from the canonical explanation;
4. creating a new canonical document only when no suitable home exists.

Do not create competing explanations of the same phenomenon merely because creating a new file is easier.

If several existing documents claim authority over the same subject:

1. identify the competing authorities;
2. determine whether they serve genuinely different purposes;
3. determine which one is canonical, if possible;
4. link specialized documents to the canonical explanation;
5. report unresolved authority ambiguity as a documentation finding.

The scientific corpus should behave as a connected body of knowledge, not as isolated Markdown pages.

---

# Existing documentation is evidence, not ground truth

Existing documentation may contain:

- valid explanations;
- historical assumptions;
- intended behavior;
- stale architecture;
- superseded mechanisms;
- unresolved contradictions;
- terminology that no longer matches the implementation.

When documenting current behavior, do not stop after reading existing documentation.

Scientifically important claims SHOULD be verified against the current implementation and, when relevant, tests, persisted state, runtime evidence or experiments.

Do not silently preserve a claim merely because it was previously documented.

Do not silently delete historical information when it remains scientifically relevant.

---

# Scientific honesty

Never infer behavior from naming alone.

A class called:

```text
Memory
```

does not prove the existence of memory.

A subsystem called:

```text
Reasoning
```

does not prove reasoning.

A value called:

```text
confidence
```

does not prove that the organism possesses the semantic concept of confidence.

Determine what operations actually occur and what evidence the organism actually possesses.

Always distinguish:

- documented intention;
- implemented mechanism;
- tested behavior;
- runtime-observed behavior;
- experimentally supported conclusion;
- inferred interpretation;
- uncertainty;
- contradiction.

Do not silently collapse these categories.

---

# No semantic elevation

Do not promote an external interpretation into an organism property.

Developer terminology, UI labels, telemetry labels and documentation terminology may describe a system from an external point of view.

They do not by themselves establish that Symbiont possesses the corresponding semantic concept.

For potentially semantic concepts such as:

- self;
- world;
- object;
- goal;
- confidence;
- intention;
- prediction;
- memory;
- decision;
- cause;
- agency;
- representation;
- value;
- meaning;

trace the strongest justified chain:

```text
external interpretation
↓
represented information
↓
operations actually performed
↓
evidence available to the organism
↓
behavior supported by that evidence
↓
scientifically justified interpretation
```

Stop at the strongest interpretation supported by evidence.

Do not cross the remaining semantic gap by assumption.

---

# Human-first explanation

Always explain the phenomenon before the implementation.

Do not begin with:

> `XManager.execute()` invokes `YResolver`.

Begin with what happens and why it matters.

Then progressively explain:

1. what happens;
2. under which conditions;
3. why the event matters;
4. which domains participate;
5. what information crosses each boundary;
6. what state is read;
7. what state changes;
8. what causality flows;
9. what becomes possible afterwards;
10. which mechanisms implement it;
11. where the implementation lives;
12. which evidence supports the explanation.

Code demonstrates the explanation.

Code must not replace the explanation.

---

# Progressive depth

Important subjects SHOULD be understandable at several depths.

## Human level

What happens without requiring knowledge of the code.

## System level

Which domains and subsystems participate.

## Causal level

What produces what and under which conditions.

## Runtime level

What executes and in what order.

## State level

What information is created, read, modified, retained, restored or destroyed.

## Temporal level

Which clocks or lifetimes matter.

## Algorithmic level

Which rules or computations produce the behavior.

## Implementation level

Which concrete symbols implement it.

## Evidence level

What proves or supports each important interpretation.

Each level must deepen the same explanation.

Do not replace the original question with an unrelated implementation explanation merely because the lower-level detail is easier to describe.

---

# Architectural boundaries

Respect boundaries demonstrated by the current architecture.

For current Symbiont architecture, investigate carefully whether the following distinction remains valid:

```text
World != Body != Embodiment != Symbiont
```

Do not assume this list is eternally complete.

If new domains appear, discover and document them.

Where relevant, also distinguish:

```text
physical reality
!= sensed information
!= transmitted signal
!= internal representation
!= learned interpretation
!= developer interpretation
!= UI representation
```

Document what crosses each boundary.

Document what does not cross each boundary.

Never attribute external semantics to Symbiont unless the organism has evidence supporting that meaning.

---

# Evidence model

Use multiple evidence sources when the importance of the claim justifies it.

Possible sources include:

- production code;
- unit tests;
- integration tests;
- boundary tests;
- experimental integrity tests;
- checkpoints;
- persisted state;
- runtime traces;
- telemetry;
- study outputs;
- experimental results;
- scientific specifications;
- ADRs;
- historical documentation.

Understand what each source can prove.

A specification supports intended design.

Code supports implementation.

A test supports behavior under the conditions exercised by the test.

Persisted state supports the existence of recorded state at a particular point.

A runtime trace supports what occurred during that execution.

An experiment supports conclusions only within its stated design and conditions.

Historical documentation supports previous interpretation or design, not necessarily current truth.

---

# Minimum evidence discipline

Before making an important claim, determine what kind of claim it is.

Use the following as a minimum guide.

| Claim | Minimum basis |
|---|---|
| A symbol or mechanism exists | Current implementation |
| A runtime path is possible | Implementation plus its enabling conditions |
| A behavior is protected against regression | Appropriate test |
| An event occurred | Runtime, telemetry, persisted state or equivalent evidence |
| State survives a lifecycle boundary | Persistence/restore path plus supporting evidence |
| A behavior is general | Evidence beyond one isolated execution |
| X causally produces Y | Causal mechanism plus evidence appropriate to the claim |
| X improves Y | Comparative experiment or equivalent controlled evidence |
| A behavior is intended | Specification, ADR or explicit design documentation |
| A semantic interpretation belongs to the organism | Evidence available to the organism, not merely external naming |

This table defines a minimum discipline, not an exhaustive scientific method.

Stronger claims require stronger evidence.

---

# Evidence status

Maintain an internal distinction between evidence statuses such as:

```text
CONFIRMED_BY_CODE
CONFIRMED_BY_TEST
CONFIRMED_BY_RUNTIME
SUPPORTED_BY_EXPERIMENT
DOCUMENTED_INTENT
INFERRED
UNCERTAIN
CONTRADICTED
```

These labels do not need to appear mechanically in normal prose.

Prefer natural wording.

Examples:

> The implementation and boundary tests support this interpretation.

> The design document describes X, while the current runtime path performs Y.

> The code permits this transition, but no runtime evidence examined here demonstrates that it has occurred.

---

# Contradictions

Never silently resolve discrepancies.

Relevant conflicts may include:

```text
DOC / CODE
CODE / TEST
SPEC / RUNTIME
TEST / RUNTIME
STATE / PROVENANCE
EXPERIMENT / IMPLEMENTATION
CANONICAL DOC / CANONICAL DOC
```

When evidence disagrees, explain:

1. what each source states or demonstrates;
2. what is currently supported;
3. what is contradicted;
4. what remains uncertain;
5. whether the discrepancy is historical, implementation-related, evidential or documentary;
6. what evidence would resolve it.

Scientific documentation must preserve uncertainty where uncertainty exists.

---

# Causal reconstruction

Whenever possible, reconstruct actual causal chains.

Do not merely list dependencies.

Investigate:

```text
what happened
↓
what made it possible
↓
what information was available
↓
what transformation occurred
↓
what state changed
↓
what consequence followed
↓
what became possible afterwards
```

A possible chain may look like:

```text
world event
↓
physical consequence
↓
sensed signal
↓
internal transformation
↓
internal evidence
↓
learning / selection / control
↓
new state
↓
future consequence
```

This is only an example.

Never force this shape onto a mechanism that behaves differently.

Discover the actual causal structure.

---

# Causal history and provenance

Do not confuse current state with the history that produced it.

Equivalent current values may have different causal histories.

Where the system preserves sufficient information, document:

```text
current state
← derived from
previous state
← modified by
process
← using
evidence
← derived from
observation
```

Determine whether causal provenance survives:

- checkpoints;
- restores;
- re-embodiment;
- process restarts;
- serialization;
- migration;
- inheritance;
- experimental snapshots;
- version transitions.

If state survives but causal history does not, say so explicitly.

Persistence of value is not necessarily persistence of provenance.

---

# State analysis

For every scientifically important state, determine:

- what it represents;
- which domain owns it;
- where it is created;
- what may modify it;
- what may observe it;
- what consumes it;
- how long it lives;
- what depends on it;
- whether it is persisted;
- whether it is restored;
- whether it is organism-specific;
- whether it is embodiment-specific;
- whether it is body-specific;
- whether it is world-specific;
- whether it survives re-embodiment;
- whether it survives process restart;
- what previous state contributed to it;
- whether its causal provenance survives with it.

Do not assume current state categories are exhaustive.

If a new form of persistence, continuity, ownership or state appears, document it according to its actual behavior.

---

# Time analysis

Do not assume a single clock.

Discover every temporal domain relevant to the phenomenon.

Possible examples include:

- physics time;
- world time;
- organism lifetime;
- embodiment lifetime;
- body lifetime;
- developmental time;
- cognitive cycles;
- training cycles;
- experimental time;
- generations;
- snapshot sequence;
- wall-clock time.

For each relevant clock determine:

- what advances it;
- what depends on it;
- whether it can pause;
- whether it can skip;
- whether it resets;
- whether it survives re-embodiment;
- whether it survives restart;
- whether it is persisted;
- how it relates to other clocks.

Do not use the word "time" ambiguously when several clocks participate.

---

# Repository exploration strategy

Do not read the repository linearly.

Begin by locating:

- relevant entry points;
- runtime orchestrators;
- domain boundaries;
- state owners;
- lifecycle boundaries;
- persistence paths;
- event flows;
- tests covering critical behavior;
- scientific specifications or experiments tied to the phenomenon.

Then follow causal paths.

Prefer:

```text
phenomenon
→ entry point
→ runtime path
→ state
→ transformation
→ downstream consequence
→ evidence
```

over:

```text
folder
→ file
→ class
→ next file
```

Repository structure is a navigation aid.

It is not the scientific explanation.

---

# Scientific anatomies

Create an anatomy when an important phenomenon benefits from an end-to-end explanation.

Possible examples include:

- Anatomy of a Perception;
- Anatomy of an Action;
- Anatomy of Learning;
- Anatomy of a Tick;
- Anatomy of Re-embodiment;
- Anatomy of a Decision.

These are examples, not required categories.

An anatomy should begin with:

> What happens?

and progressively reach:

> Exactly how does the implementation make it happen?

An anatomy SHOULD connect:

```text
phenomenon
↔ boundaries
↔ information
↔ state
↔ causal sequence
↔ implementation
↔ evidence
```

Do not create an anatomy solely to fill a documentation structure.

---

# Scientific journeys

Use a scientific journey when several mechanisms must be understood together through one continuous event.

Examples might include:

- encountering something unfamiliar;
- an unexpected outcome affecting later behavior;
- entering a new body;
- failing a prediction;
- acquiring a new competence;
- preserving or losing state across a lifecycle boundary.

Scientific journeys are not fictional stories.

They must be evidence-based reconstructions.

Clearly distinguish:

```text
general mechanism
```

from:

```text
one observed execution
```

A concrete execution can demonstrate interaction between mechanisms.

It must not be generalized beyond the evidence.

---

# Future-proof discovery

This skill is not limited to mechanisms currently known.

Every investigation must remain capable of discovering new:

- domains;
- phenomena;
- processes;
- states;
- clocks;
- causal relationships;
- lifecycle events;
- forms of persistence;
- forms of memory;
- forms of learning;
- forms of perception;
- forms of action;
- forms of interaction;
- forms of cognition;
- forms of representation.

When something new appears:

1. identify the phenomenon;
2. determine its domain boundaries;
3. identify its state;
4. determine what feeds it;
5. determine what consumes it;
6. reconstruct its causal role;
7. determine its temporal behavior;
8. determine its persistence;
9. determine available evidence;
10. integrate it into existing explanations;
11. extend the documentation model only where required.

Never force a new mechanism into an old category merely to preserve the documentation structure.

The documentation model must evolve when the system evolves.

---

# Scientific Atlas

When the repository supports a structured conceptual model, maintain it as a map of scientific knowledge rather than a decorative index.

The atlas MAY represent:

- phenomena;
- processes;
- mechanisms;
- states;
- evidence;
- domains;
- causal relationships;
- temporal relationships;
- persistence relationships;
- provenance relationships.

Possible relationships include:

```text
PRODUCES
CONSUMES
DERIVES_FROM
MODIFIES
OBSERVES
CONTROLS
DEPENDS_ON
PRECEDES
PERSISTS_AS
RESTORES
ENABLES
INHIBITS
CONTRIBUTES_TO
```

The relationship vocabulary is extensible.

Do not constrain future scientific interpretation to today's relationship types.

Where practical, support navigation between:

```text
concept ↔ implementation
state ↔ producers
state ↔ consumers
phenomenon ↔ causal chain
experiment ↔ mechanism
mechanism ↔ tests
documentation ↔ evidence
```

---

# Diátaxis

Use Diátaxis as a separation-of-purpose framework.

Do not use it as a mandatory folder template.

The four common types are:

```text
Tutorial
How-to
Reference
Explanation
```

A document should have one clear primary purpose.

## Tutorial

A tutorial is a guided learning experience.

It should help a learner complete a coherent learning path.

Do not turn it into:

- an architecture essay;
- an encyclopedic reference;
- implementation history.

## How-to

A how-to solves a concrete practical problem.

It should be action-oriented.

Do not overload it with conceptual theory merely to make it look complete.

## Reference

Reference describes the system accurately and systematically.

It may contain:

- contracts;
- schemas;
- concepts;
- APIs;
- state definitions;
- symbols;
- invariants;
- data structures.

Reference prioritizes precision and lookup value.

Do not turn it into a tutorial or narrative essay.

## Explanation

Explanation builds understanding.

It may discuss:

- why a mechanism exists;
- how systems interact;
- conceptual models;
- causal interpretation;
- implications;
- architectural reasoning;
- scientific interpretation.

Do not turn it into operational instructions or exhaustive symbol listings.

---

# Empty quadrant rule

Do not create documentation merely to satisfy Diátaxis.

Never create:

- empty category folders;
- empty Markdown files;
- placeholder documents;
- fake tutorials;
- artificial examples;
- invented reader needs;
- speculative documentation whose content is not supported.

If only explanation and reference are useful, create only explanation and reference.

A missing category is preferable to invented content.

Structure follows actual knowledge and reader needs.

---

# Terminology discipline

If a glossary or canonical terminology exists:

1. load it before substantial writing, rewriting or translation;
2. use canonical terms consistently;
3. preserve distinctions that matter scientifically;
4. do not introduce synonyms merely for stylistic variation;
5. report missing concepts instead of improvising conflicting terminology.

The first meaningful use of an internal term should make clear:

- what it denotes;
- why it exists;
- what distinguishes it from nearby concepts.

Do not repeatedly redefine established terminology afterwards.

Humanization should come from sentence structure and explanation, not from destabilizing technical vocabulary.

---

# Translation and restructuring

When translating or restructuring scientific documentation, preserve meaning before style.

Do not:

- add scientific explanations that did not exist;
- remove uncertainty;
- strengthen claims;
- soften caveats;
- change causal meaning;
- change terminology inconsistently;
- alter code;
- alter equations;
- alter identifiers;
- alter diagram semantics;
- change examples unless necessary for the requested transformation.

Preserve the document's primary purpose.

A how-to remains a how-to.

Reference remains reference.

Explanation remains explanation.

Tutorial remains tutorial.

If the source appears scientifically wrong, contradictory or stale, report that separately.

Do not silently fix scientific meaning as part of translation.

---

# Humanization rule

Documentation must read like a scientific explanation written for another human.

Avoid prose dominated by repetitive schemas such as:

```text
Input:
Output:
State:
Method:
```

unless the document is intentionally reference-oriented.

Prefer explaining relationships and consequences.

For example:

> Once the observation has become internal evidence, downstream mechanisms no longer consume the physical event directly. They operate on the organism's internal state produced from that event.

Then provide the technical mapping separately.

Use technical detail where it increases precision.

Do not include technical detail merely because it exists.

---

# Code references

Use stable implementation references where possible.

Prefer:

```text
path/to/module.py::Class.method
```

or another durable symbol reference.

Do not rely primarily on line numbers in long-lived scientific documentation.

Line numbers MAY be useful temporarily during investigation.

The scientific explanation should remain meaningful even when implementation lines move.

---

# Reproducibility

When documenting conclusions derived from experiments or concrete executions, preserve enough information for another researcher to evaluate or reproduce them where practical.

Relevant information may include:

- repository revision;
- runtime version;
- organism identity or state;
- world;
- body;
- embodiment;
- configuration;
- initial conditions;
- seed;
- duration;
- relevant clocks;
- metrics;
- intervention;
- comparison baseline;
- acceptance criteria;
- observed result;
- uncertainty;
- limitations.

Never generalize beyond the conditions supported by the evidence.

---

# Historical evolution

Preserve history when it affects present scientific interpretation.

Examples include:

- a causal mechanism changed;
- state persistence changed;
- a learning rule changed;
- domain ownership changed;
- an organism boundary changed;
- a previously valid experimental result is no longer directly comparable;
- a terminology change would otherwise create scientific ambiguity.

Do not turn scientific documentation into a changelog.

History exists to explain scientific continuity and discontinuity.

---

# Findings

During investigation, record scientifically meaningful findings.

Possible examples:

- ambiguous ownership;
- semantic leakage;
- provenance loss;
- undocumented persistence;
- unexpected reset;
- dead execution path;
- contradictory test;
- specification drift;
- duplicated causal authority;
- competing canonical documentation;
- state that survives without provenance;
- terminology that overstates organism semantics.

Do not present every implementation detail as a finding.

Separate:

```text
scientifically relevant finding
```

from:

```text
ordinary implementation detail
```

A finding should matter to interpretation, reproducibility, causality, architecture or scientific understanding.

---

# Work in bounded batches

Do not perform uncontrolled bulk transformations across large documentation trees.

Large-context operations increase the risk of:

- terminology drift;
- broken code blocks;
- modified equations;
- lost frontmatter;
- ignored constraints;
- type drift;
- contradictory explanations;
- accidental omissions;
- duplicate authority.

A batch SHOULD correspond to a coherent unit such as:

- one phenomenon;
- one causal chain;
- one scientific domain;
- one anatomy;
- one documentation type;
- one tightly related group of documents.

Finish and validate one coherent batch before expanding the scope.

---

# Investigation workflow

For substantial documentation work, use the following cycle.

## 1. Orient

Determine:

- task scope;
- work mode;
- existing canonical documents;
- glossary and terminology;
- relevant domains;
- likely implementation areas;
- relevant evidence sources.

## 2. Discover

Trace the real system.

Identify:

- entry points;
- state owners;
- runtime paths;
- boundaries;
- transformations;
- persistence;
- clocks;
- causal consequences;
- supporting tests and evidence.

Do not write the final explanation before the phenomenon is sufficiently understood.

## 3. Reconstruct

Build a coherent scientific explanation from macro to micro.

Determine:

```text
phenomenon
→ conditions
→ information
→ boundaries
→ mechanisms
→ state transitions
→ consequences
→ implementation
→ evidence
```

Record uncertainty and contradictions.

## 4. Integrate

Determine where the knowledge belongs.

Prefer updating canonical documentation.

Create new documents only when the subject genuinely requires a new documentation unit.

Update cross-links, atlas relationships or related explanations where needed.

## 5. Verify

After each coherent batch:

- inspect the diff;
- check scientific meaning;
- check Markdown integrity;
- check frontmatter;
- check links where tooling exists;
- check anchors;
- check code fences;
- check diagrams;
- check equations;
- check terminology;
- check Diátaxis purpose;
- check evidence claims;
- check canonical authority;
- check that unsupported semantic elevation has not been introduced.

Do not begin another major batch while the current batch remains internally inconsistent.

---

# Incremental update workflow

When updating documentation after implementation changes:

1. determine exactly what changed;
2. identify the affected phenomena;
3. trace the changed runtime paths;
4. identify changed state, boundaries, causality or persistence;
5. inspect relevant tests and runtime evidence;
6. determine which existing explanations became stale;
7. update causal chains;
8. update relevant anatomies;
9. update reference material;
10. update scientific journeys only if their represented behavior changed;
11. update atlas relationships where applicable;
12. record discrepancies and uncertainty;
13. leave unaffected documentation unchanged.

Maintain a living scientific corpus.

Do not regenerate the documentation tree after every implementation change.

---

# Scientific questions gate

Before considering an important subject sufficiently documented, determine whether a future researcher can answer:

- What am I observing?
- Under what conditions can it happen?
- Why can it happen?
- Which domains participate?
- Which mechanisms participate?
- What information crosses each boundary?
- What information does not cross?
- What state is read?
- What state changes?
- What persists afterwards?
- What is lost?
- Which clock or lifetime matters?
- What caused the current state?
- What can the current state cause next?
- Which implementation performs the behavior?
- Which tests support the explanation?
- Which runtime evidence supports it?
- Which parts are design intent rather than demonstrated behavior?
- What remains uncertain?
- What contradictions remain?
- Can the observation or conclusion be reproduced?

If important answers are missing, the subject is not yet sufficiently documented.

---

# Definition of done

Scientific documentation is complete only when the important claims are legible and traceable.

For each scientifically significant claim, a future researcher should be able to determine:

- what is being claimed;
- whether it describes intent, implementation, tested behavior, observation, experiment or inference;
- what evidence supports it;
- under which conditions it is valid;
- which domains participate;
- which state participates;
- which causal chain produces the phenomenon;
- what persists and what does not;
- where the relevant implementation resides;
- what remains uncertain or contradicted.

The agent SHOULD also verify that:

- no unnecessary competing canonical document was created;
- terminology remains canonical;
- external semantics were not promoted into organism semantics without evidence;
- examples were not mistaken for exhaustive categories;
- current implementation was not replaced by historical intent;
- one concrete execution was not generalized into a universal behavior.

If these conditions are not satisfied, the task is incomplete.

---

# Required completion report

At the end of substantial documentation work, report concisely:

## Scope

What was investigated or updated.

## Documentation affected

Documents:

- created;
- modified;
- superseded;
- intentionally left unchanged.

## Evidence inspected

Relevant:

- implementation;
- tests;
- runtime evidence;
- persisted state;
- experiments;
- specifications;
- historical documentation.

Do not list irrelevant files merely to make the investigation look larger.

## Scientific findings

Meaningful findings discovered during the work.

## Contradictions and uncertainty

Anything unresolved or supported by conflicting evidence.

## Validation

What was checked after the documentation changes.

## Remaining work

Only substantive remaining work.

Do not invent follow-up tasks merely to populate this section.

---

# Final quality criterion

The objective is not documentation coverage.

The objective is scientific legibility.

A future researcher should be able to encounter an unfamiliar behavior and navigate:

```text
what happened
↓
under what conditions
↓
which domains participated
↓
what information flowed
↓
what transformations occurred
↓
what state changed
↓
what causal history produced that state
↓
what became possible afterwards
↓
what evidence supports the interpretation
↓
what implementation produced it
```

The same chain should be navigable in reverse.

The documentation must make it possible to distinguish:

```text
what developers call something
```

from:

```text
what the implementation actually does
```

from:

```text
what has actually been observed
```

from:

```text
what the organism itself can know
```

Symbiont may evolve beyond anything anticipated by this document.

Therefore this skill must teach agents how to discover, verify, reconstruct and explain mechanisms — not merely enumerate the mechanisms that happen to exist today.

The documentation must evolve with the organism.

The methodology must survive the current implementation.
