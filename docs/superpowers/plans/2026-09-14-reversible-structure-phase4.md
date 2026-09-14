# Reversible Structural Plasticity — Phase 4

## Goal

Make developmental viability an explicit runtime concern and guarantee a recovery path for germinal graphs that are structurally valid but trapped by exhausted budgets or disconnected latent nodes.

## Consolidation transaction

Every germinal consolidation is planned in this order:

1. **Maintenance**
   - prune edges whose lifecycle has expired;
   - evaluate CONCEPT/READOUT orphanhood against the post-prune projected graph;
   - evict disconnected stale or over-budget SENSE nodes against the post-GC projected graph.
2. **Budget recovery**
   - compute free node/edge capacity from that projected maintenance state.
3. **Growth**
   - form concept/readout bundles first;
   - then propose generic structurally legal edges.
4. **Atomic commit**
   - replay the complete maintenance+growth batch from the original graph;
   - any invalid step rolls the whole structural transaction back.

No partial projected topology is exposed to the organism or Observatory.

## Topology health

`TopologyHealth` is derived from real topology and durable support:

- `GERMINAL`: empty graph or germinal sensory interface with no latent cognition yet;
- `DEVELOPING`: latent structure exists but no complete SENSE→READOUT path yet;
- `CONNECTED`: at least one structural SENSE→READOUT path exists;
- `ADAPTIVE`: at least one SENSE→READOUT path consists entirely of edges that reached minimum support;
- `DEGENERATE`: germinal graph has no viable path and is trapped by excess sensory occupancy, zero-edge latent structure, or a full node budget;
- `RECOVERING`: a previously degenerate germinal graph is actively undergoing homeostatic reclamation.

## Recovery

On checkpoint restore, a germinal graph is immediately classified. A worker-3-style legacy deadlock (full node budget, latent nodes, zero edges) enters `RECOVERING`; orphan grace timers are conservatively primed because the topology itself proves that those latent nodes are already disconnected, while no missing edge or lineage is fabricated.

Normal reacclimation remains intact. Once structural maintenance is allowed again, recovery removes orphan latent nodes and excess disconnected senses incrementally under the existing per-consolidation mutation cap. Recovery clears only when the underlying topology is no longer degenerate.

## Owner-authored isolation

If `develop_senses == false`, automatic recovery, node GC and sensory eviction remain disabled. Topology health can still describe the graph, but Symbiont does not rewrite owner-authored structure.

## Next phase

Phase 5 turns these properties into longitudinal regression evidence: the exact worker-3 fixture, 2,000+ tick survival, sensory turnover, failed-hypothesis reclamation, checkpoint continuity and viability invariants.
