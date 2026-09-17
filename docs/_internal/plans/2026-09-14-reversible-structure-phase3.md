# Reversible Structural Plasticity — Phase 3

## Goal

Give germinal cognitive nodes a durable lifecycle so failed hypotheses and historical sensory interfaces release capacity instead of accumulating forever.

## Changes

- Persist `ConceptLineage {concept_id, parent_ids, born_tick}` independently of current edges.
- Use lineage when checking whether a SENSE pair already owns a concept, so pruning does not erase provenance.
- Track `sense_last_seen_tick` leases for germinal SENSE nodes.
- Enforce `sense_node_budget` on admission, independently from the total node budget.
- Evict only disconnected SENSE nodes, prioritizing stale leases and then the oldest nodes required to return under budget.
- Track orphan CONCEPT/READOUT nodes and garbage-collect them after the structural tentative-lifetime grace period.
- Persist lineage, leases and orphan timers in the cognitive bridge checkpoint, with bounded validation and conservative reconstruction for legacy checkpoints.
- Reconcile normalizers, concept candidate evidence, structural candidate memory and lifecycle metadata when nodes disappear.
- Reuse node capacity reclaimed by maintenance in the same consolidation transaction before attempting new growth.

## Owner-authored isolation

Automatic leases, GC and provenance-driven concept maintenance run only when `develop_senses == true`. Owner-authored graphs remain structurally stable unless explicitly opted into germinal development.

## Remaining work

Phase 4 adds explicit topology-health states, automatic recovery of already-degenerate checkpoints, and formalizes the maintenance → budget recovery → growth transaction as a viability invariant. Phase 5 supplies longitudinal and worker-3 regression fixtures.
