---
id: explanation.web.07-ecologia-y-sociabilidad
title: "07 Ecology And Sociability"
document_type: explanation
domain: concepts
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Ecology and sociability

<a id="que-es"></a>

## What it is

When several Symbionts share a habitat with finite resources, they can compete, coexist, specialize or exchange evidence among themselves — but none of those relationships is imposed in advance. The project does not code cooperation as a goal; cooperation, if it appears, is an observed result, not a programmed goal.

<a id="mecanismo"></a>

## Mechanism

Each organism maintains its own directional relational memory: one record for each pair and for each opaque interaction channel. The valence of a relationship (positive, negative or unknown) is derived from the difference between observed support and harm — not from an external social label. The freshness of that evidence decays exponentially with time since the last observation, and the reliability combines the proportion of observations without conflict with that freshness. None of this is global reputation: it is local evidence, unique to each organism, about each specific relationship.

Faced with finite resources, `ResourceEvidenceLedger` computes a local utility score combining observed availability, freshness and a penalty for consecutive denials — with an explicit limit so that no amount of denials blocks a resource permanently. If a token has been repeatedly denied but remains inactive for several ticks, it is granted a re-exploration opportunity: temporary scarcity does not become a permanent blacklist, and the organism remains adaptable if the ecological regime changes.

An authorized habitat (`SocialHabitat`) imposes hard carrying capacity, explicit admission and transactional release when a member dies — the ecology inherits the same transactional guarantees already described for birth in chapter 6.

<a id="implementado"></a>

## What is implemented

- Directional relational memory per pair and per channel, with valence based on evidence — **[implemented]**.
- Exponential freshness and local reliability weighted by conflict — **[implemented]**.
- Evidence of resource availability with bounded penalty for consecutive denials — **[implemented]**.
- Bounded re-exploration after cooldown, avoiding permanent block — **[implemented]**.
- Autonomous multi-peer emergence (social interaction without a central planner, without isolated members) — **[implemented] [evaluator-only]**: demonstrated in a deterministic laboratory harness, not as a self-observed property by the organism in production.

<a id="evidencia"></a>

## Evidence

It is directly proven that the valence of a relationship is derived from accumulated evidence, not from an imposed label. It is proven that the relational record preserves reciprocity, conflict and freshness as separate dimensions, not merged into a single reputation number. And it is proven that the evidence of a historically useful but repeatedly denied resource is revised after the cooldown period — the organism can change its mind about a resource without needing an external signal to tell it so.

<a id="abierto"></a>

## What remains open (from this mechanism)

- Autonomous multi-peer emergence and its generalization to populations of different sizes are measured only in evaluator-only laboratory studies; there is no evidence yet of emergent social behavior outside those controlled synthetic regimes — the roadmap itself explicitly states so.
- Niche differentiation between organisms under prolonged containment has been observed in specific synthetic trajectories, but it is not claimed as a demonstrated general property of the system.

<a id="respaldo-formal"></a>

## Formal backing

The complete normative design of social perception, local decision, competition for finite resources and adversarial limits is in
[`docs/design/sociabilidad-y-desarrollo-predictivo.md`](../design/sociabilidad-y-desarrollo-predictivo.md).
The collective consensus without external oracle, relevant for how multiple organisms revise shared evidence without treating the majority as truth, is in
[`docs/math/06-consenso-colectivo-y-confianza.md`](../math/06-consenso-colectivo-y-confianza.md).
