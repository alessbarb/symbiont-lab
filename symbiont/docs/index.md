# Symbiont — scientific description of the organism

This corpus is the canonical entry point for studying Symbiont as a computational organism. It is deliberately different from the design specifications, implementation notes and historical documents that coexist in the repository. Those sources remain valuable because they preserve intent, experiments and design evolution; this corpus synthesizes them with the current implementation and separates what exists from what was proposed.

Symbiont should be read at three depths. A first reading explains the organism in ordinary scientific language. The anatomy documents then follow concrete processes end to end. The reference and atlas layers provide the exact ownership, implementation and causal relationships needed for verification.

The central architectural distinction is simple but decisive:

```text
World != Body != Embodiment != Symbiont
```

A world contains external state and dynamics. A body is a physical substrate in that world. An embodiment is the historically bounded relationship between one Symbiont and one body contract. Symbiont is the persistent organism whose internal organization may survive the end of a particular body.

This distinction does not imply that every boundary is perfectly implemented or immutable. Where implementation and specification differ, the documentation says so.

## Reading path

Start with [Foundations and epistemology](00-foundations-and-epistemology.md), then read [System and boundaries](01-system-and-boundaries.md). From there the natural path is lifecycle, embodiment, perception, physiology, cognition, agency, learning, generative cognition and social/lineage processes. The last chapters explain persistence, the laboratory and the experimental method.

For process-level study, use the anatomy documents:

- [Anatomy of a tick](anatomy/tick.md)
- [Anatomy of a perception](anatomy/perception.md)
- [Anatomy of an action](anatomy/action.md)
- [Anatomy of learning](anatomy/learning.md)

For exact lookup, use the [domain map](reference/domain-map.md), [state ownership](reference/state-ownership.md), [evidence status](reference/evidence-status.md) and the [causal atlas](atlas/relations.md).

## What is canonical here

This corpus is canonical for explanation of the current system. It does not make old specifications disappear. A specification answers “what was intended”; this corpus answers “how the present system is organised and what evidence supports that description”. Historical design documents are cited as sources where they remain useful.

The corpus is intended to be maintained with the code. When a mechanism changes, the affected scientific explanation, anatomy and reference entries should change together.
