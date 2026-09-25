---
id: design.general.autonomous-cultural-agency-v1
title: "Autonomous Cultural Agency V1"
document_type: design
domain: communication
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Autonomous Cultural Agency v1

## Scope

This phase removes evaluator selection of cultural content while retaining a
laboratory-controlled, in-memory transport. The apparatus supplies only local
topology, ticks, bounded budgets and resource conditions. It does not pass
claim IDs or composite IDs to the treatment, choose a receiver, or invoke
composition on behalf of an organism.

The organism-side `CulturalPolicy` lives in `symbiont.modeling`. It is a
deterministic bounded baseline, not reinforcement learning and not a claim of
cooperation. It scores only local ledger state: held claims, local composites,
roots, freshness-derived state, costs, memory capacity and seeded tie-breaking.
Evaluator truth, population-wide utility, labels and future outcomes are not
inputs.

## Actions and accounting

The policy can emit `SILENCE`, `RETAIN`, `DROP`, `TRANSMIT`, `VALIDATE` and
`COMPOSE`. `ModeledOrganismRuntime.autonomous_cultural_step()` accepts only a
bounded neighbor set. It asks the policy for a candidate and then executes the
selected bounded operation through the existing `SocialChannel`; explicit
claim/composite identifiers are not accepted by this treatment API.

Each decision stores a canonical `CulturalDecisionRecord` with a decision ID,
tick, digest of available options, selected action/items/recipient, local-state
digest and cost. The record is organism state and is checkpointed with the
policy. Observatory exposes a passive projection only.

Composition candidates are generated locally from pairs of held claims or one
held claim plus one current composite. Existing component signatures and shared
roots are excluded. The policy does not see task success or evaluator metrics.

## Boundaries

- No cultural ledger, decisions or acquired composites are copied by clonal
  birth. Any future heritable cultural parameters would be a separate study;
  v1 introduces none.
- No weights, adapters, corpus records or model outputs are transferred.
- Social claims remain distinct from observations and remain inadmissible as
  private-model training targets.
- No sockets, peer discovery, host action, command execution or external
  persistence are introduced.
- The treatment does not prove autonomous cooperation; it tests local action
  selection and its population-level consequence.

## Preregistered study

`experiments/learning/autonomous-cultural-agency/experiment.toml` defines
`learning.autonomous-cultural-agency`, seeds `101, 127, 149`, 24 ticks and 8
contact rounds. Conditions are no culture, the historical harness-directed
benchmark, and autonomous local policy. The historical directed condition is
not rewritten and is reported as an upper-bound control.

The minimum closure evidence is structural no-planner compliance, non-trivial
bounded decisions, autonomous multi-contributor composition, positive utility
relative to no culture, deterministic replay, and costs within the declared
ceilings. A positive result remains scoped to this policy and local topology;
it does not open language, symbols, cultural selection, reputation or SLM
co-evolution.
