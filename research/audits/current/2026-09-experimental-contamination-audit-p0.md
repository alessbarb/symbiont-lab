# Experimental contamination audit — P0

Date: 2026-09-20
Status: corrective audit; canonical World boundary changed in this branch

## Audit question

Does the canonical persistent Symbiont World currently justify the strong claim
that organism-facing meaning, useful actions and environmental categories are
discovered rather than supplied by the experimenter?

## Pre-correction verdict

**No.**

The cognitive graph was genuinely germinal, but the canonical World path still
contained multiple experimenter-supplied shortcuts that made a strong
"discovers everything" claim invalid.

## Findings

### P0-1 — Typed behavior and utility priors

The core runtime contains a typed action vocabulary:

- REST
- INTAKE
- REPAIR
- OBSERVE
- INVESTIGATE
- SOCIAL_EXCHANGE
- COMPETE
- REPRODUCE
- WAIT

and owner-authored ExpectedOutcome priors. The selector then combines viability,
integrity, resource change, reproductive feasibility, social expectation and cost.

This is legitimate for historical behavior studies but contaminates a strong
emergence experiment.

**Correction:** canonical clean World sets `autonomous_behavior=False` and does
not call that action frontier. World records only whether an opaque motor actuation
occurred.

### P0-2 — Direct resource/hazard percept segmentation

The previous World capability surface included one opaque ID per field, resource
and hazard. Hashing the label hides the human word but does not undo the
experimenter's segmentation.

**Correction:** canonical clean World exposes only eight mixed physical receptor
channels. Resource quantities contribute as physical material presence through a
fixed transfer matrix. Hazard probability/exposure is not sensed.

### P0-3 — Occupancy concept supplied

The previous local observation exposed a precomputed local occupancy-density
signal.

**Correction:** occupancy density remains apparatus-side World physics where
needed (for example density-coupled hazards) but is not available as a subject
receptor.

### P0-4 — One-to-one substrate labels

Surface water, detritus and disturbance were individually exposed as opaque
signals. Their names were hidden, but their factorization was supplied.

**Correction:** they contribute only through mixed receptors in canonical clean
World.

### P0-5 — Semantic bootstrap flag

The World adapter constructed runtimes with `bootstrap_semantic_senses=True`.
The current World manifest did not contain the legacy CPU/disk capabilities, so
the known aliases did not appear in normal World cognition, but the configuration
was an unnecessary contamination risk.

**Correction:** clean World forces the flag off and fails closed if it returns.

### P0-6 — Free metabolic replenishment

Founders received 0.25 automatic replenishment per metabolic reserve per tick.

This weakens ecological dependence and can allow survival without discovering
physical material acquisition.

**Correction:** clean founders receive zero automatic replenishment. The opaque
local-interaction motor channel can physically transfer local material.

### P0-7 — Apparatus picked a preferred resource

The previous local interaction chose the most abundant available resource before
transferring it.

**Correction:** clean local interaction couples proportionally to all physically
present material. No resource identity enters the command or subject observation.

### P0-8 — Persistent World did not exercise motor affordances

`WorldRuntimeState` previously constructed `PopulationGenesisRuntime` with
movement disabled by default.

**Correction:** fresh canonical World enables actuation/movement, sensory
plasticity and sense discovery.

### P0-9 — Shared signal identity namespace

The runtime default signal-identity key was common across organisms. This is not a
semantic label, but it can create artificial cross-organism alignment relevant to
future culture/communication studies.

**Correction:** clean founders receive per-organism private signal identity keys.

### P0-10 — Structured reception/contact side channels

Even after mixed receptors, retaining structured `reception` in the subject
WorldObservation would preserve a parallel pre-segmented channel.

**Correction:** clean observation consumes apparatus reception into receptor
mixing and then clears structured contact/reception/internal side channels.

## Confirmed clean properties

The packaged base graph is empty:

```json
{"nodes": [], "edges": []}
```

The base genome has `initial_concepts = 0`.

Physical-affordance motor mappings remain apparatus truth; cognition sees actuator
IDs and later consequences, not the meanings move/acquire.

Evaluator-only effective fertility, ecological pressure and effective
permeability remain outside subject perception.

## Allowed innate bias

P0 does not pretend the organism has no priors. The following remain inherited
constitution:

- body morphology;
- fixed finite receptors and their transfer functions;
- finite opaque actuator channels;
- motor probing/exploration machinery;
- learning/plasticity rules;
- metabolic capacities;
- homeostatic and viability dynamics;
- hard computational limits;
- World physics.

These must be reported as innate mechanisms, never as discoveries.

## Remaining non-canonical semantic code

Typed behavior, social policies, reproduction helpers, symbol policies and private
model machinery still exist in the repository for historical/controlled studies.
They are not deleted by P0.

The scientific claim therefore applies specifically to the **canonical clean
World path**, not to every possible runtime configuration in the repository.

## Runtime enforcement

Canonical clean World now fails closed if it detects:

- semantic bootstrap;
- typed autonomous behavior;
- privileged interoception;
- founder behavioral loci;
- free metabolic replenishment;
- forbidden clean motor effects;
- direct resource/hazard/occupancy/substrate capability IDs;
- direct apparatus IDs in a generated clean observation.

The mode is persisted in checkpoint schema v4 and included in the World
constitution boundary.

## Post-correction claim

P0 supports the following statement:

> The canonical persistent World supplies physical constitution and learning
> machinery, but does not supply organism-facing resource, hazard or action
> semantics.

It does **not** establish that useful concepts or strategies have already emerged.
That requires causal experiments with frozen, shuffled and ablated controls.


## P0-11 — Removing semantics must not remove the body

The first clean draft disabled the named `InteroceptionProvider` and stripped
structured internal channels, which correctly removed semantic shortcuts but risked
making physiological benefit cognitively invisible.

**Correction:** the canonical clean boundary now mixes bounded somatic physics
(reserve ratios, integrity and activity scale) into the same opaque receptor bank.
The subject never receives those apparatus names or a good/bad label. This
preserves a legitimate causal path from material acquisition or damage to later
perception without restoring typed action utility.

No generic motor reward is added in P0. The current motor learner establishes
controllability, not valence. Therefore P0 still does not support the stronger
claim that the organism has learned to prefer survival-improving affordances; that
requires a separate empirical/mechanistic gate.
