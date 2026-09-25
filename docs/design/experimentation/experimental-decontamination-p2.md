---
id: design.general.experimental-decontamination-p2
title: "Experimental Decontamination P2"
document_type: design
domain: experimentation
status: active
canonical: true
implementation_status: implemented
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
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
        -> one organism-owned physical energy pool
        -> organism-owned functional cost accounting

The World cannot choose observation/cognition/persistence/maintenance accounting
categories. Those categories are not independent physical reserves.

## No cognitive fuel

Canonical clean World sets explicit_metabolism=False.

Prediction accuracy and information assimilation may affect learning, memory and
future behavior, but cannot mint metabolic reserve. Energy must enter through the
physical body boundary.

## Reproduction

Reproduction is now organism-owned physiology.

- readiness is derived from `LivingBodyState` through `OntogenyController`;
- no cognitive topology, adaptation score, blocked growth or evaluator signal
  contributes to readiness;
- the organism has no semantic `REPRODUCE` reward or objective;
- successful birth transfers physical energy from parent to child;
- `HabitatBirthAuthority` allocates identity, lineage and carrying-capacity
  only; it owns no resource currency;
- World may deny materialization through external carrying capacity, but may
  not create readiness;
- lineage/evaluator records remain apparatus-side.

Canonical clean World still does not inject a birth authority into a subject.
Population experiments may attach one explicitly at the experimental boundary.

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


## Living Body P0 alignment

[Living Body P0](living-body-p0.md) is now the canonical next step.

This strengthens, rather than relaxes, P2:

- physical physiology is organism-owned and singular;
- reproductive readiness is now derived from physiology rather than
  cognitive/adaptive state;
- organism-facing body signals are multidimensional and opaque;
- scientific motor probes may remain Lab controls but are not accepted as
  organism-discovered behavior;
- no reward or World objective is introduced.

Until the Living Body acceptance gate passes, canonical clean-world claims stop
at constitutive physical viability plus opaque causal experience.
