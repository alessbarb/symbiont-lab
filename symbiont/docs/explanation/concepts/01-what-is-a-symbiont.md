---
id: explanation.web.01-que-es-un-symbiont
title: "01 What Is A Symbiont"
document_type: explanation
domain: concepts
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# What is a Symbiont

<a id="que-es"></a>

## What it is

A Symbiont is a digital organism: a software process that develops, maintains its own computational continuity under finite resources, and whose internal structure changes with experience without anyone rewriting its code. It is not a chatbot, it is not an agent that executes a user's instructions, and it is not a decorative simulation with biological names pasted over conventional functions.

The project explicitly distinguishes two roles that are never mixed:

- **`symbiont`** — the organism, the subject of study: cognition, host perception, environment and life cycle.
- **`symbiont_lab`** — the scientific apparatus: experiments, studies, results archive, evaluation and laboratory CLI.

<a id="no-metafora"></a>

## Why it is not a decorative metaphor

The project's biological vocabulary (metabolism, homeostasis, reproduction, death, ecology) is used under a strict criterion: a biological term is only valid if it points to a computational role with measurable consequences, not if it simply decorates a conventional function.

For example, "metabolism" does not mean "the program uses CPU" — it means that there is an explicit accounting of acquisition, transformation, maintenance cost and resource pressure. "Death" does not mean that the process ends — it means the irreversible closure of an organism identity's continuity, distinct from simply stopping or restarting a process.

<a id="mecanismo"></a>

## Mechanism

The separation between organism and scientific apparatus is an architectural boundary, not a style convention. `symbiont` never imports `symbiont_lab`: the experimental truth (what is really a threat, what synthetic regime is active) belongs exclusively to the simulator and the evaluator. The organism's cognitive layers (agent, collective memory, reasoning engine) only receive local or collective observations and beliefs — never the truth label that the evaluator uses to measure them.

Inside the organism, development occurs as **data plasticity under an immutable kernel**: a closed core defines the legal node/edge types and the hard resource limits; a declarative genome configures the development of an individual within those limits; a plastic phenotype learns weights and bounded structure during the life of that individual. The organism changes its phenotype, never its implementation — it does not generate code, it does not edit its executable, it does not invent permissions nor learn to bypass kernel limits.

<a id="implementado"></a>

## What is implemented

- The two-package boundary (`symbiont` / `symbiont_lab`) — **[implemented]**.
- Experimental truth isolation (`Observation` separated from `EvaluationEvent`) — **[implemented]**.
- The immutable cognitive graph hard limits kernel — **[implemented]**.
- The full list of functional analogies (metabolism, homeostasis, reproduction, ecology, etc.) against their biological counterparts, and their implementation status chapter by chapter — is developed in chapters 3 to 8 of this same series, not here.

<a id="evidencia"></a>

## Evidence

The `symbiont` / `symbiont_lab` boundary and the experimental truth isolation are not just a statement of intent: they are protected by a structural test that parses the Abstract Syntax Tree (AST) of the entire `symbiont` package and fails if any import of `symbiont_lab` appears. The same test verifies that the signatures of `Agent.observe`, `ReasoningEngine.analyze` and `MetacognitionEngine.assess` do not accept evaluator truth parameters (`is_threat`, `truth_label`, `ground_truth`, `evaluator`).

The immutable cognitive graph limits kernel is a frozen `dataclass` (`frozen=True`): any attempt to modify it after construction fails at runtime, not just by code convention.

<a id="abierto"></a>

## What remains open (of this mechanism)

- The package separation and the truth isolation are permanent project invariants, not development phases — there is no "more complete" state to evolve to here.
- How far the biological analogy goes in practice (which functions remain `[partial]` or `[deferred]`, and with what limits) is covered chapter by chapter in the rest of this series, not in this introduction.

<a id="respaldo-formal"></a>

## Formal backing

This chapter is definitional and architectural; it has no associated formal mathematical development. Chapters 2, 3, 4 and 8 of this series link to the mathematical compendium (`docs/math/`) where it corresponds to perception, cognition, attention and self-model.
