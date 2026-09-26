---
title: Self-Model Workbench v1
status: implemented
language: en
canonical: true
---

# Self-Model Workbench v1

## Purpose

`Self-Model` is an observer-only research surface inside the Body workspace. It
answers a different question from the physical Body view:

- **Body** shows observer-visible physical embodiment truth.
- **Self-Model** shows bounded organism-owned knowledge about itself.
- **Mind** shows current cognitive activity.

The Self-Model view must never become another source of organism truth and must
never feed observer labels, anatomical semantics, goals, rewards, or selections
back into Symbiont.

## Canonical sources

The UI is a projection over existing organism-owned state:

- `SelfModel` per-sense cost/health/confidence estimates;
- `BodySchemaEngine` learned parts, regions and dependencies;
- body-boundary evidence from `BodySchemaEngine`;
- `AgencyModel`;
- `ControllabilityModel`;
- `ActionDimensionRegistry`;
- `CompetenceLibrary`;
- `EffectSpace`;
- `CompetenceExecutionBindingRegistry`;
- current `EmbodimentEpisode`;
- current `ActionCommitment` provenance.

No monolithic canonical `SelfModelState` is introduced by the Workbench.

## Views

### Overview

Composes real evidence from the remaining views. Presentation confidence is
derived from actual model confidence, controllability, reliability or boundary
confidence; presence of an item is never converted into fabricated confidence.

The existing perceptual self-model is also shown here as per-sense health,
confidence and maturity.

### Body Schema

Shows opaque learned BodySchema parts and learned dependencies as a graph.

It deliberately does **not** project those parts onto observer anatomy because
the canonical BodySchema contains no organism-owned mapping from an opaque part
to an observer joint or named anatomical region. Such an overlay would invent
knowledge.

Boundary evidence is shown separately as:

- self-caused channels;
- somatic-correlated channels;
- external/unowned channels;
- boundary confidence and revision count.

### Agency

Shows organism-owned competence/effect agency estimates and their supporting
causal specificity, temporal contingency, controllability and reliability.

Prediction match is presented as evidence, never as synonymous with agency.

### Capabilities

Shows learned:

- action dimensions;
- motor competences;
- effects;
- known competence -> effect relations.

The view does not infer a dimension -> competence edge unless such a relation is
present in canonical organism evidence.

### Affordances

Affordances are an observer-side **derived transient projection**, not a stored
organism fact.

A candidate requires:

1. an acquired competence with an effect;
2. a current embodiment execution binding;
3. when canonical Sensorimotor v2 executability is available, `executable=true`.

Confidence is composed for presentation from existing effect, controllability
and reliability evidence. The projection never authorizes movement.

### Embodiment

Shows current embodiment identity, epoch, state, historical-prior authority,
adaptation context and current execution bindings.

Durable organism knowledge and current-body executability remain separate.

### History

Keeps a bounded browser-session history of changes in the passive Self-Model
projection. It is observer memory only and is not checkpointed into the
organism.

## Executive boundary

Until `ActionIntent` exists canonically, the view may show only factual current
action provenance such as:

- action source;
- active commitment;
- active competence.

It must not infer or display a fabricated intention from motor activation,
prospective selection, or an active commitment.

Once an executive-intention domain is implemented, its canonical passive
projection may be added here.

## Data flow

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
mind_snapshot SSE event
        |
        v
BodyViewer
        |
        v
SelfModelWorkspace
```

There is no reverse path.

## Required provenance

The following projected fields are organism facts when present:

- `self_model`
- `body_schema`
- `body_schema_boundary`
- `agency_estimates`
- `controllability_estimates`
- `motor_competences`
- `effects`
- `action_dimensions`
- `embodiment`
- `executive_state`

The Self-Model UI itself may derive layout, summaries, affordances and bounded
browser history; those derivations remain observer-side.

## Non-goals

This work does not:

- alter motor learning;
- alter BodySchema learning;
- create ActionIntent;
- introduce anatomical cognitive labels;
- teach the organism which body part is which;
- add a global reward or goal;
- claim consciousness or human self-awareness;
- make historical competences executable after re-embodiment;
- infer physical truth from display geometry.

## Acceptance criteria

1. Body includes a first-class `Self-Model` workspace.
2. Overview, Body Schema, Agency, Capabilities, Affordances, Embodiment and
   History are available without changing organism state.
3. The view consumes the existing passive `mind_snapshot` stream.
4. BodySchema visualization uses only opaque organism-owned IDs and evidence.
5. Agency and controllability are exposed through passive rich telemetry.
6. Current affordances respect canonical executability when it is available.
7. Historical and current embodiment knowledge remain visibly distinct.
8. The existing per-sense self-model is not hidden or redefined.
9. No observer UI action writes back to Symbiont.
10. Tests protect the passive boundary and reject invented anatomical/executive
    semantics.

## Deferred work

The following require source-side knowledge that does not yet exist and are
therefore deliberately not fabricated in this version:

- anatomical heatmap of BodySchema over the physical mesh;
- physical-truth versus learned-schema diff by body region;
- canonical ActionIntent lifecycle and intent history;
- organism-owned affordance objects.

Those can be added only after their respective canonical mappings or domains
exist.
