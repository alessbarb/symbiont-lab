# ADR-0015: Immutable Mathematical Kernel and Data Plasticity Limits

## Status

Accepted

## Context

Artificial life and continuous learning frameworks frequently attempt adaptability through dynamic metaprogramming: modifying class hierarchies, synthesizing runtime ASTs, executing `eval`/`exec`, or allowing unbounded graph creation. In a scientific research apparatus, dynamic code modification destroys deterministic replay, breaks formal boundary validation, risks process escalation, and causes unbounded memory exhaustion.

## Decision

1. **Zero dynamic code execution.** The `symbiont` package strictly prohibits runtime code synthesis, dynamic execution via `eval()` or `exec()`, runtime module injection, or self-modifying source code.
2. **Closed mathematical kernel.** Ontogenetic and phylogenetic adaptation operates strictly as numerical data plasticity (Oja's modified Hebbian rule, Welford online variance, Bayesian belief updating, eligibility trace integration) over an immutable, closed computational kernel.
3. **Hard architectural limits (`KernelLimits`).** Cognitive networks and concept spaces operate under closed numeric ceilings:
   - Maximum neural nodes: `KernelLimits.max_nodes = 192`
   - Maximum latent concepts: `KernelLimits.max_concepts = 32`
   - Maximum plastic synapses: `KernelLimits.max_edges = 1536`
   - Synaptic weight saturation: `[-2.0, 2.0]`
   - Neuronal time constants: $\tau \in [0.1, 10.0]$
   - Attention budget cap: `1.0`
4. **Finite memory and mandatory excretion.** Episodic and relational memory structures implement finite capacity limits and mandatory eviction policies (metabolic excretion) to prevent memory accumulation attacks or unbounded growth.

## Consequences

- Strict deterministic continuation is guaranteed when initialized from identical seeds and checkpoints.
- Memory footprint and computational cost per tick remain constant and bounded throughout infinite lifespans.
- The organism's internal structure can be audited, visualized, and verified mathematically at all times.

## Introduced in

v1.0.0 (`experimental-organism-v1`).

## Evidence

`src/symbiont/cognition/limits.py`, `tests/experimental_integrity/test_architecture_convergence.py`.
