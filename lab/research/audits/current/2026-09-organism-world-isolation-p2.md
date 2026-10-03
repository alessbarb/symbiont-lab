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

### High D — reproduction decontamination — resolved by Living Body L5

The historical cognitive-reproduction stack has been removed from the canonical
core:

- `ReproductivePressure` no longer exists in the canonical runtime;
- blocked cognitive growth, topology saturation and adaptation no longer
  contribute to reproductive readiness;
- `HabitatBirthAuthority` now manages identity, lineage and population
  capacity only; it owns no physical resource currency;
- successful asexual birth transfers physical energy from parent to child;
- denied birth leaves parental energy unchanged.

Canonical clean World still injects no birth authority. Population studies may
attach one explicitly at the experimental boundary, but readiness remains
organism-owned physiology.

P2/L5 boundary:
- readiness derives only from `LivingBodyState` through `OntogenyController`;
- World may deny materialization through carrying capacity;
- no evaluator score, semantic `REPRODUCE` objective or cognitive saturation
  signal enters the organism.

### High E — resolved: legacy semantic action vocabulary removed from core

The typed selector this finding described (`ActionKind`/`ExpectedOutcome`/
`LocalActionModel`, with `viability`/`reproductive_feasibility` dimensions)
was removed from canonical `symbiont.core.runtime` at checkpoint schema v9
(`src/symbiont/host/checkpoint.py`); `symbiont.core.behavior` no longer
exists, and a v8 checkpoint carrying any of its state is hard-rejected
rather than migrated.

A residual re-derivation of the same vocabulary (bare string matches on
`action_id` — `"rest"`, `"observe"`, `"intake"`, `"compete"`, `"reproduce"`,
`"social_exchange"` — mapped to narrative-journal labels in
`OrganismRuntime.tick`) was found and removed; the raw, opaque `action_id`
remains a passive Observatory display field, unchanged.

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

### Medium G — resolved: repair is now constitutive physiology

`HomeostaticController.constitutive_step` (`src/symbiont/core/homeostasis.py`)
now runs unconditionally every tick from `OrganismRuntime.tick`
(`src/symbiont/core/runtime.py`), with no `repairable_damage` parameter or
semantic action gating it. Damaged `structural_integrity` repairs
automatically, bounded by `autonomous_repair_rate` and available
`maintenance`/physical `energy_reserve`, and `MetabolicLedger.charge`
deducts that repair directly from `LivingBodyState.energy_reserve`.

The organism now has a complete, physically costly, organism-owned
healing/recovery affordance — exactly the "metabolically costly physiology"
design this finding originally called for, not `ActionKind.REPAIR`.

### Medium H — reproduction/ontogeny/senescence — resolved by Living Body L5

The canonical Living Body now has:

- energy-backed physical growth;
- maturity derived from `growth_progress`;
- age-driven senescence with constitutive wear;
- physiological reproductive readiness;
- conservative parent-to-child birth energy transfer;
- a physically immature, cognitively germinal child state.

Physics3D moved to constitution `genome_symbiont_physics3d_v6` because the
Living Body checkpoint now includes ontogeny. Pre-L5 Living Body checkpoints
fail closed instead of silently inventing developmental state.

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
