# ADR-0036: Hypothesis-Driven Reactivation of Embodiment Memory

## Status

Accepted

## Context

During longitudinal re-embodiment experiments (e.g. humanoid $\to$ asymmetric crawler $\to$ humanoid), the organism preserves historical identity and general relational memory across successive bodies. However, when returning to a previously mastered morphology, the organism faced a dilemma: either discard historical body schemas and relearn from scratch, or blindly assume that past motor calibrations remain valid, risking catastrophic motor errors if joint calibrations or sensor scales have drifted.

## Decision

1. **Embodiment-scoped body knowledge.** Sensorimotor coordinate maps, receptive field calibrations, and actuator associations belong strictly to an explicit `EmbodimentContract`.
2. **Persistence across morphological changes.** Transitioning to a new morphological contract does not erase historical body knowledge; past body schemas are archived into `EmbodimentMemory`.
3. **Retrieval as unverified hypotheses.** When re-entering a previously encountered morphology, historical body schemas are retrieved strictly as *hypotheses* ($H_{\text{prior}}$), never as authoritative, operative truth.
4. **Empirical evidence requirement for reactivation.** Historical motor bindings and receptive field expectations cannot command high-torque physical actions until validated against current sensory feedback from the new body.
5. **No researcher channel mapping.** The Lab/evaluator is strictly prohibited from asserting semantic equivalence between historical and current sensory/motor channels. Grounding must be established endogenously by the organism.

## Consequences

- Acceleration of re-acclimation when returning to familiar body plans without sacrificing safety.
- Protects the physical body from executing violent or miscalibrated motor commands based on stale historical memories.
- Clean separation between morphological memories and abstract, invariant cognitive knowledge.

## Introduced in

Milestone H3 / Embodiment Memory v1.

## Evidence

`docs/design/embodiment/embodiment-memory-v1.md`, `lab/tests/experimental_integrity/test_reembodiment_reacclimation.py`.
