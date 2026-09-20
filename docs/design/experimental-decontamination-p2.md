# Experimental Decontamination P2 — Organism / World Isolation

Status: implemented candidate.

## Principle

The organism may be constituted with body, metabolism, homeostasis, plasticity,
sensors and effectors. The World may provide physics.

The World must not:

- inject resource identities into the organism;
- select internal metabolic compartments;
- create metabolic reserve from cognitive success;
- provide reproductive authority or reproductive pressure;
- provide semantic action opportunities or utility priors;
- expose evaluator truth through a side channel.

The clean organism must remain meaningful if World is replaced by another physical
environment implementing the same minimal boundary.

## Canonical clean boundary

World -> organism:

1. opaque receptor values;
2. anonymous scalar metabolic absorption caused by physical contact/work;
3. physical damage;
4. anonymous motor consequences.

Organism -> World:

1. opaque motor actuation;
2. emissions/body effects explicitly represented by the body boundary.

No resource id, hazard id, world coordinate, semantic action type, lineage policy
or evaluator score crosses inward.

## Resource isolation

Canonical clean World does not attach SharedHabitat resource surfaces to the
organism. Resource identity remains World truth.

Physical material exchange is resolved in World and crosses the body boundary only
as a scalar amount:

    world material interaction
        -> scalar absorbed magnitude
        -> OrganismRuntime.absorb_metabolic_energy(amount)
        -> organism-owned distribution across internal reserves

The World cannot choose observation/cognition/persistence/maintenance reserves.

## No cognitive fuel

Canonical clean World sets explicit_metabolism=False.

Prediction accuracy and information assimilation may affect learning, memory and
future behavior, but cannot mint metabolic reserve. Energy must enter through the
physical body boundary.

## Reproduction

P2 deliberately keeps reproduction disabled in canonical clean World until it is
redesigned as organism-owned physiology.

The existing legacy ReproductivePressure / HabitatBirthAuthority / ActionKind.REPRODUCE
path remains for historical studies, but is forbidden by the clean-world boundary.

Future reproduction must satisfy:

- readiness is a physiological state, not a World instruction;
- the organism has no semantic REPRODUCE action;
- World may resolve space/material constraints after a bodily reproductive process
  starts, but may not create the motivation to start it;
- lineage/evaluator records remain apparatus-side.

## Fail-closed invariants

Clean World rejects any organism with:

- non-empty World resource habitats;
- cognition-derived metabolic replenishment enabled;
- World-owned birth authority or reproductive pressure;
- semantic bootstrap;
- typed autonomous behavior;
- privileged interoception;
- structured motor probing;
- direct resource/hazard/substrate identities.

## Interpretation

Allowed innate constitution:

> My body can deteriorate, consume finite internal reserve, absorb physical energy,
> be damaged, recover through physiological mechanisms, and produce bodily change.

Forbidden supplied knowledge:

> This is food; this action is repair; reproduce now; this outcome increases
> fitness; accurate predictions deserve energy.

P2 therefore separates biological need from semantic objective.
