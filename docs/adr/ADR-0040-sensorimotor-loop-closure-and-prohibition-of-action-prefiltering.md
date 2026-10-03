# ADR-0040: Sensorimotor Loop Closure and Prohibition of Action Pre-Filtering

## Status

Accepted

## Context

In early simulation engines, the simulation environment filtered available actions before presenting them to the agent (e.g., removing a "move north" option if an obstacle occupied that cell). This pre-filtering artificially endowed the organism with downward ground-truth knowledge of the physical world prior to action execution, bypassing the necessity of sensorimotor exploration.

## Decision

1. **Closed sensorimotor loop.** The motor execution pathway is closed symmetrically to the sensory intake pathway:
   $$\text{Percept} \longrightarrow \text{Cognition} \longrightarrow \text{MotorReadout} \longrightarrow \text{MotorIntention} \longrightarrow \text{ActuatorSystem} \longrightarrow \text{Actuation} \longrightarrow \text{World}$$
2. **Translation without pre-filtering.** The Lab and World adapters translate an emitted `Actuation` into physical consequences, but are strictly prohibited from filtering, vetting, or selecting actions on behalf of the organism.
3. **Right to fail.** The organism is fully permitted to attempt invalid, impossible, or blocked actions (e.g. attempting to walk into an impassable wall, or activating a severed joint). The World resolves these attempts as null displacement, mechanical collision damage, or somatic resistance.
4. **Empirical consequence learning.** The organism must learn physical boundaries and obstacle affordances strictly from post-action consequences and proprioceptive prediction errors, never through pre-decision affordance gifts.

## Consequences

- True sensorimotor grounding: obstacles and constraints are learned rather than externally protected.
- Preserves the integrity of counterfactual motor babbling and agency acquisition experiments.

## Introduced in

Milestone A1 (Symbiont Actuation v1).

## Evidence

`docs/design/sensorimotor/symbiont-actuation-v1.md` (§1), `lab/tests/unit/lab/world/test_actuation_adapter.py`, `lab/tests/unit/lab/world/test_actuation_end_to_end.py`.
