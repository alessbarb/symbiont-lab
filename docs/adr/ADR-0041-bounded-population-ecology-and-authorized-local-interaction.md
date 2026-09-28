# ADR-0041: Bounded Population Ecology and Authorized Local Peer Interaction

## Status

Accepted

## Context

Simulations of cultural evolution, structured communication, and multi-organism ecologies require orchestrating dozens of concurrent organisms. Without strict population caps, communication transport budgets, and local contact boundaries, simulations suffer from memory exhaustion, message storms, or artificial global broadcast shortcuts that undermine local social emergence.

## Decision

1. **Strictly bounded population capacity.** `IntegratedHabitatRuntime` enforces a constitutional population ceiling (default $\le 32$ organisms) and a maximum simulation tick limit (e.g. 10,000 ticks). Reproduction attempts exceeding the habitat carrying capacity fail closed or cause competitive displacement.
2. **Authorized local contact.** Organisms may interact and exchange signals only when physically co-located or within bounded neighborhood sensory radii. Global broadcast buses are strictly prohibited.
3. **No downward message mediation.** The habitat orchestrator facilitates contact opportunities, but never:
   - Selects a message recipient on behalf of an agent;
   - Parses, inspects, or alters transmitted tokens or symbols;
   - Dictates communicative meaning or enforces cooperative conventions.
4. **Atomic dead-member pruning.** Organisms reaching terminal physiological states (`VitalState.DEAD`) are pruned atomically at the tick boundary. Any pending inbound message delivery to a deceased organism is rejected and logged as dropped.

## Consequences

- Social and cultural transmission dynamics emerge strictly from localized physical co-presence.
- Computational resources scale linearly with population size rather than quadratically.
- Eliminates artificial telepathic coordination across habitat territories.

## Introduced in

Milestone IHR (Integrated Habitat Runtime v1).

## Evidence

`docs/design/runtime/integrated-habitat-runtime-v1.md`, `tests/unit/test_autonomous_cultural_agency.py`, `tests/unit/lab/world/test_population.py`.
