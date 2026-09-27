---
name: scientific-documentation
description: Maintain a scientifically useful, self-contained and human-readable body of documentation for Symbiont.
---

# Symbiont Scientific Documentation Skill

## Purpose

Maintain a scientifically useful, self-contained and human-readable body of documentation for Symbiont.

The goal is not to document a codebase as a collection of files and classes.

The goal is to reconstruct, explain and preserve how Symbiont actually works so that a future scientist can study it without needing its original authors to explain the system.

The documentation must remain useful as Symbiont evolves and gains mechanisms, processes, chains and phenomena that do not exist today.

---

# Use when

Use this skill when the task involves one or more of the following:

- documenting how Symbiont works;
- reconstructing behavior from code, tests, runtime evidence or experiments;
- explaining an existing process from macro to micro;
- discovering undocumented processes or causal chains;
- updating scientific documentation after implementation changes;
- documenting new cognitive, physical, sensorimotor or architectural mechanisms;
- tracing how an observed phenomenon is produced;
- tracing how state is created, transformed, consumed, persisted or lost;
- documenting causal provenance;
- documenting system boundaries and domain ownership;
- creating or updating anatomy documents;
- creating or updating scientific journeys or runtime narratives;
- maintaining the scientific atlas or conceptual graph;
- reconciling discrepancies between implementation, tests, runtime evidence and existing documentation;
- reorganizing scientific documentation according to Diátaxis where appropriate;
- translating or restructuring existing documentation without changing its meaning;
- preparing the repository so future researchers can understand the system independently.

---

# Do not use when

Do not use this skill when the primary task is:

- implementing application logic;
- fixing runtime bugs;
- changing algorithms;
- modifying system behavior;
- refactoring production code;
- running ordinary test suites solely to validate code changes;
- creating product requirements or implementation specifications;
- writing release notes;
- changing CI/CD;
- modifying infrastructure;
- performing unrelated repository maintenance;
- correcting a trivial typo in code that does not affect documentation;
- generating documentation from assumptions without examining evidence.

If documentation work reveals a code defect, architectural inconsistency or missing behavior, document the finding.

Do not silently repair the implementation unless explicitly instructed to do so.

---

# Core Principle

Treat Symbiont as a system that can be scientifically studied.

The fundamental unit of documentation is not the file.

It is the phenomenon.

A phenomenon may be:

- a perception;
- an action;
- a prediction;
- a learning event;
- a memory change;
- a structural modification;
- an interaction;
- a decision;
- a state transition;
- an embodiment event;
- an information transformation;
- a causal dependency;
- or any new type of behavior discovered in future versions.

Do not assume that the currently known set of phenomena is complete.

Discover first.

Classify afterwards.

---

# Primary reader

Write for a future scientist who:

- has never spoken with the original authors;
- does not know the historical decisions of the project;
- does not know the internal terminology;
- does not know where the relevant code lives;
- cannot ask anyone what an ambiguous sentence means;
- needs to determine what the organism does, how it does it and what evidence supports that interpretation.

The documentation must stand on its own.

---

# Fundamental documentation path

Every important phenomenon should support navigation in both directions.

From phenomenon to implementation:

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

And from implementation back to meaning:

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

The reader should never encounter important code without being able to determine why it matters.

The reader should never encounter an important conceptual claim without being able to find the evidence that supports it.

---

# Human-first writing

Always explain the phenomenon before the implementation.

Do not begin with:

> `XManager.execute()` invokes `YResolver`.

Begin with what happens:

> The organism may have several possible actions available, but only some of them become actual commitments. Before physical execution begins, those possibilities must be resolved into something the action system can maintain and control.

Then explain:

1. what happens;
2. why it matters;
3. which system boundaries are crossed;
4. which information participates;
5. what state changes;
6. how causality flows;
7. which mechanisms implement it;
8. where the implementation lives;
9. what evidence proves the explanation.

The code demonstrates the explanation.

The code must not replace the explanation.

---

# Humanization rule

Documentation must read like a scientific explanation written for another human.

Avoid output dominated by repetitive schemas such as:

```text
Input:
Output:
State:
Method:
```

unless the reader is explicitly in a reference document.

Prefer sentences such as:

> This is the point where the organism stops merely retaining a previous outcome and allows that outcome to alter what it will admit as a future action.

or:

> The body knows nothing about the meaning assigned to this value by the UI. At this boundary, Symbiont receives only the opaque signal produced by the apparatus.

Use technical detail where it improves precision.

Do not use technical detail merely because it exists.

---

# Progressive depth

Important subjects should be understandable at several levels.

## Human level

What happens, described without requiring knowledge of the code.

## System level

Which domains and subsystems participate.

## Causal level

What produces what.

## Runtime level

What executes, and in what order.

## State level

What information is created, read, modified, preserved or destroyed.

## Algorithmic level

Which rules or computations produce the behavior.

## Implementation level

Which concrete symbols implement it.

Each level should deepen the same explanation.

Do not replace one explanation with another unrelated explanation at a lower level.

---

# Architectural boundaries

Respect the actual boundaries discovered in the implementation.

For current Symbiont architecture, investigate carefully whether the following distinction is preserved:

```text
World != Body != Embodiment != Symbiont
```

Do not assume this list will remain complete forever.

If new domains appear, discover and document them.

Also distinguish, where relevant:

```text
physical reality
!= sensed information
!= internal representation
!= learned interpretation
!= developer interpretation
!= UI representation
```

Never attribute external semantics to Symbiont unless the organism itself possesses evidence supporting that meaning.

---

# Scientific honesty

Never infer a behavior solely from a class, module or variable name.

A class called:

```text
Memory
```

does not prove the existence of memory.

A class called:

```text
Reasoning
```

does not prove reasoning.

A class called:

```text
Learning
```

does not prove learning.

Determine what actually happens.

Distinguish:

- observed behavior;
- implemented behavior;
- documented intention;
- inferred purpose;
- unverified assumption.

Do not silently collapse these categories.

---

# Evidence hierarchy

Use multiple sources of evidence.

Possible sources include:

- production code;
- unit tests;
- integration tests;
- boundary tests;
- experimental integrity tests;
- runtime traces;
- telemetry;
- persisted state;
- studies;
- experiment outputs;
- scientific specifications;
- historical documentation.

Understand what each source can prove.

A specification demonstrates intended design.

Code demonstrates implementation.

A test demonstrates behavior under specific conditions.

A runtime execution demonstrates what happened in one concrete execution.

An experiment may support broader conclusions only within its stated conditions.

Never present intention as observed behavior.

Never present a single observation as a universal law.

---

# Evidence status

Maintain evidence status internally.

Use categories such as:

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

Do not clutter normal prose with these labels unless they help the reader.

Prefer natural language such as:

> The implementation and boundary tests both support this interpretation.

or:

> The current documentation states X, but the runtime path presently performs Y.

---

# Contradictions

Never silently resolve discrepancies.

When code, tests, runtime, experiments or existing documentation disagree, preserve the disagreement explicitly.

Examples:

```text
DOC / CODE DISCREPANCY
CODE / TEST DISCREPANCY
SPEC / RUNTIME DISCREPANCY
STATE / PROVENANCE LOSS
```

Explain:

- what each source says;
- what can be demonstrated;
- what remains uncertain;
- what further evidence would resolve the discrepancy.

Scientific documentation must preserve uncertainty when uncertainty exists.

---

# Causal reconstruction

Whenever possible, reconstruct actual causal chains.

Do not merely document dependencies.

Try to explain:

```text
what happened
    ↓
what made it possible
    ↓
what information was used
    ↓
what transformation occurred
    ↓
what state changed
    ↓
what became possible afterwards
```

A generic chain might look like:

```text
world event
    ↓
physical consequence
    ↓
observation
    ↓
internal transformation
    ↓
evidence
    ↓
decision or learning
    ↓
new state
    ↓
future consequence
```

But never impose this shape if the implementation behaves differently.

Discover the real chain.

---

# Causal history

Do not confuse current state with the history that produced it.

Two equivalent current values may have different causal histories.

Where the system preserves sufficient information, document:

```text
current state
    ← derived from
previous state
    ← generated by
process
    ← using
evidence
    ← derived from
observation
```

If the system cannot preserve or reconstruct this history, say so.

If checkpoint or restore preserves state but loses causal provenance, document that explicitly.

---

# Time

Do not assume a single clock.

Discover every relevant temporal domain.

Examples may include:

- physics time;
- world time;
- organism lifetime;
- embodiment lifetime;
- experimental time;
- developmental time;
- cognitive cycles;
- generations;
- snapshot sequences;
- wall-clock time.

For every time domain determine:

- what advances it;
- what depends on it;
- whether it can pause;
- whether it resets;
- whether it survives body changes;
- whether it survives process restarts;
- how it relates to other clocks.

---

# State analysis

For every scientifically important state, determine:

- what it represents;
- which domain owns it;
- how it is created;
- what may change it;
- who may observe it;
- who consumes it;
- how long it lives;
- what depends on it;
- whether it is persisted;
- whether it is restored;
- whether it is embodiment-specific;
- whether it is body-specific;
- whether it survives context changes;
- what previous states contributed to it.

Do not assume current state categories are exhaustive.

If a new kind of continuity, persistence or state ownership appears, document it as such.

---

# Anatomies

Create an anatomy when an important phenomenon requires an end-to-end explanation.

Examples may include:

- Anatomy of a Perception
- Anatomy of an Action
- Anatomy of Learning
- Anatomy of a Tick
- Anatomy of Re-embodiment
- Anatomy of a Decision

These examples are not mandatory categories.

Future mechanisms may require completely different anatomies.

An anatomy should begin with:

> What happens?

and finish with:

> Exactly how does the implementation make it happen?

---

# Scientific journeys

Use narrative journeys when multiple mechanisms must be understood together.

Examples:

- the organism encounters something unfamiliar;
- an unexpected outcome changes future behavior;
- a newly embodied organism begins learning its body;
- a prediction fails and produces structural change.

These are not fictional stories.

They must be evidence-based reconstructions.

The purpose of a journey is to make several interacting mechanisms understandable as one continuous event.

---

# Real executions

Where runtime evidence exists, complement general explanations with concrete executions.

Always distinguish:

```text
general mechanism
```

from:

```text
one observed execution
```

A real execution can demonstrate how several mechanisms interacted in one case.

It must not be presented as proof that every execution follows the same path.

---

# Future-proof discovery

This skill must not be limited to mechanisms currently known.

Every run must be capable of discovering new:

- domains;
- processes;
- states;
- clocks;
- causal relations;
- lifecycle events;
- forms of memory;
- forms of learning;
- forms of perception;
- forms of action;
- forms of interaction;
- forms of cognition;
- forms of representation.

When something new appears:

1. identify the phenomenon;
2. determine its boundaries;
3. discover its state;
4. discover what feeds it;
5. discover what consumes it;
6. discover its causal role;
7. determine what evidence exists;
8. integrate it into existing explanations;
9. create new documentation structures only when needed.

Never force a new mechanism into an old category merely to preserve the documentation structure.

The documentation model must evolve when the system evolves.

---

# Diátaxis

Use Diátaxis as a separation-of-purpose framework, not as a mandatory folder template.

The four documentation types are:

```text
Tutorial
How-to
Reference
Explanation
```

Do not force every project or domain to contain all four.

Use only the categories supported by real content and real reader needs.

---

# Diátaxis type boundaries

Prevent type drift.

A document must have a clear primary purpose.

## Tutorials

Tutorials are learning experiences.

They should guide a learner through a complete path.

Do not turn tutorials into architecture essays.

Do not use tutorials as encyclopedic references.

Do not overload tutorials with implementation history.

---

## How-to guides

How-to guides solve a specific practical problem.

They should be action-oriented.

Under no circumstances add extended conceptual theory merely to make the document appear more complete.

Do not explain the entire architecture in a how-to.

Do not turn a how-to into reference documentation.

---

## Reference

Reference documents describe the system accurately and systematically.

They may contain:

- contracts;
- schemas;
- concepts;
- state;
- APIs;
- symbols;
- invariants;
- data structures.

Do not add procedural tutorials to reference material.

Do not turn reference material into narrative essays.

Reference should prioritize precision and lookup value.

---

## Explanation

Explanation documents build understanding.

They may discuss:

- why a mechanism exists;
- how several systems relate;
- conceptual models;
- implications;
- architectural reasoning;
- scientific interpretation.

Do not turn explanation into step-by-step operational instructions.

Do not overload explanation with exhaustive symbol listings better suited to reference.

---

# Empty quadrant rule

Never create empty documentation categories merely to satisfy Diátaxis.

If the existing corpus contains no tutorials, do not create a tutorial folder with placeholder content.

If a domain requires only explanation and reference, document only explanation and reference.

Never invent filler material.

Never generate fake reader needs merely to populate a framework.

Structure follows content.

Content does not exist to justify structure.

---

# No placeholder generation

Do not create:

- empty folders;
- empty Markdown files;
- "TODO documentation" pages with no substantive content;
- speculative tutorials;
- artificial examples;
- fake scenarios;
- placeholder sections whose only purpose is structural completeness.

A missing category is preferable to invented documentation.

---

# Translation rules

When translating documentation:

Preserve meaning before style.

Do not:

- add explanations that did not exist;
- remove uncertainty;
- strengthen claims;
- soften scientific caveats;
- alter causal meaning;
- rewrite technical terms inconsistently;
- change code;
- change equations;
- alter Mermaid semantics;
- change identifiers;
- change examples unless translation requires it.

A translation task is not permission to improve the scientific content.

If scientific correction is needed, handle it separately.

---

# Type drift during translation

Translation must preserve the document's original purpose.

A how-to remains a how-to.

Reference remains reference.

Explanation remains explanation.

Tutorial remains tutorial.

Do not enrich one type using content that belongs to another type simply because the result reads more smoothly.

---

# Glossary discipline

If the repository defines a glossary or canonical terminology:

1. load it before translating or rewriting;
2. use canonical terms consistently;
3. do not invent synonyms for stylistic variation;
4. preserve distinctions that matter scientifically;
5. report missing glossary concepts rather than improvising terminology.

Terminological consistency is more important than literary variety in technical vocabulary.

Humanization should occur in sentence structure and explanation, not by destabilizing scientific terms.

---

# Work in bounded batches

Do not perform uncontrolled bulk transformations across large documentation trees.

Large-context operations increase the probability of:

- terminology drift;
- broken code blocks;
- altered equations;
- lost frontmatter;
- ignored constraints;
- type drift;
- accidental omission.

Operate in bounded, coherent batches.

A batch should normally correspond to:

- one documentation type;
- one scientific domain;
- one causal chain;
- one anatomy;
- or another naturally bounded unit.

---

# Plan → Validate → Execute

For significant documentation operations, follow this cycle.

## 1. Plan

Before modifying content:

- inspect relevant existing documentation;
- inspect canonical terminology;
- identify document types;
- identify affected concepts;
- identify code and evidence needed;
- determine dependencies;
- identify what must not change.

Produce a concrete internal map of the work.

---

## 2. Validate

Before making broad changes:

- verify classification;
- verify terminology;
- verify architectural boundaries;
- verify evidence sources;
- confirm that the intended operation will not mix Diátaxis types;
- confirm that no empty categories are being created;
- check whether existing documents already cover the subject.

---

## 3. Execute

Apply the smallest coherent batch.

Preserve:

- frontmatter;
- code fences;
- code identifiers;
- diagrams;
- equations;
- links;
- anchors;
- semantic distinctions.

---

## 4. Verify

After each batch:

- inspect the diff;
- check Markdown integrity;
- validate internal links where tooling exists;
- check frontmatter;
- check code blocks;
- check Mermaid;
- check equations;
- verify terminology;
- verify Diátaxis type;
- verify scientific meaning.

Do not start another large batch until the current batch is coherent.

---

# Incremental documentation workflow

When updating documentation after code changes:

1. determine what changed;
2. identify which phenomena are affected;
3. trace changed execution paths;
4. identify changed state or causality;
5. inspect affected tests and runtime evidence;
6. determine which existing explanations are now stale;
7. update causal chains;
8. update relevant anatomies;
9. update reference material;
10. update scientific journeys if behavior changed;
11. record discrepancies or uncertainty;
12. avoid rewriting unaffected documents without reason.

Maintain a living scientific corpus.

Do not regenerate the entire documentation tree after every change.

---

# Repository exploration strategy

Do not read the repository linearly.

Begin by finding:

- entry points;
- runtime orchestrators;
- state owners;
- lifecycle boundaries;
- major domain interfaces;
- persistence paths;
- event flows;
- tests proving critical behavior.

Then follow causal paths.

Prefer:

```text
phenomenon
→ runtime path
→ state
→ transformations
→ downstream consequences
```

over:

```text
folder
→ file
→ class
→ next file
```

---

# Code references

Use stable references where possible.

Prefer:

```text
path/to/module.py::Class.method
```

over line numbers.

Line numbers may be included temporarily during investigation but should not be the primary durable reference.

---

# Scientific Atlas

Maintain or update a structured conceptual model when the repository supports it.

The atlas should represent:

- phenomena;
- processes;
- mechanisms;
- states;
- evidence;
- domain boundaries;
- causal relationships;
- temporal relationships;
- persistence relationships.

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

This list is extensible.

Do not constrain future science to current relationship types.

---

# Scientific traceability

Whenever practical, allow navigation between:

```text
concept ↔ implementation
state ↔ producers
state ↔ consumers
phenomenon ↔ causal chain
experiment ↔ mechanisms
mechanism ↔ tests
documentation ↔ evidence
```

Documentation should behave as a connected body of knowledge, not as isolated Markdown pages.

---

# Reproducibility

When documenting conclusions derived from experiments, record enough information for another researcher to evaluate or reproduce them.

Include where relevant:

- repository revision;
- runtime version;
- world;
- body;
- embodiment;
- configuration;
- initial conditions;
- seed;
- duration;
- metrics;
- intervention;
- comparison baseline;
- acceptance criteria;
- observed result;
- uncertainty;
- limitations.

Never generalize beyond the conditions supported by evidence.

---

# Historical evolution

Preserve history only when it affects scientific interpretation.

Record changes such as:

- a causal mechanism changed;
- state persistence changed;
- a learning rule changed;
- an organism boundary changed;
- a previously valid experimental result is no longer directly comparable.

Do not turn scientific documentation into a changelog.

---

# Findings

During investigation, record meaningful findings.

Examples include:

- ambiguous ownership;
- semantic leakage;
- provenance loss;
- undocumented state persistence;
- dead execution paths;
- contradictory tests;
- specification drift;
- duplicated causal authority.

Do not present every minor observation as a defect.

Separate:

```text
scientifically relevant finding
```

from:

```text
ordinary implementation detail
```

---

# Output quality

Avoid documentation that sounds mechanically generated.

Do not produce long sequences such as:

> Component X receives Y.  
> Component X outputs Z.  
> Component Y receives Z.

Instead explain the relationship:

> Once the observation has been converted into internal evidence, it no longer describes the physical event directly. From this point onward, downstream cognition consumes the organism's internal estimate rather than the world state that originally produced it.

Then provide the technical mapping separately.

---

# Self-contained terminology

Never assume the reader already knows an internal term.

The first meaningful use of a concept should allow the reader to understand:

- what it denotes;
- why it exists;
- what distinguishes it from similar concepts.

Do not repeatedly redefine it afterwards.

---

# Scientific questions test

Before considering a subject sufficiently documented, ask whether a future researcher can answer:

- What am I observing?
- Why can this happen?
- What conditions are required?
- Which mechanisms participate?
- What information crosses each boundary?
- What state changes?
- What persists afterwards?
- What is lost?
- What caused this state?
- What can this state cause next?
- Which implementation performs the behavior?
- Which tests support it?
- Which runtime evidence supports it?
- What remains uncertain?
- Can the observation be reproduced?

If important answers are missing, the subject is not yet sufficiently documented.

---

# Final quality criterion

The goal is not documentation coverage.

The goal is scientific legibility.

A future researcher should be able to encounter an unfamiliar behavior and navigate:

```text
what happened
    ↓
under what conditions
    ↓
which processes participated
    ↓
what information flowed
    ↓
what transformations occurred
    ↓
what state changed
    ↓
what causal history led there
    ↓
what evidence supports the interpretation
    ↓
what implementation produced it
```

The same chain should be navigable in reverse.

Symbiont may change beyond what this skill can currently anticipate.

The skill must therefore describe how to discover, verify and explain mechanisms rather than enumerating the mechanisms that happen to exist today.

The documentation must evolve with the organism.

The methodology must survive the current implementation.
