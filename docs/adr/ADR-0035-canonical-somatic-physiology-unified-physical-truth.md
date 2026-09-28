# ADR-0035: Canonical Somatic Physiology: Single Unified Physical Truth

## Status

Accepted

## Context

Prior to Living Body P0, the codebase maintained dual, overlapping physiological state models: `BodyPhysiology` (tracking physical variables such as temperature, integrity, and collision damage) and `MetabolicLedger` (tracking computational reserves, maintenance costs, and cognitive execution burn). This split created desynchronization bugs, such as an organism remaining mechanically alive while its computational reserve died, or an organism starving while its physical body was undamaged.

## Decision

1. **Unification of somatic truth.** A single component (`LivingBody` / `PhysiologyDomain`) owns all physical and metabolic state variables:
   - Physical energy reserve, structural integrity, internal temperature, and canonical vital state (`VitalState`);
   - Computational energy expenditure (observation, neural integration, persistence) is deducted directly from the body's unified physical energy reservoir.
2. **Local body lifecycle.** Age, growth, physical wear, senescence, and death are strictly local to the current morphological instance (`Body`). They do not represent the age or death of the persistent cognitive identity (`Symbiont`, ADR-0013).
3. **No parallel survival authorities.** `MetabolicLedger` is absorbed into canonical somatic physiology. No secondary ledger or cognitive module may declare an organism alive or dead independently of the canonical living body.
4. **Physical death consequence.** When somatic integrity reaches 0.0 or vital state transitions to `DEAD`, the body terminates irreversibly, releasing physical resources and detritus into the local environment (ADR-0023).

## Consequences

- Completely eliminates desynchronized death states and dual-authority race conditions.
- Every cognitive calculation and sensory observation has direct, measurable consequences for physical survival.
- Physiological state can be audited and serialized in a single, unambiguous checkpoint block.

## Introduced in

Milestone L (Living Body P0).

## Evidence

`docs/design/embodiment/living-body-p0.md`, `src/symbiont/core/domains/physiology.py`, `tests/unit/host/test_interoception.py`.
