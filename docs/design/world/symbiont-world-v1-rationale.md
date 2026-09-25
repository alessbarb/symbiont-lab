---
id: design.world.symbiont-world-v1-rationale
title: "Symbiont World V1 Rationale"
document_type: design
domain: world
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
Yes. I have crossed the idea with the current state of your repository and with background in Artificial Life, digital evolution, multi-agent worlds, and open-ended evolution. The conclusion is quite clear:

> **We do not need to invent "another simulator". We need to build the permanent natural habitat for the Symbiont.**

And besides, the timing is good because the organism already has almost all the components that were missing before: physiology, death, reproduction, heredity, culture, opaque communication, basic ecology, adaptive sensors, and an IntegratedHabitatRuntime. What is missing is providing them with **space, environmental causality, and real ecological continuity**.

## 1. What previous experiments teach us

Tierra and Avida demonstrate that genuine digital evolution can exist when there is replication, heritable variation, and competition, without the need to assign an explicit human score to each individual. Avida, furthermore, turned this into a controllable and measurable experimental platform. ([MIT Press Direct][1])

Polyworld added something fundamental for us: spatially situated organisms, perception, movement, resources, reproduction, and lifelong learning through neural networks. It is probably the closest conceptual ancestor to what we want. ([PubMed Central (PMC)][2])

Neural MMO showed the importance of persistent worlds, many simultaneous individuals, distributed resources, and niche formation. But it continues to be mainly a reinforcement learning environment designed around observations, actions, and reward. ([OpenAI][3])

Melting Pot demonstrates that the **social environment** must also be considered part of the problem: cooperation, competition, reciprocity, or trust can emerge depending on how individuals affect each other. Its goal, however, is evaluation of already trained agents, not autonomous evolution of organisms. ([Google DeepMind][4])

POET brings a different lesson: the diversity of environments can generate stepping stones that a single trajectory would not discover. But I **would not yet allow the world itself to evolve its laws**, because organism and environment changing simultaneously would destroy our ability to attribute causality. ([arXiv][5])

Recent research on open-ended evolution also insists on something we must take very seriously: **just because something runs indefinitely does not mean it is open-ended**. We must measure adaptive innovation, diversity, complexity, niche formation, and phylogenetic structure. ([MIT Press Direct][6])

And recent works continue to find that **space, ecology, and ecological_pressure leave distinct signals in phylogenies**. That reinforces that the geometry of the world should not be merely decorative. ([MIT Press Direct][7])

Culture also deserves to be treated as an evolutionary process distinct from the genetic one. The recent literature on open-ended cultural evolution fits especially well with the line that Symbiont already has of cultural provenance, composition, and transmission between organisms. ([MIT Press Direct][8])

---

# 2. What we already have

Here is the interesting part. Reviewing `main`, **Symbiont World would not start from scratch**.

The `README.md` current already declares as implemented:

```text
digital physiology
reproduction + heredity
bounded digital ecology
social development
Private SLM
culture
opaque symbol grounding
structured communication
Integrated Habitat Runtime
Passive Observatory
```

And `research/STATUS.md` confirms something even more important: `IntegratedHabitatRuntime` already managed to integrate population, physiology, learning, Private SLM, culture, grounding, communication, checkpoint/replay and telemetry within the same habitat.

Furthermore we have:

```text
src/symbiont/core/social/ecology.py
    SharedHabitat

src/symbiont/core/lineage/heredity.py
    HeritableGenome

src/symbiont/core/lineage/inheritance.py
    genética
    epigenética
    cultura

src/symbiont/core/social/interactions.py
    EcologicalResourcePool
```

And now the new sensory system already correctly differentiates:

```text
WORLD
 ↓
ObservableSource
 ↓
RawSample
 ↓
Sensor
 ↓
Percept
 ↓
SENSE
 ↓
CognitiveGraph
```

That is exactly the boundary we need for an artificial world.

The world can know:

```text
resource.type = 17
position = (43, 91)
toxicity = .61
energy = 8.4
```

while the organism receives only something equivalent to:

```text
signal.4ab1
signal.981c
signal.a20f
```

through its sensors.

That decoupling is extraordinarily important.

---

# 3. My proposal: `Symbiont World`

I would define it like this:

> **Symbiont World is a spatial, persistent, causal, finite, and non-semantic digital environment from the perspective of its inhabitants, capable of indefinitely maintaining an ecology of Symbionts and producing a complete reproducible record of its history.**

It is not a game.

It has no missions.

It has no score.

It has no explicit fitness.

It has no NPCs designed to teach them things.

It has no rewards.

The only existing "reward" consists of **the physical consequences that actions produce on the organism**.

---

# 4. Architecture

I would separate it into four strict domains:

```text
┌────────────────────────────────────────────┐
│              SYMBIONT WORLD                │
│                                            │
│  espacio · tiempo · campos · recursos      │
│  causalidad · clima · objetos · ecología   │
└──────────────────┬─────────────────────────┘
                   │
             interacción física
                   │
                   ▼
┌────────────────────────────────────────────┐
│                 SYMBIONT                   │
│                                            │
│ sensores · cuerpo · cognición · memoria    │
│ fisiología · cultura · comunicación        │
└──────────────────┬─────────────────────────┘
                   │
              evidence only
                   ▼
┌────────────────────────────────────────────┐
│               WORLD JOURNAL                │
│                                            │
│ event log · checkpoints · genealogy        │
│ observer truth · replay                    │
└──────────────────┬─────────────────────────┘
                   │
                  READ
                   ▼
┌────────────────────────────────────────────┐
│               OBSERVATORY                  │
│                                            │
│ World · Phenotype · Self · Mind · History  │
└────────────────────────────────────────────┘
```

The most important property would be:

```text
Observatory → World
```

**does not exist.**

Not even as a disabled API.

---

# 5. Space: would start discrete, not continuous

Although visually we can show something organic, for v1 I would choose a **discrete 2D** geometry.

Specifically:

> **finite hexagonal mesh.**

Each cell has six neighbors.

Why hexagonal?

Because it avoids part of the anisotropy of a grid:

```text
cuadrícula
  ↑
← ● →
  ↓

hexagonal

  ↖ ↑ ↗
   \|/
  ← ● →
   /|\
  ↙ ↓ ↘
```

and remains deterministic, cheap and extremely easy to save/reproduce.

Example:

```text
World 256 × 256 hex cells
≈ 65.000 posiciones
```

Not all organisms can observe the whole world.

Each occupies:

```text
position = cell_id
orientation = 0..5
```

but **the organism should not necessarily receive these explicit concepts**.

---

# 6. The world would have fields, not semantic "things"

This point seems central to me.

I would not initially fill the world with:

```text
árbol
agua
montaña
comida
veneno
```

That introduces too much human ontology.

I would build it from **fields and resources**.

For example:

```text
field.01
field.02
field.03
field.04
```

We know they represent something like:

```text
temperature
radiation
humidity
medium resistance
```

but the Symbiont does not.

A cell could have:

```text
cell.001728

field.01 = 0.42
field.02 = 0.13
field.03 = 0.88

resource.01 = 2.31
resource.07 = 0.00

hazard.03 = 0.21
```

And these values evolve through their own physical rules.

---

# 7. We need real causality

Environmental noise is not enough.

The world needs **discoverable regularities**.

Example:

```text
field.A ↑
   ↓ después de ~20 ticks
resource.B ↑

field.C + alta exposición
   ↓
sensor health ↓

resource.D intake
   ↓
metabolic reserve ↑

resource.E intake
   ↓
integrity ↓
```

None of these relationships is revealed.

A Symbiont should be able to discover:

```text
A predice B

D suele preceder recuperación

E parece perjudicarme
```

without knowing:

```text
temperatura
alimento
toxina
```

This is where grounding really begins.

---

# 8. Resources

The current `SharedHabitat` already has:

```text
resources
renewal_rate
acquisition_cost
physiological_usefulness
information_content
```

I would keep that conceptual model, but I would spatialize it.

We would go from:

```text
SharedHabitat
     │
resource pool
```

to:

```text
World
 │
 ├── region A
 │     ├ resource.01
 │     └ resource.02
 │
 ├── region B
 │     └ resource.03
 │
 └── region C
       ├ resource.01
       └ resource.04
```

Each resource would have real properties:

```text
quantity
renewal
diffusion
decay
mobility
acquisition cost
physiological effect
information signature
```

And, very importantly:

### `food` would not exist

There would exist:

```text
resource.72ac
```

that coincidentally causes:

```text
+reserve
```

when being metabolized.

---

# 9. Not every resource should be good

This is necessary so that significant learning can appear.

For example:

```text
R1 → +reserva, barato
R2 → +reserva, muy caro
R3 → +reserva ahora, daño lento después
R4 → neutro
R5 → ligeramente tóxico
R6 → útil sólo combinado con R2
```

Thus real inference problems appear.

Especially interesting:

```text
R3
 ↓
beneficio inmediato
 ↓
daño retardado
```

A purely reactive organism will prefer R3.

One capable of learning temporal dependencies might stop doing so.

That would be a wonderful test for the current predictive system.

---

# 10. Cycles

We need environmental temporality:

```text
día / noche
estaciones
ciclos lentos
pulsos
eventos irregulares
```

But never call them that in the organism.

Something could follow:

$$
F(t)=a+b\sin(\omega t+\phi)
$$

Another process:

```text
resource spawning
  condicionada por field.3
```

Another:

```text
hazard burst
p ≈ .001 por tick
```

And another could be almost stable.

Then we can discover if a Symbiont distinguishes:

```text
ruido
periodicidad
tendencia
causalidad
evento
```

---

# 11. Movement

The first motor repertoire should be extremely small.

For example six directional channels + rest:

```text
actuator.01
actuator.02
actuator.03
actuator.04
actuator.05
actuator.06
actuator.07
```

Observatory knows:

```text
01 = forward-left
02 = forward
...
07 = stay
```

but that semantics **does not enter cognition**.

Moving costs resources.

And different surfaces can alter that cost.

Thus the organisms could end up developing behaviors similar to:

```text
rutas
territorialidad
migración
forrajeo
refugio
```

without those concepts being encoded.

---

# 12. Perception

Here the new sensory work fits like a glove.

The world would offer local `ObservableSource`s.

Example:

```text
field local
resource density local
gradient
contact
nearby organism emissions
internal state
```

But an organism does not necessarily receive all of them.

The pipeline remains:

```text
world field
   ↓
ObservableSource
   ↓
signal.x
   ↓
Sensor
   ↓
Percept
   ↓
Cognition
```

And thanks to the new sensory architecture two Symbionts could look at **exactly the same world** with different perceptual apparatuses.

This opens up a beautiful scientific question:

> Do two organisms that inhabit exactly the same universe end up building different subjective worlds?

---

# 13. Important: I would not implement "vision"

Not yet.

The current architecture continues to work fundamentally with scalar signals and bounded modalities. `research/STATUS.md` acknowledges it explicitly: vector geometry and truly emergent sensory modalities remain open.

That is why I would not make the mistake of immediately putting in:

```text
camera image → pixels → vision
```

First:

```text
local scalar fields
gradients
contact
short temporal patterns
multi-source relationships
```

When `ReceptorProgram` and vector geometry emerge, then we can incorporate spatially much richer modalities.

---

# 14. Action and intervention

Neither would I give actions like:

```text
eat()
attack()
mate()
trade()
```

Polyworld does do this because it researches something else. ([PubMed Central (PMC)][2])

For Symbiont I would try to use **more primitive physical operations**.

For example:

```text
move
sample
acquire
release
emit
contact
rest
```

The emergent meaning of these combinations could end up being:

```text
forrajear
huir
seguir
proteger
intercambiar
señalizar
cooperar
```

but those are our labels.

---

# 15. Interaction between Symbionts

Individuals are also part of the world.

A nearby organism produces:

```text
presence field
motion perturbation
resource competition
opaque emissions
contact effects
```

It should not magically appear:

```text
entity.type = symbiont
```

in cognition.

The organism would have to discover that certain environmental sources:

* move,
* respond,
* consume,
* produce messages,
* have different regularities than passive objects.

With enough development we could test:

> **does it discover the category "other agent"?**

That would be much more interesting than providing it.

---

# 16. Communication

Here we already have a huge advantage.

The current repo has opaque structured communication:

```text
opaque symbols
variable-length sequences
silence
cost
grounding
```

In Symbiont World communication should become **spatial**.

An emission could have:

```text
range
attenuation
duration
cost
channel
```

Example:

```text
Symbiont A
   ↓ sequence.912
   ))))))))

B recibe 0.82
C recibe 0.31
D no recibe
```

That radically changes the ecology of communication.

There could appear:

```text
proximidad
agrupamiento
territorialidad
señalización local
dialectos
```

without introducing a global social network.

---

# 17. No global broadcast

This seems essential to me.

If everyone can talk instantaneously to everyone:

```text
population → global chat
```

we destroy almost all the importance of space.

It must be:

```text
locality
+
range
+
cost
+
noise
```

The social topology must largely emerge from **who can physically encounter whom**.

---

# 18. Physiology

The world has to directly feed the existing physiology.

Currently Symbiont already models:

```text
intake
assimilation
maintenance
activity
learning
memory
degradation
dormancy
death
```

Therefore World should not create another HP or energy system.

It should supply **inputs to the existing metabolism**.

Example:

```text
World resource
      ↓
acquisition
      ↓
existing MetabolicLedger
      ↓
reserve
      ↓
learning / maintenance / movement
```

This avoids duplicating concepts.

---

# 19. Death

Death must become a real ecological event.

Currently it is already irreversible.

In World:

```text
Symbiont dies
   ↓
position becomes free
   ↓
resources allocated to it released
   ↓
possibly local environmental residue
   ↓
lineage remains in history
```

I would even add an option later:

```text
dead biomass → reusable resources
```

but **not in v1**, because it adds another unnecessary causal layer.

---

# 20. Reproduction

The current architecture uses `habitat-authorized birth`.

I would keep it.

The Symbiont can be:

```text
READY
```

but World decides if physically there is:

```text
space
resources
capacity
```

to materialize the offspring.

That does not mean artificial selection.

The world only applies its laws.

The offspring appears near the parent:

```text
parent cell
   ↓
available neighboring cell
   ↓
offspring
```

I would not teleport it randomly.

Thus the genealogy also acquires **geographical structure**.

---

# 21. Heredity

I would keep exactly the distinction that already exists:

```text
GENÉTICA
    ↓
capacity / parameters

EPIGENÉTICA
    ↓
bounded priors

CULTURA
    ↓
post-birth social transmission

FENOTIPO APRENDIDO
    ✕ no germinal
```

This is scientifically very clean.

And it opens fantastic experiments:

```text
genética solamente
vs
genética + epigenética
vs
genética + cultura
```

---

# 22. Permanent world

Here your original idea appears.

The world would have a:

```text
world_id
```

that survives the individuals.

For example:

```text
world.0001
created: 2026-10-01

tick 0
...
tick 18,726,291
...
```

The individuals are born and die inside.

```text
World 1
│
├─ Generation 0
│   ├ A
│   ├ B
│   └ C
│
├─ Generation 1
│   ├ A.1
│   ├ B.1
│   └ B.2
│
├─ ...
│
└─ Generation 184
```

The world does not reset because an organism dies.

---

# 23. Time

I would separate three concepts:

```text
wall time
simulation time
biological ticks
```

The world can run:

```text
1×
10×
100×
máxima velocidad
```

without changing its causality.

This is fundamental for research.

A "one year" experiment should not necessarily need a human year.

---

# 24. Determinism

Every run would have:

```text
world seed
```
world config fingerprint
kernel version
initial founders
```

Therefore:

```text
same state
+ same events
+ same RNG state
=
same future
```

This is essential to be able to repeat interesting stories.

If we see:

> "In generation 47 a strange behavior appears."

we must be able to go back to the previous tick and reproduce it exactly.

---

# 25. Event sourcing

I would make **World event-sourced from day one**.

Not depend only on snapshots.

Example:

```text
tick 8712991

WORLD_FIELD_CHANGED
RESOURCE_RENEWED
ORGANISM_MOVED
RESOURCE_ACQUIRED
ORGANISM_EMITTED
ORGANISM_CONTACT
BIRTH
DEATH
GENOME_MUTATION
CULTURAL_TRANSMISSION
```

Each event would include:

```text
event_id
world_id
tick
actor
position
payload
causal_parent_ids
```

Snapshots are for performance.

The event log constitutes the history.

---

# 26. This is extremely important: causal provenance

I would explicitly add:

```text
causal_parent_ids
```

when possible.

For example:

```text
RESOURCE_ACQUIRED #7812
        ↓
METABOLIC_RESERVE_CHANGED #7813
        ↓
REPRODUCTION_READY #7820
        ↓
BIRTH #7901
```

Thus Observatory could reconstruct causal chains without "explaining" them to the organism.

---

# 27. Observatory would have six scales

I would evolve the current Observatory towards:

```text
WORLD
REGION
POPULATION
LINEAGE
INDIVIDUAL
MIND
```

### World

We would see:

```text
fields
resources
organism density
birth/death
migration
events
```

### Region

```text
resource history
population turnover
local lineages
communications
```

### Population

The view that already exists would be expanded:

```text
ecology
knowledge
activity
dissent
genealogy
culture
```

### Lineage

```text
genome mutations
births
extinctions
phenotypic divergence
```

### Individual

The functional anatomy that already exists.

### Mind

```text
signals
sensors
concepts
predictions
beliefs
self-model
private model
```

---

# 28. And I would keep four epistemological layers

Instead of just Reality / Phenotype / Self, I would formalize:

```text
1. WORLD TRUTH
   lo que existe

2. PHENOTYPE
   lo que el organismo hace/es

3. PERCEPT
   lo que recibe

4. SELF / MODEL
   lo que cree
```

This allows us to distinguish:

```text
resource realmente presente
        ↓
señal disponible
        ↓
sensor la detecta o no
        ↓
concepto aprendido
        ↓
predicción
        ↓
acción
```

The discrepancy between those layers is precisely the interesting scientific information.

---

# 29. World Truth never enters the Symbiont

This must be an automatically proven invariant:

```text
observer.*
world.semantic.*
ground_truth.*
```

cannot enter:

```text
Sensor
CognitiveGraph
Private SLM
Culture
Decision
```

I even propose integrity tests for taint/provenance.

Something like:

```text
assert no_ground_truth_reaches_organism()
```

in each data pipeline.

---

# 30. Regions and niches

The map should not be homogeneous.

I would design a few emergent causal regions from fields, not labels.

For example:

```text
        North
    high field A
    low resource X

West             East
resource Y       resource X
high hazard      periodic field B

        South
    stable conditions
    scarce resources
```

We visualize it as biomes.

For them only signal distributions exist.

This allows the appearance of:

```text
nichos
migraciones
especialización
```

Recent research in ALife backs precisely the importance of spatial structure + ecology for evolutionary dynamics. ([MIT Press Direct][7])

---

# 31. A small number of laws, lots of combinatorics

I would not create a hundred types of resources.

For World v1:

```text
4 campos ambientales
4 recursos
2 hazards
1 canal social
1 canal comunicativo
```

is enough.

Because we want to study:

> what emerges from the relationships,

not visually impress.

For example:

```text
Field A
Field B
Field C
Field D

Resource 1
Resource 2
Resource 3
Resource 4

Hazard 1
Hazard 2
```

With cross relationships hundreds of possible ecological states already appear.

---

# 32. I would explicitly avoid quests

Nothing like:

```text
collect 10 resources
reach location X
survive 100 ticks
communicate with B
```

That would turn the experiment into RL in disguise.

Our criterion must be:

```text
mundo produce consecuencias
organismo produce comportamiento
observador mide
```

Not:

```text
evaluador define éxito
 ↓
organismo optimiza éxito
```

---

# 33. I also would not give fitness

Especially:

```text
fitness = lifespan
```

would be dangerous.

Because we would immediately turn the entire dynamics into optimizing a number.

Real fitness is observed retrospectively:

```text
descendencia
persistencia del linaje
supervivencia
acceso a recursos
```

but is never provided as a signal.

This is very aligned with the principle of digital evolution based on selection resulting from reproduction and competition, not necessarily from an explicit evaluating function. ([MIT Press Direct][9])

---

# 34. A crucial distinction: persistence ≠ open-endedness

We can run:

```text
1.000.000.000 ticks
```

and get nothing interesting.

An equilibrium could appear:

```text
todos hacen A
todos comen B
todos se reproducen igual
```

That would not be open-ended evolution.

That is why we need to measure externally:

```text
phenotypic diversity
genotypic diversity
behavioral diversity
niche count
innovation rate
lineage turnover
phylogenetic depth
adaptive novelty
cultural novelty
complexity
```

The MODES metrics and the open-ended evolution literature are very pertinent here. ([MIT Press Direct][10])

---

# 35. What would be an "innovation"

It is not enough with:

```text
nuevo genome_id
```

An irrelevant mutation is not innovation.

I would distinguish:

```text
genotypic novelty
phenotypic novelty
behavioral novelty
ecological novelty
cognitive novelty
cultural novelty
```

For example:

> a lineage begins to exploit a resource that no ancestor exploited.

That is interesting.

Another:

> an acquisition strategy based on anticipating a cycle appears.

Another:

> a message reduces the receiver's search cost.

Another:

> a culturally transmitted behavior emerges that is not genetically fixed.

---

# 36. Emergent niche

I would not assign:

```text
species = forager
species = hunter
```

Observatory can subsequently infer clusters.

For example:

```text
Lineage 37

82% intake resource.3
habitat preference region.7
low movement
high communication
```

We could call it:

> "resource.3 specialist"

but never the organism.

---

# 37. Authentic natural selection within the system

If:

```text
Genotype A
→ aprende rápido
→ consume muchos recursos

Genotype B
→ aprende lento
→ mantenimiento barato
```
then according to the world:

```text
abundancia → A prospera
escasez → B prospera
```

The world does not decide who wins.

It simply applies:

```text
resource availability
+
cost
+
reproduction
+
death
```

That would be a convincing digital ecology.

---

# 38. Environmental changes

After stabilizing v1, I would introduce rare changes.

For example:

```text
Day 0–10000
regime A

Day 10001
gradual transition

Day 15000+
regime B
```

And we observe:

```text
plasticidad
migración
extinción
adaptación genética
adaptación cultural
```

Recent work on populations subjected to disruptive habitat changes shows precisely how fertile this kind of experiment is. ([MIT Press Direct][11])

---

# 39. Culture

Symbiont already has a foundation that many previous experiments do not possess.

That allows studying a brutal question:

```text
Gen 1 descubre X
        ↓
Gen 2 recibe X socialmente
        ↓
Gen 3 modifica X
        ↓
Gen 4 nunca ha observado el fenómeno original
pero conserva comportamiento útil
```

We can differentiate:

```text
evolución genética
ontogenia
evolución cultural
```

That directly connects with one of the contemporary frontiers of open-ended evolution. ([MIT Press Direct][8])

---

# 40. The world must be able to forget its inhabitants, but not its history

Operating state:

```text
living population
```

can be bounded.

History:

```text
append-only archive
```

can grow externally.

Thus Symbionts do not carry the entire world genealogy.

But we can reconstruct it.

---

# 41. Concrete software architecture

I would not create another repo immediately.

Given that right now `symbiont`, `symbiont_lab` and Observatory are integrated within `symbiont-lab`, I would start it as a new package:

```text
src/
  symbiont/
      ...
  symbiont_world/
      __init__.py
      kernel.py
      clock.py
      topology.py
      fields.py
      resources.py
      hazards.py
      occupancy.py
      actions.py
      perception.py
      ecology.py
      lifecycle.py
      events.py
      checkpoint.py

  symbiont_lab/
      ...
      world/
          runner.py
          experiments.py
          metrics.py
          replay.py
```

When it matures, we would decide if it deserves to become its own repository.

That avoids creating premature boundaries.

---

# 42. The boundary would be this

```text
symbiont_world
     │
     │ WorldObservation
     ▼
symbiont
     │
     │ WorldAction
     ▼
symbiont_world
```

Two contracts.

Nothing more.

For example:

```python
WorldObservation
```

contains only what is physically observable.

And:

```python
WorldAction
```

contains only allowed actions.

Without organism access to:

```text
World
Cell
Resource
Hazard
GroundTruth
```

---

# 43. World tick

I would define a strict deterministic order:

```text
1  world scheduled processes
2  field propagation
3  resource renewal/decay
4  organism local observation surfaces
5  sensor sampling
6  organism cognition
7  organism decisions
8  resolve movements
9  resolve resource competition
10 resolve contacts
11 resolve communications
12 physiological consequences
13 births
14 deaths
15 cultural deliveries
16 telemetry
17 journal commit
18 checkpoint if due
```

The order is critical.

It cannot depend on dictionary order or thread scheduling.

---

# 44. Simultaneous actions

If A and B want the same resource:

bad design:

```text
A ejecuta primero
A gana
```

because an accidental advantage by execution order would appear.

Correct:

```text
intent A
intent B

     ↓

resolver simultáneamente

     ↓

allocation rule
```

The rule can be:

```text
proportional
lottery deterministic with RNG
cost-dependent
```

but it must be declared and reproducible.

---

# 45. Parallelism without losing determinism

Later we can divide the map:

```text
region workers
```

but the ticks should work as barriers:

```text
compute intents
      ↓
synchronize
      ↓
resolve
      ↓
commit world
```

Thus we can scale thousands of Symbionts without introducing nondeterminism.

---

# 46. First size

I would not start with 10,000 organisms.

World Alpha:

```text
64 × 64 cells
4.096 locations

8 founders

capacity: 64 organisms

4 fields
4 resource types
2 hazards

1 world tick / simulation tick
```

It is enough to check almost the entire architecture.

---

# 47. Then World Beta

```text
256 × 256
65.536 cells

32 founders
capacity 512

regional ecology
reproduction
mutation
culture
communication
```

And only then I would scale more.

---

# 48. "Genesis" World

The first canonical world could be called:

```text
Genesis
```

Not because we are going to claim there is life, but because it would be the zero environment of the population.

I would freeze its configuration:

```text
worlds/genesis/world.toml
```

Conceptually something like this:

```toml
[world]
schema = 1
width = 64
height = 64
topology = "hex"
seed = 101

[population]
founders = 8
capacity = 64

[time]
checkpoint_interval = 1024

[fields]
count = 4

[resources]
count = 4

[hazards]
count = 2

[communication]
local = true
attenuation = true
```

The real meanings of each field/resource would be saved only in **apparatus metadata**.

Not in the organism contract.

---

# 49. Genesis should have a solvable ecology, but not trivial

Something like this:

```text
R1
abundante
poco nutritivo
regeneración rápida

R2
escaso
muy nutritivo
regeneración lenta

R3
beneficioso a corto plazo
daño diferido

R4
beneficioso sólo bajo determinado estado fisiológico
```

Fields:

```text
F1
ciclo periódico

F2
gradiente espacial

F3
ruido autocorrelacionado

F4
evento raro
```

Hazards:

```text
H1
dependiente de F1

H2
dependiente de densidad poblacional
```

With that alone really complex problems appear.

---

# 50. The population-dependent hazard especially interests me

For example:

```text
más población
      ↓
más contaminación / presión
      ↓
menor disponibilidad
```

Without calling it pollution.

This introduces **organism → world feedback**.

There true ecology appears:

```text
organismos cambian entorno
      ↓
entorno cambia selección
      ↓
selección cambia organismos
```

Without that feedback the world would be mainly a passive scenario.

---

# 51. Niche engineering

Later I would allow actions that slightly modify the world:

```text
resource depletion
waste production
local field alteration
persistent emissions
```

This can create **niche construction**.

A lineage could modify a territory in a way that favors its descendants.

We don't need to call it "building a nest".

It simply emerges from the dynamics.

---

# 52. What I would not do in World v1

I would expressly leave out:

```text
3D
visión por píxeles
```
```text
LLMs externos
física rígida
objetos manufacturables
herramientas
construcción compleja
depredación explícita
combate
sexualidad compleja
evolución de las leyes físicas
ecosistemas generados proceduralmente sin límite
```

All of that can come.

But right now it would obscure the main scientific question.

---

# 53. The scientific question of World v1

I would write it literally like this:

> **Can a Symbiont situated in a persistent and non-semantic spatial environment autonomously learn environmental regularities and modify its perception and behavior in a way that produces better physiological consequences, without receiving objectives, labels or reward signals from the evaluator?**

That is testable.

---

# 54. And World v2

Afterwards:

> **Can a population develop different ecological niches under the same world?**

---

# 55. World v3

> **Can between-generation selection produce heritable adaptation to niches without explicit fitness?**

---

# 56. World v4

> **Can socially learned information persist and improve results after its discoverers disappear?**

---

# 57. World v5

> **Can cumulative cultural innovation emerge that exceeds what is discovered individually?**

That does lead us to the big vision.

---

# 58. What I would measure from day one

The scientific apparatus should record, without supplying these metrics to the organism:

| Scale          | Variables                                                |
| -------------- | -------------------------------------------------------- |
| World          | spatial entropy, resources, stability, perturbations     |
| Ecology        | abundance, niches, competition, occupancy                |
| Individual     | age, reserves, movement, intake                          |
| Cognition      | predictive error, concepts, causal utility               |
| Sensors        | specialization, lineage, selection                       |
| Genetics       | mutations, diversity, distance                           |
| Phylogeny      | depth, branching, extinctions                            |
| Social         | encounters, reciprocity, isolation                       |
| Communication  | information, grounding, structure                        |
| Culture        | persistence, derivation, accumulation                    |
| Open-endedness | innovation, diversity, complexity                        |

I would not use any single metric as a "final score".

---

# 59. We need very strict controls

Each experiment should be able to run against variants:

```text
learning ON / OFF
sensor plasticity ON / OFF
culture ON / OFF
mutation ON / OFF
communication ON / OFF
spatiality ON / shuffled
resource scarcity ON / OFF
```

Then we can answer:

> did this appear thanks to learning?

instead of simply:

> "look what a curious behavior".

This is especially important because your own research program already found examples where an existing capacity could look like adaptation without having been autonomously selected. That discipline you applied to Sensory Plasticity should be maintained here too.

---

# 60. Observatory should allow counterfactual replay

Not change the original experiment.

But from a historical snapshot create:

```text
Branch A — replay original

Branch B — mismo estado,
           pero resource R3 desaparece

Branch C — misma población,
           comunicación desactivada
```

These branches belong to `symbiont_lab`.

Never to the original world.

That would be extremely powerful to infer causality.

---

# 61. Very important: living world and experiment are not exactly the same

We would have:

```text
WORLD
una entidad persistente
```

and:

```text
EXPERIMENT
una observación/control científico
sobre un mundo o réplica
```

The world can live for months.

Experiments can take reproducible clones of moments of that world.

That avoids sacrificing the "living history" every time we want to do science.

---

# 62. Two kinds of worlds

I would end up having:

### Canonical worlds

Permanent:

```text
Genesis
Gaia-1
...
```

They are not arbitrarily manipulated.

### Experimental worlds

Cloned:

```text
Genesis@tick-481720
 + perturbation X
```

for testing.

Thus we keep both:

**natural history**

as well as:

**experimental science**.

Avida precisely stood out for evolving from mere observation of digital evolution to rigorously controlled experimentation. ([Frontiers][12])

---

# 63. World and real world

There is another interesting point.

The original Symbiont lives on a real host.

I don't think we should abandon it.

We would have two ecologies:

```text
HOST ECOLOGY
mundo físico/computacional real

SYMBIONT WORLD
mundo digital controlado
```

That allows us something scientifically magnificent:

> test the same cognitive architecture in a perfectly known world and in a partially unknown real environment.

World would be our controlled laboratory.

Host would be our external world.

---

# 64. I would not replace `SharedHabitat`

I would turn it into a lower level.

Now we have approximately:

```text
SharedHabitat
```

I would evolve towards:

```text
World
 └ Region
    └ Habitat/Resource Surface
```

`SharedHabitat` can continue to be the bounded unit of a resource or a zone.

We don't need to throw it away.

---

# 65. Neither would I replace `IntegratedHabitatRuntime`

I would expand it towards:

```text
IntegratedWorldRuntime
```

conceptually:

```text
IntegratedHabitatRuntime
        ↓
one habitat/population runtime

IntegratedWorldRuntime
        ↓
many spatial habitats
+ topology
+ movement
+ fields
+ environment dynamics
```

It is a natural evolution of what you already have.

---

# 66. Final architecture I would propose

```text
                      WORLD KERNEL
                           │
         ┌─────────────────┼──────────────────┐
         │                 │                  │
      Topology           Fields           Resources
         │                 │                  │
         └──────────────┬──┴───────┬──────────┘
                        │          Hazards
                        ▼
                 Interaction Layer
                        │
           ┌────────────┴────────────┐
           ▼                         ▼
     Symbiont A                  Symbiont B
     sensors                     sensors
     cognition                   cognition
     physiology                  physiology
     culture                     culture
           │                         │
           └────────────┬────────────┘
                        ▼
                   World Commit
                        │
                append-only events
                        ▼
                  World Journal
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
         Observatory          Symbiont Lab
          passive             experiments
```

---

# 67. My decision on visualization

For humans I would make the world look much richer than it really is.

A field could be represented as:

```text
temperatura → color
resource density → vegetación
hazard → niebla
communication → ondas
```

although internally they are only numbers.

Thus Observatory can offer something almost akin to looking at a terrarium:

```text
             ◌ ◌
      ●→              ◉
           ≋≋≋
  ▲                     ●
          ◉ ◉
```

The drawings are ours.

The physics continues to be abstract.

That is perfect.

---

# 68. We could even have a "naturalist mode"

Without metrics.

Only:

```text
mapa
organismos
nacimientos
muertes
movimientos
señales
```

Like looking at an anthill.

And then activate:

```text
Scientific overlay
```

and see the whole truth.

I think that would make the project much more tangible.

---

# 69. How we will know it starts getting interesting

I would mark five levels.

```text
LEVEL 0 — SURVIVAL

el organismo simplemente persiste
```

```text
LEVEL 1 — ADAPTATION

cambia conducta según experiencia
```

```text
LEVEL 2 — ECOLOGY

diferentes organismos ocupan nichos distintos
```

```text
LEVEL 3 — EVOLUTION

aparecen diferencias heredables seleccionadas
```

```text
LEVEL 4 — CULTURE

conocimiento persiste entre individuos
```

```text
LEVEL 5 — OPEN-ENDEDNESS

continúan apareciendo novedades adaptativas
que nosotros no habíamos enumerado
```

I would not claim LEVEL 5 quickly.

Current literature is quite clear that this remains one of the fundamental difficulties of Artificial Life. ([MIT Press Direct][13])

---

# 70. How I would really build it

I would divide it into **seven milestones**, but without developing everything at once.

### W0 — contracts

Create:

```text
symbiont_world
WorldState
WorldObservation
WorldAction
WorldEvent
WorldCheckpoint
```

without ecology yet.

### W1 — space

```text
hex topology
occupancy
movement
local observations
deterministic resolution
```

A single Symbiont.

### W2 — causal world

```text
fields
resources
hazards
cycles
spatial gradients
```

A Symbiont living permanently.

### W3 — metabolism

Couple:

```text
resource acquisition
→ existing physiology
→ dormancy/death
```

Here "living in the world" truly exists.

### W4 — population

```text
multiple organisms
local competition
birth
death
genealogy
```

### W5 — society

```text
local encounter
communication range
culture
social consequences
```

### W6 — longitudinal evolution

```text
mutation
selection
lineages
niches
```
extinction
```

### W7 — open-ended research

Do not add features just for the sake of adding them.

Measure:

```text
innovation
complexity
niche creation
cultural evolution
```

---

# 71. First experiment I would run

Not 20 little bugs.

**One.**

```text
WORLD-0001
       │
       ▼
Symbiont A
```

We leave it for several hundreds of thousands of ticks.

The world has:

```text
2 recursos beneficiosos
1 perjudicial retardado
2 ciclos ambientales
1 gradiente espacial
```

And we ask only:

> does A learn anything true about the world that causally improves its physiological trajectory?

We need to demonstrate that before filling the map.

---

# 72. Second experiment

Two identical Symbionts:

```text
same genome
same starting cell
```

but:

```text
different stochastic history
```

We want to test:

> do their sensors, concepts and behavior really diverge?

This is particularly important because your recent sensory research found complete convergence under various conditions. `research/STATUS.md` records, for example, `unique_phenotypes = 1` in the previous protocol and 18/18 organisms converging on the same preference in another protocol.

World should provide us with environments where **history really matters**.

---

# 73. Third experiment

8 founders.

No mutation.

Goal:

```text
ecological differentiation
without genetic variation
```

If niches appear, they are ontogenetic/social.

---

# 74. Fourth

We activate mutation.

Then we can separate:

```text
plasticidad
vs
evolución
```

---

# 75. Fifth

We activate culture.

Then we already have the three temporalities:

```text
APRENDIZAJE
durante una vida

EVOLUCIÓN
entre generaciones

CULTURA
entre individuos y generaciones
```

That is, for me, **the true great Symbiont experiment**.

---

# Conclusion

After reviewing both the background and the current code, **I would indeed build Symbiont World**.

But not as a side project.

I consider it the logical step after organism v1.

Until now we have been building:

> **the bug.**

World would allow us to stop asking only:

> "does this cognitive mechanism work?"

and start asking:

> **"what does this organism do when it has a life to live?"**

The current architecture is surprisingly well prepared for it: the `source → sensor → percept` boundary, the physiology, irreversible death, bounded reproduction, heredity separate from phenotype, culture with provenance and the passive Observatory are exactly the elements that make it viable to do it without turning it into an RL video game.

My base design, therefore, would be:

> **A 2D hexagonal universe, spatial and persistent; causal but semantically opaque; with fields, resources, risks and cycles; local interaction, finite resources, physical cost of action and perception, real reproduction and death within the existing physiology, spatial communication, heredity and culture; completely event-sourced, deterministic and reproducible; observed from the outside by Observatory without any return channel.**

And I would do one more thing before implementing a single line: **I would write `docs/design/symbiont-world.md` as a normative specification**, along with the epistemological invariants, tick model, `WorldObservation/WorldAction` contracts, event schema, Genesis v1 and the first preregistered experiments. Then we would really have a sufficiently rigorous base to start building the bugs' world.

[1]: https://direct.mit.edu/artl/article/10/2/191/2455/Avida-A-Software-Platform-for-Research-in?utm_source=chatgpt.com "Avida: A Software Platform for Research in Computational Evolutionary Biology | Artificial Life | MIT Press"
[2]: https://pmc.ncbi.nlm.nih.gov/articles/PMC2801533/?utm_source=chatgpt.com "How evolution guides complexity - PMC"
[3]: https://openai.com/index/neural-mmo/?trk=public_profile_project-title&utm_source=chatgpt.com "Neural MMO: A massively multiagent game environment | OpenAI"
[4]: https://deepmind.google/blog/melting-pot-an-evaluation-suite-for-multi-agent-reinforcement-learning/?utm_source=chatgpt.com "Melting Pot: an evaluation suite for multi-agent reinforcement learning — Google DeepMind"
[5]: https://arxiv.org/abs/1901.01753?utm_source=chatgpt.com "Paired Open-Ended Trailblazer (POET): Endlessly Generating Increasingly Complex and Diverse Learning Environments and Their Solutions"
[6]: https://direct.mit.edu/artl/article/25/2/198/2923/Open-Endedness-for-the-Sake-of-Open-Endedness?utm_source=chatgpt.com "Open-Endedness for the Sake of Open-Endedness | Artificial Life | MIT Press"
[7]: https://direct.mit.edu/artl/article/31/2/129/130570/Ecology-Spatial-Structure-and-Selection-Pressure?utm_source=chatgpt.com "Ecology, Spatial Structure, and Selection Pressure Induce Strong Signatures in Phylogenetic Structure | Artificial Life | MIT Press"
[8]: https://direct.mit.edu/artl/article/30/3/417/116175/Evolved-Open-Endedness-in-Cultural-Evolution-A-New?utm_source=chatgpt.com "Evolved Open-Endedness in Cultural Evolution: A New Dimension in Open-Ended Evolution Research | Artificial Life | MIT Press"
[9]: https://direct.mit.edu/artl/article/26/2/274/93255/The-Surprising-Creativity-of-Digital-Evolution-A?utm_source=chatgpt.com "The Surprising Creativity of Digital Evolution: A Collection of Anecdotes from the Evolutionary Computation and Artificial Life Research Communities | Artificial Life | MIT Press"
[10]: https://direct.mit.edu/artl/article/25/1/50/2915/The-MODES-Toolbox-Measurements-of-Open-Ended?utm_source=chatgpt.com "The MODES Toolbox: Measurements of Open-Ended Dynamics in Evolving Systems | Artificial Life | MIT Press"
[11]: https://direct.mit.edu/artl/article/31/1/106/124849/Survival-and-Evolutionary-Adaptation-of?utm_source=chatgpt.com "Survival and Evolutionary Adaptation of Populations Under Disruptive Habitat Change: A Study With Darwinian Cellular Automata | Artificial Life | MIT Press"
[12]: https://www.frontiersin.org/journals/ecology-and-evolution/articles/10.3389/fevo.2021.739047/full?utm_source=chatgpt.com "Frontiers | Symbiosis in Digital Evolution: Past, Present, and Future"
[13]: https://direct.mit.edu/artl/article/30/1/1/120293/What-Is-Artificial-Life-Today-and-Where-Should-It?utm_source=chatgpt.com "What Is Artificial Life Today, and Where Should It Go? | Artificial Life | MIT Press"
