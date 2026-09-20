# Adversarial audit — organism/world isolation and basic-needs boundary

Date: 2026-09-20
Status: P2 remediation implemented candidate

## Criterion

Allowed innate content is limited to constitution and physiology: finite body,
metabolism, homeostasis, damage, death, plasticity, sensory/motor embodiment and
bounded spontaneous activity.

Forbidden supplied content includes semantic goals, strategies, interpretations,
fitness objectives, named needs and apparatus-selected priorities.

The World may provide physics and consequences. It may not decide what the
organism should value or inject privileged world truth into the subject.

## Findings

### Critical A — resource identity leaked through the core runtime

P0/P1 mixed World resources into opaque physical receptors, but clean organisms
also received SharedHabitat objects keyed by World resource ids. OrganismRuntime
then synthesized habitat_surface.<resource_id> readings and inserted them into
signal knowledge/cognition.

This bypassed the adapter decontamination boundary.

P2 remediation:
- clean organisms receive no resource_habitats;
- clean World resource identity remains apparatus-side;
- clean material exchange crosses only as an untyped scalar absorption amount.

### Critical B — cognition could mint metabolic reserve

With explicit_metabolism enabled, successful information assimilation and low
prediction error replenished metabolic compartments.

This turned epistemic success into physical fuel and created an implicit reward
channel. A subject could partially survive by predicting well rather than by
obtaining physical energy.

P2 remediation:
- canonical clean organisms set explicit_metabolism=False;
- physical absorption is the only replenishment path;
- cognition may still cost energy and change learning, but cannot create energy.

### High C — organism identity depended on World identity

Clean receptor ids, BodySchema salt and SignalIdentity key were derived partly from
world_id/world_seed. The same organism constitution instantiated in another World
therefore changed internally merely because the apparatus changed.

P2 remediation:
- internal identity derives from organism_seed + organism_id;
- world identity no longer contributes to receptor namespace, BodySchema salt or
  SignalIdentity.

### High D — legacy reproduction is semantically contaminated for canonical use

The core still contains a historical reproduction stack:
- ActionKind.REPRODUCE;
- ReproductivePressure;
- HabitatBirthAuthority;
- reproductive_feasibility in ExpectedOutcome;
- a selector that explicitly includes reproductive feasibility in action ranking.

This is suitable only as a historical/control surface. It must not become the
canonical basic need for descendants.

P2 boundary:
- canonical clean organisms must have no birth authority and no reproductive
  pressure;
- the boundary fails closed if World injects either.

Required future design:
reproductive readiness must be organism-owned physiology; initiation must emerge
from bodily/cognitive dynamics without a semantic REPRODUCE action. World may only
resolve physical space/material consequences after initiation.

### High E — legacy semantic action vocabulary remains inside core

The core still exposes REST, INTAKE, REPAIR, OBSERVE, INVESTIGATE,
SOCIAL_EXCHANGE, COMPETE, REPRODUCE and WAIT plus ExpectedOutcome dimensions such
as viability and reproductive_feasibility.

Canonical clean World currently bypasses this frontier, so it is not a current
causal contamination path. However it is architectural debt and an attractive
future shortcut.

Required P3:
extract the typed behavior/utility system from the canonical organism runtime into
a legacy/research compatibility surface. New needs must not be built on it.

### Medium F — homeostatic reflexes are innate policy-like mechanisms

Homeostasis automatically reduces activity, pauses plasticity and may enter safe
mode under resource pressure. Physiology maps severe pressure to dormant/agonizing
states and unrecoverable pressure to death.

Assessment:
acceptable as constitutional physiology if these mechanisms are reported as innate
body dynamics, never as learned survival strategy.

A future audit should distinguish:
- automatic bodily regulation (allowed);
- cognitive action selection hard-coded to preserve viability (forbidden).

### Medium G — repair is not yet a clean learned affordance

Canonical clean World bypasses typed REPAIR. Automatic HomeostaticController
repair occurs only when repairable_damage is explicitly supplied, and the current
clean World path does not provide a semantic repair action.

Therefore the clean organism currently has damage/death but not a complete
organism-owned healing/recovery affordance.

Future basic-needs design should model repair as metabolically costly physiology or
primitive body dynamics, not as ActionKind.REPAIR.

### Medium H — reproduction/ontogeny/senescence are incomplete in canonical World

Current canonical World has real mortality pressure but no clean reproduction
cycle, maturation or organism-level senescence.

These should be introduced as physiology/constitution only after the P3 semantic
action extraction.

## P2 invariant

For canonical clean World, the intended inward causal surface is now limited to:

1. opaque receptor values;
2. scalar physical metabolic absorption;
3. physical damage;
4. anonymous motor consequences.

No World resource identity, coordinate, hazard label, lineage policy, semantic
action type, evaluator score or cognitive reward may cross inward.

## Basic-needs conclusion

Survival should not be a goal. It should emerge from finite reserves, damage,
homeostatic dynamics and irreversible death.

Descendance should not be a goal. It should emerge from a bodily reproductive
process with maturity, energetic cost and physical constraints.

The governing rule is:

> Constitution may create vulnerability and capability. Meaning, strategy and
> purpose must be learned.
