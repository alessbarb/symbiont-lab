# ADR-0013: Longitudinal Re-embodiment and Symbiont/Body Decoupling

## Status

Accepted

## Context

Early versions of Symbiont coupled the organism's computational identity directly with its immediate morphological instantiation. When a body suffered irreversible mechanical destruction or starvation, the entire organism was terminated, making multi-epoch ontogenetic adaptation and morphological transfer impossible without unnatural ad-hoc state transplants.

## Decision

1. **Ontological separation.** `Symbiont` (cognitive identity, historical memory, consolidated beliefs, epigenetic marks) is structurally decoupled from `Body` (physical morphology, actuator limits, sensory receptors, kinetic state).
2. **Embodiment episodes and epochs.** A physical lifespan is bounded within an `EmbodimentEpisode`. Physical body death (`BodyState.DEAD`) closes the active episode with termination reason `BODY_DEATH`.
3. **Dormancy and continuity.** Physical death terminates the body, not the cognitive subject. Upon body death, the `Symbiont` transitions to a dormant state. The causal checkpoint preserves consolidated cognitive structures, relational memory, and developmental baselines.
4. **Re-embodiment.** A dormant Symbiont may undergo re-embodiment into a new physical body (either identical or altered morphology), initiating a new `EmbodimentEpoch`.
5. **Body schema re-acclimation.** Sensorimotor bindings, receptive field calibrations, and actuator associations (`BodySchema`) are re-discovered and calibrated upon entering each new body. Core consolidated knowledge remains intact without somatic crosstalk or corruption.

## Consequences

- Supports longitudinal developmental studies across morphological transitions and lifecycles.
- Physical consequence completeness is preserved: bodies die irreversibly, but phylogenetic and ontogenetic knowledge persists.
- Memory models must differentiate between body-relative sensorimotor calibrations and invariant relational/world knowledge.

## Introduced in

v0.30.0 (Milestone H).

## Evidence

`tests/experimental_integrity/test_embodiment_v2_architecture.py`, `tests/experimental_integrity/test_reembodiment_reacclimation.py`.
