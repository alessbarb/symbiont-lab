# ADR-0022: Factorized Effect Representation & Causal Agency Attribution

## Status

Accepted

## Context

In high-dimensional embodied systems (such as Physics3D with 62 effectors and 107 receptors), defining an "effect" as the holistic quantized change of all somatic features simultaneously leads to combinatorial saturation. In practice, 84% of whole-state signatures recur only once, preventing the formation of stable competences or intentional agency. Furthermore, holistic signatures confound an agent's true motor consequences with passive environmental drift (gravity, momentum, or external perturbations).

## Decision

1. **Atomic effect decomposition.** Consequence signatures are factorized into discrete, directional tokens:
   `EffectAtom(feature_ref, direction, magnitude_class)` where `direction ∈ {+, -}` and `magnitude_class ∈ {1, 2, 3}`.
2. **Consequence versus passive drift.** An effect is strictly defined as what an intervention *changes beyond what occurs passively*. Counterfactual evidence windows isolate feature deltas attributable to self-action from passive background drift.
3. **Single factual ledger.** All effect attribution derives exclusively from `CausalEvidenceLedger`. Internal mental simulation or imagination is strictly forbidden from writing effect instances.
4. **Graded equivalence.** Effects are compared via similarity metrics in `EffectMatcher` rather than rigid whole-state identity, enabling robust generalization across varying environmental conditions.
5. **Semantic-free identities.** Effect tokens are content-addressed hashes over opaque feature indices and numerical magnitude classes, exposing no anatomical or environmental labels.

## Consequences

- Stable recurring effects form even in high-dimensional morphological substrates.
- Prevents false attribution of external physical dynamics (wind, gravity, contact with peers) to internal agency.
- Competence bindings and intentional planning can reliably converge in 3D physics.

## Introduced in

Milestone E4 / Executive Outcome Learning v1.1.

## Evidence

`docs/design/core/factorized-effect-representation-v1.md`, `lab/tests/unit/lab/test_structured_causal_experience.py`, `tests/unit/core/test_causal_provenance.py`.
