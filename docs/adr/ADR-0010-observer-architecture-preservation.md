# ADR-0010: Observer Architecture Preservation (ADR-EW-003)

## Status

Accepted

## Context

Performance program P0–P7 separated the causal organism path from observation. The pieces are: `OrganismRuntime.tick(include_observability=False)`, independent physics/cognition/observation/render clocks (`ExecutionRates`), `observer-live-delta-v1` anchor/delta transport, serialized-once SSE in `ObservationBus`, and bounded browser rendering. Experience & World work could easily regress these by adding per-tick Experience snapshots or parallel transports.

## Decision

The following are normative for all Experience/World work:

1. No rich Experience, Vision or World projection is built on every causal tick. Projections are built only when the observation cadence requires them.
2. No second observer bus, SSE transport or live-state protocol exists. New live channels enter `ObservationBus`. `world_scene` keeps its revisioned contract.
3. No universal `ExperienceSnapshot` exists. Truth, apparatus, organism evidence, acquired structure and observer correspondence are separate passive projections with their own provenance.
4. **Observability independence (Gate I).** For the same starting checkpoint, seed, physics configuration, rate plan and definition, runs with observation on and off must produce identical causal outcomes within declared determinism guarantees.
5. **Age-independent observation (Gate J).** No live projection may do work proportional to the complete organism or world history.
6. Browser work keeps RAF animation, data-model recomputation and DOM summary refresh decoupled.
7. Lab run guards, such as acquisition protection, read only state computed on the causal path, whether or not observation is enabled, and never mutate organism state.

## Consequences

The Experience/World refactor is an ownership and ontology change on top of existing mechanisms, not a new runtime.

## Introduced in

Milestone EW-A.
