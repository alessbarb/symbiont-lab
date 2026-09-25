---
id: design.world.symbiont-world-v3
title: "Symbiont World V3"
document_type: design
domain: world
status: active
canonical: false
implementation_status: implemented
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Symbiont World — Persistent World & Scientific Observatory

**Status:** implemented in `main` (P0–P6) and hardened on 19-Sep-2026. This pass adds rollback preserving the organism's reference graph, segmented durable journal, fallback from corrupt `HEAD`, incremental event API, and strict provenance in Observatory. The corresponding regression tests are coded; this pass does not depend on GitHub Actions.
**Scope:** `symbiont_world` + `symbiont_lab.world` + World Observatory.
**Guiding principle:** the world must be able to exist, evolve, survive restarts and be observed exhaustively without the observation modifying its causality.

---

## Implementation and recovery note

The v3 persistence distinguishes between **recoverable full state** and **confirmed descriptive events**. The journal events are not used to invent or reconstruct missing cognitive state. If the checkpoint pointed by `HEAD` is corrupt, the system recovers the previous valid full checkpoint, rewinds `HEAD`, the manifest and the journal suffix to the same causal point, and from there can open a new durable continuation.

Observatory applies the **unknown > invented** rule: when the runtime does not expose a factual metric, the projection uses `null` / `not available`, never a plausible default value.

# 1. Objective

The next stage of Symbiont World does not consist in adding more mechanics.

The objective is to convert the current prototype into an **intact, durable, reconstructible and scientifically observable digital world**.

It must be possible to:

```text
create Genesis
     ↓
introduce Symbionts
     ↓
execute millions of ticks
     ↓
close the process
     ↓
restart machine/process
     ↓
recover exactly the same world
     ↓
continue from the next tick
```

Meanwhile, a human must be able to observe:

```text
World Reality
    ↓
ecology
    ↓
organisms
    ↓
physiology
    ↓
perception
    ↓
cognition
    ↓
causal history
```

without having any mechanism capable of modifying the experiment.

The sought result is a **permanent digital scientific terrarium**.

---

# 2. Starting point

The current implementation already contains a significant amount of valid infrastructure:

```text
symbiont_world
├── WorldConstitution
├── WorldObservation / WorldAction
├── HexTopology
├── OccupancyGrid
├── WorldBody
├── WorldState
├── TickTransaction
├── WorldEvent / EventJournal
├── fields
├── resources
├── hazards
├── regional GroundTruth
└── deterministic RNG

symbiont_lab.world
├── Genesis presets
├── SingleOrganismGenesisRuntime
├── PopulationGenesisRuntime
├── deferred damage
├── founder placement
├── W01/W02/W03 experiments
├── dashboard server
├── read-only API
└── SVG world view
```

There is also a server that continuously executes the world independently of the browser.

The problem is no longer "making the world exist".

The problem is ensuring that:

```text
what happens
=
what is saved
=
what is reproduced
=
what Observatory represents
```

---

# 3. Constitutional principles

Any subsequent implementation must preserve five separations.

```text
WORLD
causal reality

ORGANISM
experience and action

LAB
experimental orchestration

JOURNAL
confirmed history

OBSERVATORY
passive projection
```

The dependencies remain:

```text
symbiont_world
      ↑
symbiont_lab
      ↓
   symbiont
```

Never:

```text
symbiont → symbiont_world
```

and never:

```text
Observatory → World
```

Observatory can know ground truth.

The organism cannot.

---

# 4. Top priority: true atomic tick

The current atomicity is incomplete.

`TickTransaction` primarily protects:

```text
WorldState
├── occupancy
└── bodies
```

but during a tick the following can also be modified:

```text
WorldEnvironment
resource pools
field state

SharedHabitat
resource allocations

ModeledOrganismRuntime
cognition
memory
physiology
homeostasis
metabolism

DeferredEffectQueue

pending journal events
```

Therefore we need to replace the current concept with an integrated transaction.

## 4.1 IntegratedWorldTickTransaction

Conceptually:

```text
BEGIN TICK N
    │
    ├── snapshot WorldState
    ├── snapshot WorldEnvironment
    ├── snapshot every organism
    ├── snapshot SharedHabitat surfaces
    ├── snapshot deferred effects
    ├── stage events
    │
    ▼
execute tick
    │
    ├── success ──────────────► COMMIT
    │
    └── failure ──────────────► ROLLBACK
```

COMMIT means:

```text
world state accepted
organism states accepted
resource states accepted
deferred queue accepted
events appended
tick += 1
```

ROLLBACK means:

```text
no tick advance
no resource consumption
no physiology change
no cognition change
no damage
no deferred-effect removal
no journal event
```

The property that must be proven is:

```text
failed_tick(state_n) == state_n
```

byte-equivalent where the contract allows binary equivalence, or semantic-equivalent where non-causal external timestamps exist.

---

# 5. Commit ordering

The tick model should evolve to four major phases.

```text
WORLD PHASE
1 scheduled environment processes
2 field propagation
3 resource regeneration/decay
4 observation surfaces

ORGANISM PHASE
5 sensing
6 cognition
7 action intent generation

RESOLUTION PHASE
8 resolve simultaneous movement/intents
9 resolve resource acquisition
10 resolve contact
11 resolve communication
12 apply physiological consequences
13 lifecycle transitions
14 culture/social delivery

COMMIT PHASE
15 construct committed WorldEvents
16 journal append
17 advance tick
18 durable checkpoint when required
```

Nothing should reach the journal before it is known that the entire tick is going to be confirmed.

---

# 6. Complete persistence of the universe

The current `WorldCheckpoint` is insufficient for a perennial world.

We need a new artifact:

```text
PersistentWorldCheckpoint
```

that represents a complete recoverable universe.

## 6.1 Content

Conceptually:

```text
PersistentWorldCheckpoint
├── schema_version
├── world_id
├── world_fingerprint
├── world_seed
├── epoch
├── tick
│
├── topology
├── occupancy
├── WorldBody[]
│
├── environment
│   ├── field values
│   ├── resource pools
│   └── environmental state
│
├── organisms
│   ├── organism_id
│   ├── organism checkpoint
│   ├── resource habitats
│   └── adapter-owned state
│
├── deferred_effects
├── RNG stream states
├── last_event_id
└── journal integrity metadata
```

It must include everything whose state could change the future.

---

# 7. Persistence rule

The world is not considered truly persistent until it passes this test:

```text
Run A
tick 0 → tick 50,000
checkpoint
continue → tick 60,000

Run B
tick 0 → tick 50,000
checkpoint
kill process
restore
continue → tick 60,000
```

And then:

```text
future(A) == future(B)
```

for:

```text
world
organisms
resources
hazards
actions
birth/death
events
RNG
```

This must become a mandatory technical gate.

---

# 8. Physical persistence

The checkpoint cannot live only in memory.

Proposal:

```text
~/.local/state/symbiont/worlds/<world_id>/
├── manifest.json
├── constitution.json
├── checkpoints/
│   ├── 000000001024.chk
│   ├── 000000002048.chk
│   └── ...
├── events/
│   ├── segment-000001.jsonl
│   └── ...
└── HEAD
```

`HEAD` points to the last confirmed state.

Writing:

```text
write temporary checkpoint
fsync
validate checksum
atomic rename
update HEAD
```

Never overwrite the last known good checkpoint directly.

---

# 9. Real event sourcing

`EventJournal` must stop being just an available structure and become the official history of the world.

The journal only contains **confirmed** events.

Examples:

```text
WORLD_FIELD_CHANGED
RESOURCE_RENEWED
RESOURCE_ACQUIRED
ORGANISM_MOVED
ORGANISM_CONTACT
ORGANISM_EMITTED
HAZARD_EXPOSURE
PHYSIOLOGICAL_DAMAGE
REPAIR
BIRTH
DEATH
GENOME_MUTATION
CULTURAL_TRANSMISSION
```

Each one maintains:

```text
event_id
world_id
tick
kind
actor
position
payload
causal_parent_ids
contributing_event_ids
```

---

# 10. Causality

The following distinction is strictly preserved:

```text
causal_parent_ids
```

= mechanical transition known by construction.

Example:

```text
RESOURCE_ACQUIRED
        ↓
METABOLIC_RESERVE_CHANGED
```

while:

```text
contributing_event_ids
```

= relevant but not sufficient antecedents.

Example:

```text
resource history
damage history
age
reserve
       ↓
REPRODUCTION_READY
```

Observatory must represent both in a visually distinct way.

---

# 11. WorldEpoch

`WorldEpoch` is maintained as an evaluator-side concept.

An epoch does not change the world.

It only provides durable navigation:

```text
Genesis
├── epoch 0
├── epoch 1
├── epoch 2
└── ...
```

Its internal representation:

```text
epoch
start_tick
trigger_event_id
label
```

The labels:

```text
first birth
first extinction
```

are human.

The durable identity remains:

```text
epoch=3
start_tick=182731
trigger_event_id=evt...
```

---

# 12. Canonical Genesis vs test worlds

The current ambiguity must be corrected.

If `WorldConstitution` says:

```text
64 × 64
```

a run:

```text
8 × 8
```

is not the same constitutional universe.

I propose formally distinguishing:

```text
Genesis-v1
64×64
canonical world

Genesis-Smoke-v1
8×8
fast tests

Genesis-Experimental-*
scientific variants
```

Each receives its own:

```text
WorldConstitution
world_fingerprint
```

Never reuse the Genesis fingerprint for a different geometry.

---

# 13. State of W03

The current results are not deleted.

They are reclassified.

W03 must remain as:

```text
EXPLORATORY
OBSERVED
NEEDS_REPLICATION
```

because W01 did not reject H0 and the original barrier required individual adaptation before interpreting emergent ecology.

Furthermore:

```text
first proposed causal mechanism
        ↓
hazard density coupling
        ↓
FALSIFIED by control
```

and currently remains as a candidate:

```text
different occupancy percept
→ different percept stream
→ different deterministic trajectory
```

Before turning W03 into a confirmed result it will be necessary to perform:

```text
occupancy-percept ablation
+
multiple seeds
+
larger population
+
replication
```

---

# 14. Observatory: objective

Observatory must not be a videogame.

It must allow a human to quickly understand:

```text
what exists
what is changing
which individual is deteriorating
which resource is depleting
what event just happened
what the organism perceives
what the organism believes
```

without touching the world.

---

# 15. Observatory architecture

```text
World Runtime
      │
      ├── current committed state
      └── EventJournal
             │
             ▼
      Projection Layer
             │
             ▼
       Read-only API
             │
             ▼
        Observatory UI
```

The browser never talks to:

```text
WorldAction
WorldKernel
PopulationRuntime.run_tick()
```

There are no endpoints:

```text
POST
PUT
PATCH
DELETE
```

about the world.

---

# 16. Visual map model

Each hexagon must exist permanently in the DOM.

The visual map is divided into:

```text
BASE
region / terrain

OVERLAY
resources / hazards / fields

FOREGROUND
organisms / recent events
```

---

# 17. Geography

Currently empty cells look identical.

That must disappear.

Every cell must represent:

```text
CellView
├── q,r
├── region_id
├── resources
├── hazards
├── fields
├── occupant
└── recent event markers
```

The region determines the base background.

Names like:

```text
north
south
rich biome
```

are evaluator-side metadata.

They never reach the organism.

---

# 18. Overlays

The user can select a visual layer, without changing the world.

```text
REGION
RESOURCE
HAZARD
FIELD
POPULATION
```

## Resource overlay

It can represent:

```text
quantity / capacity
```

as intensity/opacity.

## Hazard overlay

It must show **real exposure** using the same factual local density that the runtime projects. The v3 hardening removed the old fallback `local_density=0.0` from both the structured view and the textual render.

It must be calculated with the same local density used by the runtime.

## Field overlay

It allows visualizing:

```text
field.01
field.02
...
```

using human labels only in Observatory.

---

# 19. Visual organism

The organism must not be the hexagon.

It must be an independent glyph placed on top of the terrain.

```text
terrain hex
     +
 organism
```

This later allows:

```text
movement interpolation
health rings
action pulses
selection
death markers
```

without confusing place and inhabitant.

---

# 20. Vitality

The organism shows factual data.

Do not start with interpretive categories like:

```text
hungry
happy
sick
```

but:

```text
vital_state
integrity
metabolic reserve
metabolic pressure
age
generation
```

Visually:

```text
outer ring      integrity
inner fill      reserve
opacity         alive/dead
border pattern  vital state
```

---

# 21. Actions and recent events

Visual effects are Observatory's interpretation of objective facts.

Example:

```text
resource acquired
→ acquisition pulse

repair amount > 0
→ repair pulse

damage > 0
→ damage ring

death event
→ death marker
```

A label like:

```text
organism_is_suffering
```

is not transmitted to the frontend.

but actual quantities and events.

---

# 22. Death

Upon dying:

```text
organism
→ removed from live occupancy
```

Observatory can temporarily maintain:

```text
recent_death_marker
```

but this is a historical annotation.

It does not constitute a physical corpse unless in a future version the world explicitly models residual matter.

---

# 23. Inspector

Clicking on a cell or organism opens a side panel.

## Organism

```text
IDENTITY
organism_id
generation
age

PHYSIOLOGY
vital_state
integrity
metabolic reserve
pressure

BEHAVIOR
last action
recent action history

WORLD EFFECTS
recent acquisition
damage
repair
hazard exposures

PERCEPTION
signals actually received

COGNITION
concept count
prediction data
confidence
self model
```

---

# 24. Four epistemological perspectives

The inspector must explicitly separate:

```text
WORLD
PHENOTYPE
PERCEPTION
SELF
```

## World

What actually exists.

## Phenotype

What the organism actually is and does.

## Perception

What it effectively receives through its sensors.

## Self

What it internally represents about itself or its environment.

They must never be mixed.

---

# 25. Reality / Perception / Self

The most important visual element might be a toggle:

```text
[ Reality ] [ Perception ] [ Self ]
```

Example:

```text
REALITY

resource.71 = 8.2
hazard.03 = .41


PERCEPTION

signal.a81 = .63
signal.d91 = .17


SELF

concept.18
expected consequence = favorable
confidence = .44
```

That allows observing the birth of understanding.

---

# 26. Cell inspector

It must show:

```text
CELL q=12,r=7

region
occupant

resources
current quantity
capacity
renewal law summary

hazards
actual local exposure

fields
current values

recent events
```

All this information belongs to the scientific apparatus.

---

# 27. Timeline

The simulation needs a visible historical dimension.

We will keep bounded evaluator-side buffers:

```text
population_history
mean_integrity_history
mean_reserve_history
resource_acquisition_history
hazard_hits_history
birth_history
death_history
```

For example:

```text
2048 samples
```

with downsampling when necessary.

---

# 28. Initial charts

The first four:

```text
alive organisms
mean integrity
mean metabolic reserve
resource acquisition rate
```

Then:

```text
births
deaths
hazard hits
behavior distribution
```

Native canvas is sufficient.

We do not need a charting dependency.

---

# 29. Causal feed

Once `EventJournal` is connected, Observatory shows confirmed events:

```text
tick 19342
RESOURCE_ACQUIRED

tick 19342
METABOLIC_RESERVE_CHANGED
caused by evt.9123

tick 19343
HAZARD_EXPOSURE

tick 19343
PHYSIOLOGICAL_DAMAGE
caused by evt.9131
```

The UI must differentiate:

```text
mechanical cause
```

from:

```text
contributing antecedent
```

via iconography or different lines.

Never infer events from observed differences.

---

# 30. Flicker-free render

Remove:

```javascript
svg.innerHTML = ''
```

The SVG must be built once.

Keep:

```javascript
cellNodes = Map
organismNodes = Map
```

For each update:

```text
update attributes
update classes
update transforms
update labels
```

Do not reconstruct DOM.

---

# 31. Animation

With persistent nodes:

```css
transition:
    fill .45s,
    opacity .45s,
    stroke .2s,
    transform .45s;
```

When movement exists:

```text
cell A → cell B
```

the organism glyph can move smoothly.

---

# 32. Frontend technology

Do not introduce React/Vue yet.

The current stack can be maintained:

```text
stdlib HTTP
vanilla JavaScript
SVG map
Canvas charts
CSS transitions
```

But `dashboard_page.py` should not continue accumulating the entire application in an HTML string.

Separate conceptually:

```text
dashboard/
├── page.py
├── world.js
├── renderer.js
├── inspector.js
├── timeline.js
├── api.js
└── styles.css
```

---

# 33. API

The current payload must evolve into an explicit structure.

```json
{
  "world": {},
  "fields": {},
  "cells": {},
  "organisms": {},
  "history": {},
  "events": []
}
```

Organism example:

```json
{
  "id": "founder-3",
  "q": 12,
  "r": 7,
  "alive": true,
  "vital_state": "active",
  "integrity": 0.81,
  "metabolic_reserve": 0.54,
  "last_action": "intake:...",
  "recent_damage": 0.05
}
```

The more interpretive evaluator-side data must be kept separate.

---

# 34. Incremental events

Polling can be maintained.

We do not need WebSocket yet.

For example:

```text
GET /api/state
GET /api/events?after=<event_id>
```

This way polling every second does not lose events even if the world advances several ticks.

---

# 35. Semantic zoom

Navigation must follow:

```text
WORLD
 ↓
REGION
 ↓
CELL
 ↓
ORGANISM
 ↓
MIND
```

It is not just geometric zoom.

Each scale changes what information is presented.

World:

```text
ecology
```

Region:

```text
local pressures
```

Cell:

```text
ground truth
```

Organism:

```text
physiology and behavior
```

Mind:

```text
perception, concepts and prediction
```

---

# 36. Natural history and experimental science

Persistent worlds and experiments must remain separate.

```text
CANONICAL WORLD
lives continuously

EXPERIMENTAL CLONE
starts from a checkpoint
```

For example:

```text
Genesis
tick 2,184,993
```

can be cloned into:

```text
Experiment A
original

Experiment B
communication disabled

Experiment C
resource X removed
```

without altering Genesis.

---

# 37. Recovery semantics

Upon restarting the server:

```text
load HEAD
validate constitution fingerprint
validate journal/checkpoint continuity
restore world
restore population
resume at N+1
```

If the last checkpoint is corrupt:

```text
fallback previous checkpoint
+
replay committed events
```

Never invent state.

---

# 38. Dashboard and persistence are the same project

They must not evolve separately.

The dashboard only consumes:

```text
committed world state
+
committed journal
```

Therefore:

```text
UI never sees provisional state
```

This is important.

If a tick fails, the browser must not observe a universe that subsequently disappears due to rollback.

---

# 39. Implementation plan

## Phase P0 — World Integrity

Resolve:

```text
IntegratedWorldTickTransaction
WorldEnvironment rollback
organism rollback
SharedHabitat rollback
DeferredEffectQueue rollback
pending-event staging
```

Gate:

```text
forced failure at every phase
→ exact state restoration
```

---

## Phase P1 — Durable World

Implement:

```text
PersistentWorldCheckpoint
disk storage
atomic checkpoint writes
HEAD
startup restore
checkpoint/replay equivalence
```

Primary gate:

```text
continuous run
==
kill + restore + continue
```

---

## Phase P2 — Journal Integration

Connect real events:

```text
resource
damage
repair
death
birth
movement
communication
```

Events are published only after COMMIT.

---

## Phase P3 — Observatory 0.2

Implement:

```text
persistent SVG DOM
region map
organism glyphs
vitality
actual hazard exposure
cell selection
organism selection
inspector
last action
damage markers
```

---

## Phase P4 — Observatory 0.3

Add:

```text
resource overlays
hazard heatmap
field overlays
transitions
legend
semantic zoom
```

---

## Phase P5 — Observatory 0.4

Once journal exists:

```text
event feed
causal provenance
population timeline
resource timeline
birth/death timeline
historical annotations
```

---

## Phase P6 — Observatory 0.5

Finally:

```text
Reality
Perception
Self

sensor inspector
concept inspector
prediction inspector
self-model inspector
```

---

# 40. What NOT to add yet

Until P0–P2 is closed, I would not open new substantial capabilities:

```text
MOVE as new cognitive capability
spatial reproduction
culture-in-world
communication range
evolutionary expansion
complex niche construction
```

Not because they are bad ideas.

Because they would increase the causal space before we can guarantee:

```text
rollback
recovery
history
replay
```

---

# 41. What we do with current experiments

Do not delete anything.

Reclassify:

```text
W01
valid null result

W02
valid methodological null result

W03
exploratory observation
needs replication
not formal ecological gate
```

The runs already performed are useful development evidence.

But the next scientific program must start from a world whose identity, persistence and causality are closed.

---

# 42. Condition to call the world "perennial"

It is not enough that the process has been running for several days.

The definition should be:

> A Symbiont World is perennial when its causal continuity does not depend on the continuity of the process executing it.

That is:

```text
process lifetime
≠
world lifetime
```

That is the important frontier.

---

# 43. Final objective state

We want to be able to do this:

```text
$ symbiont-world serve Genesis
```

and get:

```text
Loading Genesis...

world_id        genesis
fingerprint     91ab...
epoch           27
tick            18,392,188
population      43
last checkpoint 18,391,808
journal         valid

Resuming world.
Observatory:
http://127.0.0.1:8766
```

While the browser shows:

```text
WORLD
──────────────
map
regions
resources
hazards
population

TIMELINE
──────────────
population
integrity
resources

EVENTS
──────────────
birth
damage
acquisition
death

INSPECTOR
──────────────
Reality
Phenotype
Perception
Self
```

The user can close the browser.

Nothing changes.

Can kill the server.

The world is saved.

Can start it a week later.

Continues from the last confirmed state.

---

# 44. Success criterion

This stage will be finished when we can simultaneously affirm:

```text
1. The world does not lose causality in the event of a tick failure.

2. The world survives a process restart.

3. Its future is reproducible from checkpoint + journal.

4. Observatory only shows confirmed states.

5. Observatory does not have any control channel.

6. A human can visually understand the ecology.

7. Can distinguish World / Phenotype / Perception / Self.

8. The world's history can be causally reconstructed.

9. Canonical Genesis has an unequivocal constitutional identity.

10. We can let Symbionts live without depending on a human watching.
```

---

# 45. Conceptual result

So far we have gone through:

```text
Symbiont
"we have an organism"

        ↓

Symbiont World
"we have an environment to put it in"

        ↓

Persistent Symbiont World
"we have a place where it can live"

        ↓

Scientific Observatory
"we can observe what happens without intervening"
```

This should be the priority before expanding digital biology even further.

The project's next big leap does not consist in giving Symbionts a new capability.

It consists in achieving that **the life they can already develop has a continuous world, a real history and a scientific instrument capable of making it visible to us**.
