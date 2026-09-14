# Reversible Structural Plasticity — Phase 2

## Goal

Remove the bootstrap deadlock observed in the germinal CognitiveGraph by separating node activity from evidence that an edge actually transmitted signal, and by preventing structurally illegal SENSE-target candidates from entering generic structural memory.

## Changes

1. Edge use is based on transmitted contribution (`abs(weight * source_activation)`) rather than requiring both source and target nodes to cross the global node-activity threshold.
2. `StructuralPlasticity.observe_coactivation` accepts optional node kinds and rejects candidate accumulation whenever the target is `SENSE`; this makes SENSE→SENSE and latent→SENSE candidates impossible before they enter the pool.
3. `CognitiveBridge` supplies node kinds to the generic candidate pool while continuing to route SENSE↔SENSE coactivity only through the germinal concept-support pool.
4. Focused regressions cover low-activation targets, illegal SENSE targets, and survival of the first germinal concept/readout bundle beyond its tentative lifetime.

## Non-goals

This phase does not add node GC, ConceptLineage, sensory leases, topology health states, or recovery of already-degenerate checkpoints. Those remain Phases 3–4.
