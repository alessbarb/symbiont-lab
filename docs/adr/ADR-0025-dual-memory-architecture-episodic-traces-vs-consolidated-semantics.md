# ADR-0025: Dual Memory Architecture: Bounded Episodic Traces vs Consolidated Semantics

## Status

Accepted

## Context

An autonomous cognitive organism requires both precise recall of recent transitions for temporal credit assignment, and generalized conceptual structures for long-term survival. Retaining raw episodic data indefinitely leads to unbounded memory growth and quadratic retrieval costs. Conversely, immediately discarding episodic traces prevents counterfactual replay and post-hoc causal discovery.

## Decision

1. **Dual memory separation.** Cognition maintains two decoupled memory stores:
   - *Episodic Experience Store:* Bounded FIFO buffer storing high-resolution transition tuples $(s_t, a_t, r_t, s_{t+1}, \tau_t)$ subjected to strict metabolic capacity limits and excretion.
   - *Semantic Cognitive Atlas:* Low-dimensional, consolidated conceptual graph storing persistent relational invariants, cross-domain bindings, and predictive weights.
2. **Unidirectional consolidation.** Information flows strictly from episodic traces to semantic models via asynchronous consolidation sweeps. Consolidation compresses topological relationships and prunes fine-grained sensor values.
3. **Mandatory excretion.** Episodic entries that have been consolidated or whose epistemic novelty has decayed below homeostatic thresholds are irreversibly excreted (deleted), maintaining a constant memory footprint throughout arbitrary organism lifespans.
4. **Epistemic priority eviction.** When metabolic stress restricts memory maintenance, eviction prioritizes discarding episodes with low predictive variance and redundant causal signatures.

## Consequences

- Long-term cognitive stability without catastrophic forgetting or memory bloat.
- Memory maintenance scales predictably with lifetime length, preserving bounded per-tick computational latency.

## Introduced in

Milestone M / Episodic Experience Memory v2.

## Evidence

`docs/design/cognition/episodic-experience-memory-v2.md`, `tests/unit/modeling/test_episodic.py`, `tests/unit/lab/test_generative_consolidation_gates.py`.
