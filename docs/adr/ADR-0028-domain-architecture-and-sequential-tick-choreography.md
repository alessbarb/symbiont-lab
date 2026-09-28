# ADR-0028: Domain Architecture and Sequential Tick Choreography

## Status

Accepted

## Context

As the internal complexity of Symbiont evolved, internal subsystems risked becoming tightly coupled through direct cross-module calls (e.g., Epistemic investigation directly commanding Action effectors, or Physiology directly mutating cognitive weights). Such unmediated cross-calling creates circular dependencies, race conditions, non-deterministic execution paths, and breaks modular auditability.

## Decision

1. **Seven decoupled core domains.** Internal organism state is strictly partitioned into seven functional domains under `symbiont.core.domains`:
   - `PerceptionDomain`: sensor ingestion and feature normalization;
   - `CognitionDomain`: latent concept activation and predictive filtering;
   - `MemoryDomain`: episodic buffering and semantic graph retrieval;
   - `EpistemicDomain`: hypothesis tracking, second-look probing, and dissent recording;
   - `EmbodimentDomain`: body schema maintenance and somatosensory binding;
   - `ActionDomain`: motor proposal generation and executive arbitration;
   - `PhysiologyDomain`: metabolic accounting, homeostatic regulation, and vital state.
2. **Prohibition of peer cross-calling.** No domain may import, instantiate, or invoke methods on another domain. For example, `EpistemicDomain` and `PhysiologyDomain` have zero knowledge of `ActionDomain` or `MotorCommand`.
3. **Choreographed sequential execution.** `OrganismRuntime` coordinates tick execution through an invariant, linear phase sequence:
   $$\text{Perceive} \longrightarrow \text{Attend} \longrightarrow \text{Decide} \longrightarrow \text{Arbitrate} \longrightarrow \text{Actuate} \longrightarrow \text{Learn} \longrightarrow \text{Regulate}$$
4. **Immutable `TickContext` mediator.** State transfer between successive phases is mediated exclusively by passing an immutable, strongly-typed `TickContext`. No mutable pointers or shared buffers are passed between domains.

## Consequences

- Completely eliminates circular dependencies and side-channel state pollution across cognitive subsystems.
- Enables granular unit testing and isolated benchmarking of individual domains.
- Guarantees deterministic tick replay from serializable tick contexts.

## Introduced in

v0.32.0 (Milestone D / Core Domain Architecture).

## Evidence

`tests/experimental_integrity/test_domain_tick_context.py`, `tests/experimental_integrity/test_runtime_domain_boundaries.py`, `tests/experimental_integrity/test_epistemic_domain_boundary.py`.
