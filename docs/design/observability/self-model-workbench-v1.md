---
title: Self-Model Workbench v1
status: implemented
language: en
canonical: true
---

# Self-Model Workbench v1

## Purpose

`Self-Model` is an observer-only research surface inside the Body workspace.
It separates three different questions:

- **Body**: what the current physical embodiment is doing;
- **Self-Model**: what the organism has learned about itself;
- **Mind**: what cognitive activity is currently occurring.

The Workbench is a passive projection. It never becomes a second source of
organism truth and never feeds observer labels, anatomy, goals or selections
back into Symbiont.

## Agency Acquisition & Executive Action v1 integration

The Workbench consumes the canonical Agency v1 domains directly:

- learned `ActionDimension` state and agentic classification;
- `agency_acquisition` evidence and intervention statistics;
- canonical ephemeral `ActionAffordance` projections;
- canonical persistent `ActionIntent` executive state;
- intent outcome counts and the latest causal action trace;
- `MotorCompetence`, `Effect`, embodiment bindings and BodySchema evidence.

The Workbench does **not** reconstruct affordances from bindings and effects.
`AffordanceResolver` is the canonical source. It also does not infer an
intention from motor activity: `ActionIntent` is now the canonical source.

## Views

### Overview

Shows the path from learned self-knowledge to executive action:

```text
BodySchema -> Agency -> Capability -> Affordance -> ActionIntent -> Embodiment
```

All displayed confidence is derived from real model evidence.

### Body Schema

Shows opaque organism-owned learned parts, cognitive regions, dependencies and
body-boundary evidence. It deliberately does not paint those IDs onto observer
anatomy because no canonical organism-owned anatomical mapping exists.

### Agency

Shows acquisition rather than a post-hoc skill-only view:

- physical motor opportunities;
- action attempts;
- intervention signatures and recurrence;
- causal relations/evidence;
- action dimensions;
- whether each dimension has become agentic;
- controllability and confidence.

This preserves the Agency v1 result that agency can be acquired before a
`MotorCompetence` exists.

### Capabilities

Shows learned action dimensions, motor competences, effects and known
`MotorCompetence -> Effect` relations.

### Affordances

Shows the canonical current `ActionAffordance` set. Affordances remain derived,
ephemeral and non-authoritative: they state what the organism can probably do
now, but never grant motor authority.

### Executive

Shows the canonical `ActionIntent` bridge:

```text
ActionAffordance
    -> ActionIntent
    -> ActionCommitment
    -> MotorCommand
    -> observed effect
    -> intent reconciliation
```

The view exposes the active intent, admission route, anticipated effect,
supporting affordance, current commitment, terminal outcome counts and the
latest causal action trace.

`ActionIntent` specifies **what consequence is being attempted**, never how the
body must produce it. Motor authority remains with `ActionCommitment` and
`ActionDomain`.

### Embodiment

Shows current embodiment identity, epoch, lifecycle/adaptation context and
execution bindings. Durable competence knowledge remains distinct from
current-body executability.

### History

Keeps a bounded browser-session history of changes in self-knowledge and
executive state. It is observer memory only and is never checkpointed into the
organism.

## Existing perceptual self-model

The original per-sense `SelfModel` is preserved and surfaced in Overview:

- cost class;
- health class;
- confidence class;
- maturity class;
- recency.

It is not replaced by the larger Workbench composition.

## Passive data flow

```text
organism-owned models
        |
        v
Physics3D rich telemetry
        |
        v
mind_snapshot_from_rich_state()
        |
        v
mind_snapshot SSE
        |
        v
BodyViewer
        |
        v
SelfModelWorkspace
```

There is no reverse path.

## Additional passive projection

`BodySchemaEngine.export_representation()` intentionally omits internal
boundary evidence. Physics3D therefore exposes a bounded
`body_schema_boundary` block containing only:

- self-caused channels;
- somatic-correlated channels;
- external channels;
- boundary confidence;
- revision count;
- disruption score.

This is organism-owned evidence and remains passive.

## Non-goals

The Workbench does not:

- alter agency acquisition;
- alter affordance resolution;
- form or terminate intents;
- arbitrate motor authority;
- issue commands;
- infer anatomy from simulator geometry;
- add semantic goals or reward;
- claim consciousness;
- make historical competences executable after re-embodiment.

## Acceptance criteria

1. Body contains a first-class `Self-Model` workspace.
2. Overview, Body Schema, Agency, Capabilities, Affordances, Executive,
   Embodiment and History are available.
3. Affordances come directly from the canonical `affordances` snapshot block.
4. Executive state comes directly from canonical `executive_intention`.
5. Agency acquisition uses `agency_acquisition` plus action-dimension evidence.
6. Per-sense SelfModel remains visible.
7. Body-boundary evidence is exposed without leaking anatomy.
8. Embodiment continuity remains visible without conflating durable knowledge
   with current executability.
9. UI interaction cannot mutate Symbiont.
10. Tests protect the passive and semantic boundaries.
