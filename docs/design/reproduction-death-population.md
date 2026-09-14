# Reproduction, death and bounded population

Status: design specification for Milestones F-G-H.

This document packages the life-cycle decisions that follow from long-run resident development, reversible structural plasticity and the first observed cognitive saturation of a real resident Symbiont.

The purpose is to make reproduction, death and population control first-class computational semantics rather than process-management metaphors.

## 1. Motivation

A long-running resident can reach a healthy but saturated cognitive phenotype.

The motivating resident observation was:

```text
Topology health       ADAPTIVE
Nodes                 64 / 64 soft budget
  SENSE               31 / 32 sense budget
  CONCEPT             32 / 32 kernel maximum
  READOUT              1
Edges                181 / 384 soft budget
Orphan latent nodes    0
```

This is not degeneration. The graph is connected, the readout is live and structural plasticity continues through edge learning. The individual has instead reached a bounded representational capacity while the environment can still provide new developmental evidence.

That suggests a functional reproductive signal: **persistent developmental pressure that the current individual can no longer express within its allowed phenotype**.

The design must also prevent that signal from becoming uncontrolled exponential process creation. Reproduction therefore requires physiology, death and habitat-level carrying capacity.

## 2. Core principles

1. **Genome is inheritance. Phenotype is lifetime experience.**
2. **A checkpoint is an individual, not a genome.**
3. **Birth creates a new organism identity.** It is never a renamed process or copied PID.
4. **Death closes organism continuity irreversibly.** A dead identity cannot be resumed as if no death occurred.
5. **Reproductive readiness is endogenous; materialization is habitat-authorized.**
6. **No birth bypasses carrying capacity or resource allocation.**
7. **No organism may create descendants by arbitrary process spawning, remote placement or self-selected deployment targets.**
8. **Population control is ecological and resource-bounded, not an unbounded fork tree.**
9. **Organism lineage and genome lineage are distinct.** Multiple organisms may share exactly the same genome.
10. **No evaluator label becomes a reproductive teaching signal.**

## 3. Reproductive mechanism: clonal budding

The first asexual mechanism is **clonal budding**, not clonal fission.

In clonal budding the parent remains the same individual and continues living. A new descendant is created with a new identity, the same genome and an empty germinal phenotype.

```text
               parent organism
                     │
          sustained reproductive pressure
                     │
                     ├──────────────────────┐
                     │                      │
                     ▼                      ▼
               same parent              offspring
               continues               new identity
               same state              same genome
               same graph              empty germinal graph
                                       empty lifetime memory
                                       independent development
```

The offspring inherits the parent's genome but does **not** inherit the parent's acquired cognitive phenotype.

### 3.1 Inherited at clonal birth

- exact genome configuration and genome identity;
- kernel compatibility requirements;
- habitat membership/placement authorization;
- organism-lineage parent reference.

### 3.2 Not inherited at clonal birth

- CognitiveGraph nodes or edges;
- concepts, states, predictors, gates or readouts developed by the parent;
- learned weights or eligibility traces;
- ConceptLineage;
- sensory baselines, utility statistics or discovered-sense history;
- beliefs, attention state, investigations or narratives;
- sensory relations;
- transient activation;
- parent's checkpoint, tick or random-generator state.

The descendant starts from the canonical germinal graph and develops independently inside the same authorized habitat.

This creates a clean experimental distinction between heredity and acquired experience.

## 4. Reproductive pressure

Simple saturation is not sufficient to reproduce.

A mature graph at its node limit may simply have nothing useful left to learn. Reproduction becomes relevant only when capacity is exhausted **and valid new developmental evidence remains blocked by that capacity**.

The intended readiness condition is conceptually:

```text
topology_health == ADAPTIVE
AND recovering == false
AND organism_viable == true
AND conceptual_capacity_exhausted == true
AND valid_blocked_growth_evidence persists
AND physiological_reproduction_reserve is sufficient
```

For the current cognitive substrate, `conceptual_capacity_exhausted` can include both:

- `concept_count >= kernel.max_concepts`, and/or
- `node_count >= genome.development.soft_node_budget`.

`valid_blocked_growth_evidence` means candidate evidence that would otherwise be eligible for structural growth but cannot be committed because the individual has exhausted its permitted phenotype capacity.

A one-tick spike must not be enough. Readiness requires persistence across a bounded number of consolidation epochs.

## 5. Reproductive-pressure consumption

A successful birth consumes the accumulated reproductive pressure that justified it.

The parent remains structurally intact, but the pressure ledger is reset or reduced so that the same blocked evidence cannot produce descendants repeatedly.

```text
blocked growth evidence
        ↓
persistent reproductive pressure
        ↓
READY
        ↓
authorized birth
        ↓
consume pressure + reproduction cost
        ↓
new blocked evidence required for next birth
```

This is analogous to consuming concept-candidate support after committed concept birth: pre-birth evidence cannot act as permanently reusable credit.

A failed or denied birth does not silently consume evidence unless the physiology design explicitly charges an attempted-reproduction cost.

## 6. Reproduction has physiological cost

Clonal budding is not free.

Once digital physiology exists, reproduction must consume an explicit bounded reserve or resource allocation. The exact unit is defined by the physiology milestone, not hard-coded here.

Conceptually:

```text
reproductive_pressure
AND healthy enough
AND reserve >= reproduction_cost
AND habitat grants descendant slot
        ↓
BIRTH
        ↓
parent.reserve -= reproduction_cost
```

This creates an organism-level trade-off between maintenance, learning and reproduction.

The habitat also allocates the descendant's initial CPU, memory, storage and observation budget. The offspring cannot exist outside an explicit allocation.

## 7. Habitat authority and carrying capacity

An organism may express reproductive readiness but cannot materialize another process or placement target by itself.

Birth is an authorized habitat operation.

The habitat owns:

- population hard limit;
- descendant slots;
- aggregate CPU/memory/storage ceilings;
- valid placement targets;
- organism identity allocation;
- lineage registration;
- admission and consent;
- lifecycle audit records.

When carrying capacity is full:

```text
REPRODUCTIVELY_READY
        ↓
BIRTH_BLOCKED_BY_HABITAT
```

The parent remains alive. A requested birth does **not** automatically kill, evict or replace another organism.

This rule prevents reproduction from becoming a hidden selection operator implemented by the habitat.

## 8. Death

Death is an explicit irreversible lifecycle transition:

```text
viable organism
      ↓
STRESSED / DORMANT / FAILING
      ↓
recovery impossible
      ↓
DYING
      ↓
DEAD
```

`DEAD` means the organism identity is permanently closed.

Stopping a process is not death. Restarting a viable checkpoint is not birth. Deleting a container is not automatically a biological death event unless continuity is explicitly closed.

### 8.1 Initial death causes

The first implementation should use a closed cause vocabulary, for example:

- `homeostatic_failure` — the organism can no longer maintain viability under bounded resources;
- `integrity_failure` — durable organism state cannot be restored safely after bounded repair attempts;
- `irrecoverable_cognitive_failure` — required viable organization cannot be recovered within kernel rules;
- `explicit_retirement` — an authorized operator intentionally closes the organism's continuity.

Administrative process shutdown without continuity closure remains `STOPPED`, not `DEAD`.

Future ecology may add carefully specified causes, but arbitrary free-text causes should not become behavior inputs.

### 8.2 No implicit resurrection

A final dead checkpoint may be retained as a historical artifact, but normal restore must reject it.

```text
checkpoint.lifecycle == DEAD
        ↓
resume() rejected
```

An experiment may later reconstruct or clone from historical artifacts, but that operation creates a **new organism identity** and must never masquerade as continued life of the dead individual.

## 9. Resource release after death

A dead organism no longer consumes active habitat capacity.

Death releases its live resource allocation and descendant slot eligibility, subject to bounded archival policy for lineage and final records.

This closes the population loop:

```text
birth
→ development
→ maturation
→ reproduction
→ stress / decline / failure
→ death
→ resource release
→ capacity for later birth
```

Death alone is not sufficient population control. A population remains bounded only because births are habitat-authorized and carrying capacity is a hard external invariant.

## 10. Organism lineage versus genome lineage

The existing laboratory `LineageArchive` describes **genome lineage**. That remains correct for mutation/recombination experiments.

Ecological reproduction needs a separate **organism lineage**.

### 10.1 Genome lineage

```text
genome G1
   ↓ mutation / recombination
genome G2
```

A new genome identity is created only when the heritable genome itself changes.

### 10.2 Organism lineage

```text
organism A --clonal budding--> organism B
        genome G1                  genome G1
```

No new genome identity is required for an exact clone.

A minimal durable organism birth record should contain fields equivalent to:

```text
organism_id
parent_organism_ids
reproduction_mode
habitat_id
genome_id
birth_event_id
born_at
parent_tick
parent_topology_revision
```

A minimal death record should contain:

```text
organism_id
death_event_id
died_at
death_tick
death_cause
final_topology_revision
genome_id
```

Records are append-only and must not contain raw telemetry merely because it existed near a birth or death event.

## 11. Lifecycle state separation

Three different state dimensions must not be collapsed into one enum.

### Organism lifecycle

```text
GERMINAL
DEVELOPING
MATURE
STRESSED
DORMANT
DYING
DEAD
```

### Cognitive topology health

```text
GERMINAL
DEVELOPING
CONNECTED
ADAPTIVE
DEGENERATE
RECOVERING
```

### Reproductive state

```text
NOT_READY
ACCUMULATING_PRESSURE
READY
BIRTH_BLOCKED_BY_HABITAT
COOLDOWN
```

For example, an organism can be:

```text
lifecycle=MATURE
topology_health=ADAPTIVE
reproduction=READY
```

without any contradiction.

## 12. Population safety invariants

The following are permanent safety properties:

1. Population cannot exceed habitat carrying capacity.
2. An organism cannot enlarge carrying capacity through learned or mutated state.
3. Birth cannot select arbitrary hosts or network destinations.
4. Reproduction cannot bypass normal owner/habitat consent.
5. A birth transaction either creates a complete new organism + lineage record + resource allocation or creates none of them.
6. A denied birth leaves no hidden process, partial checkpoint or lineage edge.
7. Reproductive readiness alone never creates a process.
8. A birth never silently kills another organism to make room.
9. Dead identities cannot be normally resumed.
10. Genome mutation cannot alter permissions, executable behavior or hard kernel limits.
11. Population metrics remain evaluator-side and are never fed back as ground-truth fitness labels.
12. Observatory remains observational; it may display readiness, births and deaths but does not command them.

## 13. Selection and ecology

Once births, deaths and finite resources exist, long-run reproductive success can emerge without being directly optimized by the organism runtime.

Different genomes may trade off:

- learning speed;
- maintenance cost;
- structural turnover;
- reproductive timing;
- reproduction cost tolerance;
- dormancy behavior;
- lifespan.

The habitat should not decide which strategy is "best" by injecting an evaluator score into cognition. Population outcomes are measured externally.

A bounded habitat may then observe birth rate, death rate, lineage persistence, extinction, specialization, competition or cooperation as ecological outcomes.

## 14. Implementation sequence

### F1 — life/death foundation

- stable `organism_id` distinct from PID, state-file path and genome identity;
- lifecycle state and explicit `DEAD` terminal state;
- append-only birth/death records;
- restore rejection for dead identities;
- transactional finalization and resource release hooks.

### G1 — reproductive pressure

- bounded pressure accumulator derived from blocked valid structural growth;
- persistence across multiple consolidation epochs;
- readiness state separate from topology health;
- successful-birth pressure consumption and cooldown;
- no descendant materialization yet.

### G2 — minimal habitat birth authority

- `habitat_id` and authorized participant registry;
- hard carrying capacity;
- descendant-slot reservation;
- aggregate resource reservation;
- transactional birth protocol.

This is the minimum habitat primitive required before any reproduction can be materialized. Milestone H later expands it into a full ecological resource model.

### G3 — clonal budding

- parent remains alive;
- child receives same genome and new identity;
- child starts canonical germinal graph and empty lifetime phenotype;
- same habitat membership;
- parent pays reproduction cost;
- birth is all-or-nothing.

### G4 — heritable variation and paired reproduction

- genome lineage remains separate from organism lineage;
- mutation/recombination creates new genome identities;
- optional bounded epigenetic inheritance is separate from genetics;
- cultural transfer occurs post-birth through normal ecological communication.

### H — ecological population dynamics

- finite shared resources;
- physiological resource competition;
- carrying-capacity enforcement;
- population birth/death accounting;
- lineage survival/extinction studies;
- declared inter-organism interaction channels.

## 15. Longitudinal acceptance tests

The design is not complete until deterministic tests demonstrate at least:

1. Saturation without blocked growth does not create readiness.
2. Persistent eligible blocked growth does create readiness in a viable adaptive organism.
3. One tick of saturation does not reproduce.
4. A full habitat rejects birth transactionally.
5. No rejected birth leaves a child process, checkpoint or lineage record.
6. Successful clonal birth leaves the parent unchanged except declared physiological/reproductive accounting.
7. The child has a new organism identity, the same genome and an empty germinal phenotype.
8. Parent and child develop independently after birth.
9. Successful birth consumes the pressure that caused it; immediate repeated birth from the same evidence is impossible.
10. Population can never exceed carrying capacity under repeated concurrent readiness events.
11. Death releases live habitat allocation.
12. A dead organism cannot be restored through the normal resident restore path.
13. Stopping and restarting a viable organism preserves its identity and is not recorded as death/birth.
14. Genome lineage changes only when genome material changes; exact clonal siblings can share one genome identity.
15. Population metrics remain outside organism cognition.

## 16. Observatory requirements

Population/lineage observability should eventually show:

```text
Habitat H1
capacity  3 / 8

worker-3       MATURE     ADAPTIVE   READY
worker-3.1     DEVELOPING GERMINAL   NOT_READY
worker-7       DORMANT    CONNECTED  NOT_READY
worker-2       DEAD       —          —
```

A lineage view should distinguish organism descendants from genome mutation ancestry. Dead organisms remain visible as historical records but consume no live population slot.

No decorative activity should be fabricated. Birth, death, pressure changes and topology revisions are rendered only when corresponding durable/runtime events actually occur.

## 17. Design decision

The default first asexual reproductive mechanism is therefore:

> **Clonal budding under habitat authority.** A viable adaptive organism that persistently accumulates valid developmental pressure beyond its bounded phenotype may become reproductively ready. If physiology and habitat capacity permit, the habitat atomically materializes a new organism in the same habitat with a new identity, the same genome and an empty germinal phenotype. The parent continues living, pays the declared reproduction cost and consumes the pressure that justified that birth. Population remains bounded by hard habitat carrying capacity. Death is an explicit irreversible closure of organism continuity that releases live habitat resources but never silently permits resurrection.
