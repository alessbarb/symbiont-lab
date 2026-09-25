---
id: design.embodiment.embodiment-v2
title: Embodiment v2 — canonical domain architecture
document_type: design
domain: embodiment
status: active
canonical: true
implementation_status: implemented
supersedes: []
extends: []
implements: []
depends_on: []
related_adrs: []
migrated_on: 2026-09-25
last_reviewed: null
review_required: false
language: en
---
# Embodiment v2 — canonical domain architecture

**Status:** implemented on `main`  
**Scope:** `symbiont` core, clean embodiment path, Physics3D adapter, passive Observatory projection

## 1. Canonical ontology

Symbiont has three distinct domain entities:

```text
Symbiont != Body != EmbodimentEpisode
Symbiont time != Body time != Embodiment time
```

- **Symbiont** owns persistent cognitive identity, genome, generalized knowledge,
  generalized motor competences and autobiographical history.
- **Body** owns physical identity, morphology, physical dynamics, physiology,
  damage, growth, age and senescence.
- **EmbodimentEpisode** owns the learned and historical coupling between one
  Symbiont and one Body.

A runtime process, PyBullet session or checkpoint save event is not an
EmbodimentEpisode.

## 2. Physical, inferred and controllable body are different

```text
Body
    what physically exists

BodySchema
    what the Symbiont currently infers about its bodily boundary/relations

execution bindings
    what the Symbiont currently has evidence to control here
```

Therefore:

```text
physical body != inferred body != controllable body
```

The core never builds BodySchema from simulator anatomy.

## 3. EmbodimentEpisode

Canonical implementation:

```text
src/symbiont/core/embodiment/episode.py
```

An Episode carries:

- `embodiment_id`
- `symbiont_id`
- `body_id`
- ordinal `epoch`
- `start_symbiont_tick` / optional `end_symbiont_tick`
- independent `embodiment_tick`
- ACTIVE / SUSPENDED / CLOSED lifecycle
- `EmbodimentContract`
- canonical BodySchema reference
- low-level sensorimotor dynamics model
- factual causal evidence ledger
- abstract competence/effect forward model
- controllability and agency models
- current execution-binding registry
- evidence-driven adaptation state
- reachability state
- hypothesis-only historical prior
- bounded contract transition history

The Episode references the same canonical inference/binding services used by
the organism runtime. It does not clone a second factual truth.

## 4. EmbodimentContract

Canonical implementation:

```text
src/symbiont/core/embodiment/contract.py
```

Schema v3 describes only the exposed opaque interface:

- perceptual surface
- actuator surface
- timing semantics
- opaque mutually-exclusive actuator groups

The fingerprint intentionally excludes:

- `body_kind`
- anatomy labels
- URDF/PyBullet link names
- learned response quality
- actuator health
- current Body dynamics
- Body identity

Two different Bodies may have the same contract. The same Body may retain its
identity while its dynamics change.

## 5. Body identity vs contract identity

`body_id` identifies one physical Body.

In Physics3D this identity is persisted in the physical Body checkpoint itself,
not only in the Symbiont bundle. A same-Body restart must therefore satisfy:

```text
physical checkpoint body_id
    ==
EmbodimentEpisode.body_id
```

Pre-v2/v3 physical checkpoints without a Body identity are migrated once: when
an associated Episode exists its Body identity is adopted; otherwise a
deterministic legacy identity is derived from the physical checkpoint. The next
physical save persists that identity and future continuity no longer depends on
the Symbiont checkpoint.

`contract_fingerprint` identifies one exposed sensorimotor interface.

They are independent:

```text
same contract != same Body
same contract != same dynamics
```

A weakening actuator can leave the contract unchanged while increasing
prediction error and forcing re-adaptation.

## 6. BodySchema

Canonical implementation:

```text
src/symbiont/core/embodiment/body_schema.py
```

The production stack has one BodySchema authority: `BodySchemaEngine`.

It learns opaque evidence including:

- sensorimotor dependencies
- self-caused channels
- separately evidenced somatic correlation
- external-channel boundary
- boundary confidence
- disruption
- revisions

Controllability alone does not make a channel part of Body.

The old `InferredBodySchema` stack remains only in
`core/embodiment/agency.py` as an explicitly retired falsification specimen.
Production code must not import it.

## 7. Two forward-model levels

The names are deliberately distinct.

### SensorimotorDynamicsModel

```text
state/percepts + motor activation
    -> expected next perceptual change
```

Implementation:

```text
core/embodiment/dynamics.py
```

This is the low-level body-dynamics model and future substrate for internal
sensorimotor simulation.

### CompetenceEffectModel

```text
competence + context
    -> expected abstract effect
```

Implementation:

```text
actuation/model.py
```

The ambiguous historical `SensorimotorModel` alias is removed.

## 8. Evidence provenance

Experienced and imagined evidence are different.

```text
EXPERIENCED
    may update factual dynamics/causal support

IMAGINED
    may support future planning/rehearsal
    must not manufacture factual Body knowledge
```

This boundary is intentionally in place before future imagination/dream work.

## 9. Competence vs execution authority

General motor knowledge:

```text
MotorCompetence
```

Current-Body authority:

```text
CompetenceExecutionBindingRegistry
```

`MotorCompetence` contains no `surface_binding` and no `executable`
truth.

A competence becomes executable only when current-embodiment factual evidence
creates a binding for the current actuator surface.

On re-embodiment:

- general competence/strategy may survive;
- current effect grounding is withdrawn;
- execution bindings are discarded;
- new factual evidence is required before execution authority returns.

## 10. Adaptation vs restart reacclimation

These are separate mechanisms.

### Restore reacclimation

Existing bounded technical mechanism after checkpoint/process discontinuity.
It protects against pretending transient microstate survived a restart.

### EmbodimentAdaptation

Implementation:

```text
core/embodiment/adaptation.py
```

Evidence-driven, not timer-driven. Tracks:

- recent prediction error
- predictive baseline
- current prediction shock
- peak prediction shock
- schema uncertainty
- causal confidence
- controllability confidence
- competence revalidation ratio
- disruption
- first revision
- recovery

No fixed number of ticks means "adapted".

## 11. Reachability

Canonical implementation:

```text
core/embodiment/reachability.py
```

Reachability is learned as opaque relationships between observed effect regions
and competences. It does not encode human anatomy or metric space.

Both clean embodiment and Physics3D update it from demonstrated control.

## 12. Longitudinal memory

Canonical persistent store:

```text
EmbodimentArchive
src/symbiont/core/embodiment/memory.py
```

Schema v3 is indexed by:

- Body identity
- contract fingerprint
- Episode summaries

Body-specific memory may contain historical:

- BodySchema prior
- dynamics prior
- execution-binding prior
- causal state
- motor candidates
- body-specific cognitive surface
- private-model references

These remain historical hypotheses.

## 13. Historical priors never carry authority

`EmbodimentPrior` has one of:

```text
novel
same-contract
same-body
```

Its serialized authority is always:

```text
hypothesis_only
```

Priority:

```text
same body
    strongest historical prior

same contract, different body
    weaker compatible-interface prior

unknown contract
    novel
```

A prior is attached to the Episode for provenance and future candidate
generation. It is never copied into active BodySchema, causal evidence or
execution bindings as truth.

## 14. Re-embodiment

Core semantics live outside Physics3D:

```text
core/embodiment/reembodiment.py
```

Conceptual sequence:

```text
close old Episode
archive Body-specific knowledge
preserve Symbiont-general knowledge
withdraw old execution authority
attach new Body
create new Episode
select hypothesis-only prior
re-ground through current experience
```

A fresh physical Body always receives a new `body_id` and
`embodiment_id`.

Returning later to the same Body can produce a `same-body` prior, but still
requires revalidation.

## 15. Runtime restart is not re-embodiment

When the same physical Body checkpoint is restored:

- same `symbiont_id`
- same `body_id`
- same `embodiment_id`
- same Episode epoch
- Episode clock continues

The Episode may move ACTIVE -> SUSPENDED -> ACTIVE without changing identity.

## 16. Physics3D boundary

Physics3D is an adapter.

It owns:

- PyBullet physical simulation
- physical Body apparatus
- physical reading collection
- physical command delivery
- physical state persistence
- construction/verification of the opaque core contract

It does not own:

- Embodiment lifecycle semantics
- BodySchema meaning
- transfer semantics
- historical authority
- general competence

The Physics3D-only descriptor is named
`PhysicsEmbodimentDescriptor`; it is not a domain contract.

## 17. Contract schema migration

Contract v3 removed nominal Body identity from the fingerprint and includes
opaque legal motor exclusions.

Old v2 Episode identity may be preserved only when an adapter explicitly
verifies equivalent sensor and actuator channels/constraints.

The default core behavior is fail-closed.

Physics3D additionally verifies:

- exact actuator channel equivalence
- motor exclusion topology
- perceptual channel count/order/availability

before authorizing v2 -> v3 Episode contract migration.

## 18. Legacy memory migration

The old `embodiment_memory` store is not active v2/v3 state.

It remains only as one-way input migration:

```text
legacy embodiment_memory
    -> EmbodimentArchive v3
```

The next canonical checkpoint no longer writes the legacy store.

Likewise, archive schema v2 is readable and migrates the former
`embodied_competence_priors` field to
`execution_binding_priors`.

## 19. Clean embodiment path

`Symbiont + Body + EmbodimentSession + Individual` uses the same ontology.

- `EmbodimentSession`: opaque port-transduction adapter.
- `EmbodimentEpisode`: persistent coupling/history.
- Session and Episode share `embodiment_id`.
- Episode shares the actual canonical inference and execution-binding objects
  used by the Symbiont.
- A transplant preserves Symbiont identity/general competence and resets
  Body-specific factual authority.

## 20. Observatory

Observatory receives an optional passive bounded Embodiment projection.

It may expose:

- Episode/Body IDs
- epoch/tick
- contract fingerprint
- lifecycle
- adaptation metrics
- dynamics summary
- execution-binding counts
- prior relation/provenance

It must not expose:

- anatomy
- physical port names
- raw learned weights
- private Body state

Observer interpretation never feeds back into cognition.

## 21. Senescence

Senescence remains exclusively Body-owned.

```text
old Body != old Symbiont
```

A long-lived Symbiont can inhabit a physically young Body without resetting its
cognitive history.

## 22. Architectural guards

Tests explicitly protect:

- production does not import the retired inference stack;
- `MotorCompetence` cannot regain execution authority;
- run catalog reads `EmbodimentArchive`, not legacy memory;
- same-Body restart preserves Episode identity;
- fresh Body creates a new Episode;
- same-contract and same-body priors are distinct;
- historical prior authority is rejected;
- contract history is bounded;
- imagined evidence does not update factual dynamics;
- Observatory projection is bounded/passive;
- incompatible contract migration fails closed.

## 23. Current legacy exceptions

The following are intentional and must not be mistaken for parallel runtime
architectures:

1. `core/embodiment/agency.py`: retired component specimen used only by
   explicit adversarial/falsification studies.
2. Reads of `embodiment_memory`: pre-v2 one-way migration only.
3. Reads of archive field `embodied_competence_priors`: archive schema-v2
   migration only.
4. Legacy contract fingerprint function: migration/comparison of historical
   checkpoints only.

They must not become writable or authoritative production state again.

## 24. Scientific validation target

The architecture supports a falsifiable sequence such as:

```text
crawler
-> humanoid A
-> humanoid B
-> damaged humanoid A
-> repaired humanoid A
```

Measure:

- causal-discovery latency
- prediction-error convergence
- BodySchema convergence
- competence revalidation/acquisition
- transfer advantage over naive control
- same-Body return savings

If prior experience provides no measurable advantage over an equivalent naive
Symbiont, cross-embodiment transfer has not been demonstrated.

## 25. Future imagination boundary

Embodiment v2 intentionally provides the state required by future imagination:

```text
BodySchema
+ SensorimotorDynamicsModel
+ CompetenceEffectModel
+ WorldModel
-> internal rollout
```

But simulated transitions remain hypotheses. Reality must validate them before
they become factual Embodiment evidence.
