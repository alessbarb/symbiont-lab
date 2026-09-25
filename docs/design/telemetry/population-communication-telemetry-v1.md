---
id: design.telemetry.population-communication-telemetry-v1
title: "Population Communication Telemetry V1"
document_type: design
domain: telemetry
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Population Communication Telemetry v1

> Give Symbionts capabilities and constraints, not linguistic answers.

This is an observability-only layer. It does not change symbol selection,
message selection, receiver selection, grounding, cultural policy, learning,
or metabolism. The runtime emits bounded factual records outward; Observatory
projects and aggregates them read-only.

## Boundaries

Three layers remain distinct:

1. **Organism state**: local knowledge and grounding actually held by an
   organism.
2. **Population telemetry**: exported facts such as a delivered message or a
   local grounding update.
3. **Evaluator analytics**: externally computed counts, information measures,
   clusters, and persistence analyses.

Events contain no meaning, latent state, labels, ground truth, weights, or
corpus. A graph edge is created only by an exported `DELIVER`, `RECEIVE`, or
`RETRANSMIT` event. Missing or pruned history is never reconstructed as fact.

## Contract and bounds

`CommunicationEvent` and `GroundingEvent` are canonical, versioned,
serializable records. `CommunicationTelemetry` is a bounded append-only buffer
with deterministic IDs, duplicate rejection, per-tick and total ceilings,
optional age pruning, checkpoint/restore, and truncation metadata. The current
wire ceiling is 2,048 records per category and 4 symbols per event; the study
uses smaller capacities for explicit pruning tests.

Telemetry is a best-effort outbound sink: a full or invalid sink cannot change
whether local delivery or grounding succeeds. Telemetry is not copied into
clonal epistemic state.

## Observatory

The passive view provides Communication Live, a directed population graph,
Convention Explorer, grounding rows, and a derived emergence timeline. Filters
operate only on the rendered bounded snapshot. Neutral aliases are reversible
and no message is translated. The fleet aggregator namespaces event IDs by
instance, honors source truncation boundaries, and creates no inferred edges.

A warning exposes `earliest_available_tick` when history was pruned. All
scientific interpretation belongs in an explicitly evaluator-side report, not
in organism cognition or the UI's factual layer.
