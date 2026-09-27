# Anatomy of an action

An action begins before the actuator moves and finishes after the body has produced a consequence.

## Before execution

Cognition and internal regulation can expose candidate possibilities. The agency/action layers determine whether a possibility is afforded, sufficiently supported and compatible with current constraints. Admission creates an intention; reconciliation and arbitration determine what becomes an active commitment.

A commitment then binds to a competence or exploratory controller. `ActuatorSystem` is deliberately late in the chain: it validates requested channel values against the current actuator surface and returns the delivered activations.

## Physical execution

In Physics3D, delivered actuator values are applied to the apparatus. PyBullet then advances several physical substeps. Contact, gravity, inertia, joint limits and resource interactions produce consequences that are not under direct cognitive control.

## Observation closes the loop

On the next organism tick, those consequences return through perception. `ActionDomain.observe_consequences()` compares the observed transition with the active attempt and updates causal evidence, competence state and commitment outcome before current cognition proceeds.

This ordering means an action is not scientifically complete at command emission. Its causal unit is closer to:

```text
proposal
→ admitted intention
→ commitment
→ controller
→ delivered actuation
→ body/world dynamics
→ sensed consequence
→ outcome evidence
→ competence/executive update
```

The distinction is especially important when evaluating agency. A system that emits motor commands has actuation; evidence that observed consequences change later action admission is stronger evidence of a learned closed loop.
