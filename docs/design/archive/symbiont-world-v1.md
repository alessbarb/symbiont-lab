---
id: design.world.symbiont-world-v1
title: "Symbiont World V1"
document_type: design
domain: world
status: superseded
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Symbiont World v1

> **Normative specification, not implementation.** Nothing described here
> exists in `src/`. This document fixes the contract, the invariants and the
> tick model that any future implementation of `symbiont_world` must
> comply with. The real implementation status is only verified in
> [`../roadmap.md`](../roadmap.md) and [`../../ORGANISM.md`](../../ORGANISM.md).
> The rationale, the ALife background and the bibliography that motivate
> this design are in
> [`symbiont-world-v1-rationale.md`](symbiont-world-v1-rationale.md).

## 1. What it is

Symbiont World is a spatial, persistent, causal, finite and
semantically opaque digital environment from the perspective of its inhabitants, capable of
indefinitely sustaining an ecology of Symbionts and of producing a complete
reproducible record of its history. It is not a game: no quests, no
score, no explicit fitness, no reward. The only consequence of an
action is its physical effect on the organism executing it.

It is a third piece alongside `symbiont` and `symbiont_lab`, not a replacement for
`SharedHabitat` nor for `IntegratedHabitatRuntime`: it extends them with spatial
topology, fields and environmental dynamics.

## 2. Package boundary

```
symbiont_world   →  (nothing)
symbiont         →  (nothing new; still does not import symbiont_lab)
symbiont_lab     →  symbiont_world, symbiont
```

`symbiont_world` does not import `symbiont` nor `symbiont_lab`. `symbiont` does not
import `symbiont_world`: the organism continues receiving only normalized readings
through `source → sensor → percept`, just like with the real host. `WorldObservation` and `WorldAction` (§4) are owned by
`symbiont_world`; `symbiont_lab` is the one who instantiates a world, connects it to an
existing `ModeledOrganismRuntime` and translates in both directions. This
document adds a rule to the existing AST dependency tests
(`tests/experimental_integrity/test_ground_truth_boundary.py` and alike):
no `symbiont_world` import appears under `src/symbiont/`.

## 3. Epistemological invariants

Each one must be verifiable by an automated test before the world
feeds a real organism:

1. **No ground truth to the organism.** No `world.semantic.*`,
   `observer.*` or `ground_truth.*` field crosses into `Sensor`, `CognitiveGraph`,
   Private SLM, culture or decision. The resources and fields have opaque
   identity (`resource.<hash>`, `field.<hash>`); their real meaning lives
   exclusively in apparatus metadata (`symbiont_lab`), never in the
   contract that the organism sees.
2. **Strict determinism.** `world_seed + events + RNG state ⇒` unique
   future. The world's RNG uses namespaced streams with the same derivation
   scheme as `symbiont.environment.rng.derive_seed` (sha256 of
   `prefix:seed:namespace`), reimplemented inside `symbiont_world` without
   importing `symbiont` (§2), so as not to disturb the same-seed
   reproducibility of the existing synthetic experiments.
3. **No Observatory backchannel.** `Observatory → World` does not exist,
   not even disabled. Observatory only reads `WorldEvent` and snapshots.
4. **No imposed fitness.** No evaluator-side utility function is
   injected as a signal to the organism. Selection emerges only from already existing
   resources, cost, reproduction and death in the physiology.
5. **No global broadcast.** All communication and all contact are local:
   they depend on `range`, `attenuation` and cost. There is no channel that
   reaches the entire population in a tick.
6. **No duplicating physiology.** World never introduces a second energy/health
   accounting; it only produces inputs (`resource acquisition`) that are
   delivered to the already existing `MetabolicLedger` in `symbiont`.
7. **Perceptive failure is tolerated; state transition failure is not.** Two
   classes of failure are distinguished, with opposite semantics:
   - **Observation failure** (e.g. a punctual `ObservableSource` does not
     produce reading): the organism continues the tick with percept
     missing/unavailable, just like a real provider can fail without
     stopping cognition.
   - **World state transition failure** (e.g. `field propagation` or
     `resolve resource competition` do not complete consistently): the
     world tick **is not committed**. There is no partial advance of
     causality — either the full tick is applied (commit), or it aborts and
     retries from the last committed state (rollback). An organism
     never cognizes nor acts upon a tick that did not physically occur.

## 4. `WorldObservation` / `WorldAction` contract

Two types, and nothing else crosses the boundary.

### `WorldObservation` (World → organism, via `ObservableSource`)

Allowed fields, all scalars or bounded vectors of scalars:

- `signals: Mapping[SignalId, float]` — local field/resource readings
  under opaque identity (`SignalId` is a stable hash, not a semantic
  name).
- `contact: Sequence[ContactEvidence]` — evidence of nearby sources
  (intensity, not typed identity: never `entity.type = symbiont`).
- `reception: Sequence[ReceivedEmission]` — received emissions with
  attenuated intensity, same contract as the existing structured
  communication.
- `internal: Mapping[str, float]` — projection of already existing internal
  physiological state (reserve, integrity), not new.

Explicitly excluded: `cell_id`, absolute coordinates, orientation
numbered with semantics, any `field.NN =` with real name, distance to
a target with imposed meaning.

### `WorldAction` (organism → World)

- `move: ActuatorId` — one of a small, fixed repertoire of opaque directional
  channels plus "stay"; the actuator→direction mapping lives only in
  apparatus metadata.
- `sample: SignalId | None` — sampling intent of a local source.
- `acquire: SignalId | None` — acquisition intent of a local resource.
- `emit: OpaqueSequence | None` — reuses the existing structured communication
  channel, with added cost and spatial range.
- `rest: bool`

Explicitly excluded: `eat()`, `attack()`, `mate()`, `trade()` or
any action with high-level semantics imposed by the design. The
emergent meaning of primitive combinations is a result to
observe, not a capability to implement.

Both types are immutable per tick and do not expose any handle to `World`,
`Cell`, `Resource`, `Hazard` nor to the ground truth.

## 5. Tick model

The order is part of the contract, not an implementation detail; no
implementation can depend on dictionary iteration order or
thread scheduling. The sequence is unique, but the *ownership* of each phase
is separated by design: `symbiont_world` (WORLD/RESOLUTION/COMMIT) never
executes cognition, and `symbiont` (ORGANISM) never sees raw world state —
`symbiont_lab` is the only orchestrator that crosses the boundary in both
directions:

```
WORLD PHASE           (owner: symbiont_world.WorldKernel)
 1  world scheduled processes
 2  field propagation
 3  resource renewal/decay
 4  local observation surfaces per organism → WorldObservation

ORGANISM PHASE        (owner: symbiont_lab orchestrator, delegating to
                        already existing symbiont.*; symbiont_world does not participate)
 5  sensor sampling (existing Sensor contract)
 6  organism cognition
 7  organism decisions → WorldAction intents

RESOLUTION PHASE      (owner: symbiont_world.WorldKernel, consumes
                        WorldAction, never internal state of the organism)
 8  resolve movement
 9  resolve resource competition
10  resolve contacts
11  resolve communications
12  physiological consequences — translated by symbiont_lab into the
    existing `MetabolicLedger` in `symbiont`; the World kernel only
    produces acquired resource quantities, does not apply physiology
13  births (existing habitat-authorized path, invoked by symbiont_lab)
14  deaths (existing terminal physiology state, invoked by symbiont_lab)
15  cultural deliveries (existing entry points, invoked by symbiont_lab)

COMMIT PHASE          (owner: symbiont_world.WorldKernel)
16  telemetry
17  journal commit (append WorldEvent) — tick is committed here; before
    this point a failure in WORLD/RESOLUTION phase aborts the entire tick
18  checkpoint if due
```

Phases 12–15 are the responsibility of `symbiont_lab` as adapter: the
World kernel never imports or invokes `MetabolicLedger`,
reproduction or culture directly — it only emits the quantities/events that the
orchestrator translates to the already existing `symbiont` APIs. This is
what keeps the §2 package boundary valid.

**Resolution of simultaneous intents.** When two or more organisms declare
intent over the same resource/cell in the same tick, the resolution never
depends on the intent execution order (avoids accidental advantage
by order). The allocation rule (proportional, deterministic lottery with
namespaced RNG, or cost-dependent) is explicitly declared in the
world configuration and must be reproducible byte-by-byte for the same
seed and the same set of intents.

## 6. Event schema (`WorldEvent`)

World is event-sourced from day one; snapshots are a performance
optimization, not the source of truth.

```
event_id
world_id
tick
kind            # WORLD_FIELD_CHANGED | RESOURCE_RENEWED | ORGANISM_MOVED |
                # RESOURCE_ACQUIRED | ORGANISM_EMITTED | ORGANISM_CONTACT |
                # BIRTH | DEATH | GENOME_MUTATION | CULTURAL_TRANSMISSION
actor           # organism id, or null for purely environmental events
position        # opaque cell id
payload         # bounded, typed by kind
causal_parent_ids       # event_id[] — mechanical causality known by the
                        # kernel, e.g. RESOURCE_ACQUIRED →
                        # METABOLIC_RESERVE_CHANGED
contributing_event_ids  # event_id[] — relevant antecedents without affirming
                        # sufficient causality, e.g. a sequence of
                        # METABOLIC_RESERVE_CHANGED contributing to
                        # REPRODUCTION_READY, where the threshold depends on
                        # accumulated state and not on a single prior event
```

The log is append-only. `causal_parent_ids` is reserved for relations that the
kernel guarantees by construction (a state transition that can only
occur as a direct effect of another, in the same tick or the immediate
next). Everything else —relations depending on accumulated state,
thresholds or multiple concurrent antecedents— goes into
`contributing_event_ids`. Observatory must distinguish both when reconstructing
genealogies: presenting `contributing_event_ids` as strict causality
would be affirming more certainty than the kernel has.

## 7. Genesis v1 (frozen configuration)

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

The real meaning of each `field.N`/`resource.N`/`hazard.N` (what cycle
it follows, what physiological effect it produces, what depends on what) is documented
only in apparatus metadata inside `symbiont_lab`, never in the
organism's contract nor in this frozen configuration file.

At least one resource must have immediate benefit with deferred damage (to
test if the existing predictive system avoids preferring it out of pure
reactivity), and at least one hazard must depend on population density (to
introduce organism→world feedback, not just world→organism).

### Genesis frozen ground truth

`world.toml` fixes dimensions and counts; it is not enough to identify a reproducible
world because the real dynamics remain unspecified. It needs a
second file, evaluator-side and never visible to the organism:

```
experiments/world/genesis-v1/world-ground-truth.toml
```
which freezes, for each `field.N`/`resource.N`/`hazard.N`:

```
field equations              # exact functional form (e.g. F(t)=a+b·sin(ωt+φ))
initial distributions
diffusion constants
resource renewal laws
resource physiological effects   # mapping to MetabolicLedger effects
hazard equations
population-density coupling      # explicit coupling for W06
delays                            # e.g. the delay of deferred damage
RNG namespaces                    # via symbiont.environment.rng.derive_seed
boundary conditions
```

`Genesis seed = 101` without this file does not identify a world: it identifies only
its geometry and counts. The full reproducible tuple is
`(world.toml, world-ground-truth.toml, seed)`.

### Founder placement

The 8 founders share genome and germline architecture, but **not** the
same starting cell: placing them together would introduce intense social
interaction before any has learned to perceive the world. The
placement is a deterministic function `seed → founder placement`, declared
in `world-ground-truth.toml`, not random at runtime nor
chosen by the implementer ad hoc.

W02 is the deliberate exception: to isolate divergence by pure
stochastic history, its replicas start from the same starting cell, just as
already fixed by the gate.

### Spatial Embodiment (`WorldBody`)

It belongs to `symbiont_world`, not to the organism's `SelfModel` — it is what the
world knows about where a body is, not what the organism believes about
itself:

```
WorldBody {
    organism_id
    occupied_cell
    orientation_state
    interaction_radius
    emission_origin
}
```

Occupancy rule for Genesis v1: **a cell admits at most one
living organism.** This gives a clear physical meaning to movement, contact,
territorial blocking and density without introducing multiple collision
resolution. A `move` intent towards an already occupied cell fails like
any other losing intent in the simultaneous resolution of §5.

### Map boundary

`hard/reflecting boundary`, not toroidal. A toroidal topology is computationally
cheap but introduces an artificial physics (exiting east
reappears west) that the organism has no honest way to discover
as a regularity. With a reflecting/impermeable boundary, a `move` intent
that would cross the edge fails — the action's cost can continue
applying — and the organism can learn the regularity empirically,
without receiving the concept "wall" or "edge".

## 8. Falsification gates (W01–W07)

Preregistered before running, with explicit criteria for what counts as
a negative result — not just success. Given the history of this repo
(`genesis: controls ineffective` in previous emergent ecology runs,
`unique_phenotypes = 1` in a sensory protocol, and a negative result of
reversible pressure with p=1.0 in the most recent evolutionary probe), the default
is to expect trivial convergence and demand positive evidence, not the reverse.

| Gate | Question | Rejects H0 if | H0 (default) |
|------|----------|----------------|---------------|
| W01 | Does a single Symbiont improve its physiological trajectory above a random action policy under the same world? | significant improvement vs. random control, same seed, multiple replicas | no measurable improvement |
| W02 | Do two identical Symbionts (same genome, same starting cell) diverge in sensors/concepts/behavior under different stochastic history? | measurable phenotypic divergence between replicas | complete convergence (repeats the `unique_phenotypes = 1` pattern already observed) |
| W03 | Do 8 founders without mutation produce ecological differentiation (niches) purely ontogenetic/social? | niche clustering statistically distinct from noise | no differentiation |
| W04 | Does activating mutation change the W03 result beyond what is explainable by plasticity alone? | effect attributable to heritable variation, with isolated plasticity control | mutation adds no separation over W03 |
| W05 | Does activating culture allow knowledge learned by an individual to persist and benefit descendants who never lived the original discovery? | measurable benefit in lineage after the discoverer's disappearance, controlled against null transmission | no useful persistence |
| W06 | Does the population density-dependent hazard produce detectable organism→world→selection feedback? | causal correlation (not just temporal) between density and resulting selective pressure | no detectable feedback |
| W07 | Does any innovation appear that is classifiable according to the novelty ontology frozen below, not enumerated by the designer before the run? | event crosses the four conditions of the novelty ontology | absence of novelty crossing them |

Each gate runs with a matrix of controls: `learning ON/OFF`, `sensor
plasticity ON/OFF`, `culture ON/OFF`, `mutation ON/OFF`, `communication
ON/OFF`, `spatiality ON/shuffled`, `resource scarcity ON/OFF`. A result
is only reported as an observation (`OBSERVED` / `NEEDS_REPLICATION`), never
as a confirmed claim, without a second independent preregistration — same
protocol as `longitudinal-population-ecology-v1.md`.

### Novelty ontology for W07

"Not enumerated by the designer" is too lax on its own — it lends itself to
retrospective interpretation. Before running W07 it is frozen, without
later exceptions:

```
descriptor spaces     behavioral | ecological | cognitive | cultural
distance_threshold     minimum distance to the closest phenotype/behavior
                        already observed in the corresponding descriptor space
persistence_threshold  minimum ticks that the trait must remain active
adaptive_value         measurable causal improvement (not just correlational) in
                        physiological trajectory or offspring
minimum_replication    minimum number of independent instances before
                        reporting, not an isolated event
```

```
novelty =
    distance(new, previously_observed) > distance_threshold
    AND persistence ≥ persistence_threshold
    AND adaptive_value demonstrated (not just "looks interesting")
    AND replication ≥ minimum_replication
```

Without the four conditions it is not reported as novelty — it is reported, at
most, as unclassified `OBSERVED`. This is mandatory if the project
wants to speak seriously about open-endedness (MODES demands exactly this
discipline, not ad hoc post-hoc judgment).

### Formal barrier between programs

W01–W07 do not run as a single sweep. Each program is a gate: if the
previous one does not reject its H0, it makes no sense to interpret the next —
functional adaptation (W01) is a precondition for ecology, evolution,
culture or open-endedness to mean something other than noise:

```
WORLD v1            W01, W02
────────── GATE ──────────
WORLD Ecology v1    W03, W06
────────── GATE ──────────
WORLD Evolution v1  W04
────────── GATE ──────────
WORLD Culture v1    W05
────────── GATE ──────────
Open-endedness      W07
```

W07 does not run just because it is technically possible; it runs only after
crossing the previous barriers.

## 9. World Constitution and epochs

### `WorldConstitution`

Equivalent, for the world, to the constitutional fingerprint that already identifies
the organism. A `world_seed` alone does not identify a reproducible
universe across implementations or code versions; the fingerprint does:

```
WorldConstitution {
    constitution_schema_version   # versions the canonical serialization itself,
                                   # independent of lifecycle/rng
    topology_schema
    world_dimensions
    field_laws_hash          # hash of world-ground-truth.toml, fields
    resource_laws_hash       # hash of world-ground-truth.toml, resources
    hazard_laws_hash         # hash of world-ground-truth.toml, hazards
    interaction_rules_hash   # resolution rule for simultaneous intents
    resolution_policy
    communication_physics
    lifecycle_contract_version
    rng_scheme_version
}

world_fingerprint = SHA256(canonical(WorldConstitution))
```

`constitution_schema_version` allows evolving the canonical form itself
(field order, hash format) without future ambiguity about whether two
fingerprints are comparable.

An execution is identified, unambiguously, by:

```
organism_constitutional_fingerprint + world_fingerprint + world_seed
+ founder_genomes
```

Two organisms with the same `world_fingerprint` and `world_seed` lived the
same constitutional universe; this is what makes W02 (same
cell, same constitution, different stochastic history) comparable across
implementations or code revisions.

### `WorldEpoch`

A world can live for months; `tick` as the sole reference identifier
stops being manageable in archiving and navigation. An epoch is a
durable, evaluator-side point that **does not restart the world**:

The durable record of an epoch is identity, not interpretation —
a semantic event like "first reproduction" is a human label that
Observatory displays, never the normative identifier of the scientific
artifact:

```
world_id, epoch, start_tick, trigger_event_id
```

```
Genesis
 ├ epoch=0, start_tick=0,       trigger_event_id=null      (label: "foundation")
 ├ epoch=1, start_tick=184920,  trigger_event_id=<BIRTH #…> (label: "first reproduction")
 ├ epoch=2, start_tick=…,       trigger_event_id=<DEATH #…> (label: "first extinction")
 └ ...
```

The criteria of what constitutes a new epoch (first birth, first
extinction, experimental phase change) are declared in the
`symbiont_lab` configuration, not in `symbiont_world`: the world kernel does not know that
"epoch" exists, it only produces the `WorldEvent` that the orchestrator uses to
mark it. The human label ("first reproduction") lives alongside the epoch in
apparatus metadata, never replaces `trigger_event_id` as a reference.

## 10. Scope excluded from v1

3D, pixel vision, external LLMs, rigid physics, tools,
explicit predation/combat, evolution of the world's physical laws,
procedurally unlimited ecosystems, and any explicit fitness or
quest. Out of scope because they would obscure the scientific question of v1, not
because they are forever forbidden.

## 11. Scientific question of v1

> Can a Symbiont situated in a persistent and non-semantized spatial environment
> learn environmental regularities and autonomously modify its
> perception and behavior in a way that produces better physiological
> consequences, without receiving goals, labels or reward signals from the
> evaluator?

W01–W02 operationalize it directly; W03–W07 are the questions of
subsequent versions (niche ecology, inheritance without explicit fitness,
cultural persistence, cumulative innovation) and are not addressed until v1
has implementation and at least one gate with a real result, not just the
contract described here.

## 12. Normative increment W1 — movement and local perception

W0 (implemented; see `roadmap.md` / `ORGANISM.md` Part XIII) delivered only
the structural foundation: constitution, contracts, topology, RNG, events,
state and checkpoint. No organism lives inside the world yet. This
section freezes the normative contract of W1 — the next increment, not
a revision of the invariants already frozen in §1–§9.

### Scope of W1

Exactly two capabilities on top of the W0 kernel, and nothing else:

1. **Local perception per organism.** Phase 4 of the tick (§5,
   `local observation surfaces per organism`) starts producing a
   real `WorldObservation` per organism, populated solely with `signals`
   derived from the occupied cell (`WorldBody.occupied_cell`, §7) and its
   immediate neighborhood (`interaction_radius`). Without `fields` or `resources`
   yet: W1 can synthesize placeholder signals (e.g. a
   single opaque signal "local occupancy") solely to exercise the
   `ObservableSource → WorldObservation` pipeline end-to-end. The real laws
   of fields/resources remain deferred to W2 (Genesis ground truth, §7).
2. **Movement resolution.** Phase 8 of the tick
   (`resolve movement`) consumes each organism's `WorldAction.move`,
   invokes `HexTopology.resolve_move` (already implemented in W0) and
   `OccupancyGrid.move`/`occupy` (already implemented in W0) to update
   `WorldBody.occupied_cell`. The resolution of simultaneous intents over the
   same target cell follows the §5 rule (deterministic, namespaced RNG,
   never dependent on iteration order).

Explicitly outside of W1: any real `field`/`resource`/`hazard`,
`acquire`/`sample` with physiological effect, communication (`emit`/`reception`),
contact (`ContactEvidence`) beyond crude occupancy, and any of
the W01–W07 gates (they require, at minimum, W2).

### Ownership unchanged

W1 does not modify the ownership table of §5: `symbiont_world.WorldKernel`
continues producing `WorldObservation` and consuming `WorldAction` without knowing
`symbiont`; `symbiont_lab` continues being the sole orchestrator that invokes
sensor sampling, cognition and decision of the organism between both phases.

### Technical gates of W1 (implementation, not scientific falsification)

Just as W0 had technical gates (package boundary, atomicity, etc., see
`ORGANISM.md` Part XIII), W1 is accepted only if it demonstrates:

```
observation pipeline end-to-end   # WorldBody → signals → WorldObservation,
                                    # without real fields/resources yet
movement resolution correctness    # HexTopology + OccupancyGrid already
                                    # correct in W0, now connected to
                                    # WorldAction.move per tick
simultaneous move determinism      # two organisms attempting the same
                                    # target cell: reproducible result
                                    # byte by byte for the same seed
tick atomicity preserved            # an inconsistent movement resolution
                                    # still aborts the complete tick
                                    # (§3, inv. 7), not just the
                                    # affected organism's movement
no ground-truth leakage in signals  # W1's synthetic placeholder
                                    # is as opaque as any real
                                    # W2 field (SignalId, not name)
```

No falsification gate (W01–W07, §8) runs in W1: they still require at
least one real `field`/`resource` (W2) so that "improving the physiological
trajectory" (W01) has content to measure.

## 13. Normative increment W2 — Genesis laws (fields and resources)

W1 (implemented) only exercised the pipeline with a synthetic occupancy
signal. W2 introduces the first real Genesis laws (§7), still
without touching hazards, physiology or `symbiont_lab`.

### Why the kernel can know the laws without breaking §2

`symbiont_world` still imports nothing. The resolution to the apparent conflict
between "the kernel executes `field propagation`" (phase 2 of the tick, ownership
`symbiont_world.WorldKernel`, §5) and "the real meaning lives in apparatus metadata
inside `symbiont_lab`" (§3 inv. 1, §7) is this separation:

```
FieldLaw / ResourceLaw    →  generic numeric parameters, without domain
                              name (amplitude, bias, angular frequency,
                              phase; capacity, renewal rate, decay
                              rate) — lives in symbiont_world.laws,
                              part of the pure kernel
GroundTruth                →  opaque FieldId/ResourceId -> Law map,
                              built and injected by symbiont_lab from
                              world-ground-truth.toml; symbiont_world never
                              reads TOML nor knows the file path
semantic label              →  ("this models moisture") lives solely in
("this models moisture")        separate apparatus metadata inside
                              symbiont_lab, never even reaching
                              GroundTruth
```
The kernel calculates real dynamics with real parameters; only the domain
name remains out of its reach. This preserves §3 inv. 1: even if
someone inspected the internal state of the kernel, they would not find
`"humidity"` — they would find `field.<hash>` with a generic
`PeriodicFieldLaw`.

### Scope of W2

1. **Fields.** `PeriodicFieldLaw(amplitude, bias, angular_frequency, phase)`
   evaluated at `value_at(tick)`, spatially uniform (without gradient
   yet — a real spatial gradient remains deferred to a subsequent
   increment). Phase 2 of the tick (`field propagation`) recalculates the value
   of each field once per tick.
2. **Resources.** `ResourceLaw(capacity, renewal_rate, decay_rate,
   initial_quantity)` per cell: each cell with its own resource pool,
   lazily initialized. Phase 3 of the tick (`resource
   renewal/decay`) moves each pool towards `capacity` at `renewal_rate` and
   subtracts `decay_rate`, without negatives.
3. **Acquisition.** Phase 9 (`resolve resource competition`) resolves
   `WorldAction.acquire` on the pool of the cell occupied by each
   organism. Multiple organisms in conflict for the same resource in the
   same cell are not possible yet because Genesis v1 already imposes one
   occupancy per cell (§7); the real simultaneous acquisition conflict
   only appears if co-occupancy is allowed in a future version. Therefore
   W2 implements acquisition as simple depletion of the local pool,
   leaving the proportional/lottery resolution machinery (§5) ready but
   without a forced test case until co-occupancy or remote acquisition
   exists.
4. **Real perception.** W1's `WorldObservation.signals` (only occupancy
   density) is extended with an opaque `SignalId` per active field and per
   resource present in the local cell, calculated from `GroundTruth` +
   environment state, never from domain names.

Explicitly outside of W2: hazards (left for a later increment,
just like W06's population density coupling §8), any
real physiological effect (`MetabolicLedger` still does not exist on this side of
the boundary — that is the job of `symbiont_lab`), field spatial
gradients, and communication. The W01–W02 falsification gates still cannot
run: they require a real organism, which still does not exist until
`symbiont_lab` builds the adapter (§2).

### Technical gates of W2

```
field value determinism        # same seed/tick -> same field value,
                                # without depending on evaluation order
resource renewal/decay bounds  # the pool never exceeds capacity nor drops below 0
resource acquisition depletes  # acquiring subtracts from the local pool; acquiring
  pool without going negative    more than available never leaves the pool
                                  negative
lazy per-cell initialization   # an unvisited cell does not consume memory
  is deterministic               before its first access, and its initial
                                  value is always initial_quantity
no domain semantics in state   # GroundTruth and WorldEnvironment only
                                  contain opaque FieldId/ResourceId and
                                  numeric parameters, never a domain
                                  name
signals extend, don't replace  # W1's occupancy signal continues
  W1's occupancy signal          to be produced unchanged
```

## 14. Normative increment W2.1 — density-coupled hazards

W2 explicitly deferred hazards. This increment closes them, finally
completing the Genesis v1 count (§7: 4 fields, 4 resources, 2 hazards) on
the kernel side.

### Scope

`HazardLaw(base_probability, density_coupling)` is stateless: unlike
a resource, a hazard has no pool to deplete — it is an
exposure function evaluated over the local density already calculated by
`local_observation` (§12.1) for W1's occupancy signal:

```
exposure(local_density) = clamp(
    base_probability * (1 + density_coupling * local_density), 0, 1
)
```

This is exactly the organism→world→selection coupling that W06 (§8)
needs to measure later: more local density produces more exposure,
without the kernel calling this "pollution" or any other domain
name. The exposure is exposed as another opaque `SignalId` in
`WorldObservation.signals`; it does not apply any physiological effect — that
requires the `symbiont_lab` adapter (§2) and is left out of this increment,
just as resource acquisition was left out of the effect on
the `MetabolicLedger` in W2.

### Technical gates

```
exposure is bounded in [0, 1]        # for any density and valid parameters
                                        of the law
exposure increases monotonically      # at higher local density, higher or
  with local density                    equal exposure, never lower
zero density yields base_probability  # without occupied neighbors, the exposure
                                        is exactly base_probability
hazard has no persistent pool         # unlike a resource, two
                                        consecutive calls with the same
                                        density produce the same result
                                        without accumulation effects
no domain semantics in hazard state   # HazardLaw and GroundTruth.hazards
                                        only contain opaque HazardId and
                                        numeric parameters
```

## 15. Normative increment W3 — `symbiont_lab` adapter and real scope of v1

This increment connects the kernel (W0–W2.1) to a real
`ModeledOrganismRuntime`. It is the largest one so far because it decides how to cross §2 without touching
`symbiont` — the organism is frozen at `1.0.0`
(`docs/roadmap.md`: "CAPABILITY DEVELOPMENT: FROZEN BY DEFAULT") and adding
a new `ActionKind` to it (move, sample-world) would be exactly the kind of
new capability that the freeze prohibits without an explicit review gate from
the owner. This increment does not open that door: it resolves it by reusing
already existing surfaces without modifying them.

### Discovery: v1 does not need movement or multiple founders

Rereading the gate table of §8, **W01 and W02 — the only gates that
operationalize the scientific question of v1 (§11) — do not require
movement or multiple occupancy**:

- W01 uses a single stationary Symbiont; the question is whether it improves its
  physiological trajectory against a random policy, not whether it
  displaces itself.
- W02 uses independent replicas that start from the same cell; the
  divergence it measures is of internal stochastic history, not spatial.

Movement (W1) and multiple founder placement (§7) remain
correct and already implemented in the kernel, but **fall outside the scope
of v1**: they belong to W03+ (ecology with 8 founders, §8). This reduces the
adapter to something much more tractable: one organism, one cell, without
communication or reproduction.

### How it crosses the boundary without touching `symbiont`

Three surfaces already existing in `symbiont`, without modifying any:

1. **Perception.** `DiscoveryProvider`/`ReadingProvider`
   (`symbiont/host/contracts.py`, `symbiont/host/readings.py`) are
   constructor injection protocols, already designed so that
   external platforms provide `Capability`/`SensorReading` without
   cognition knowing their origin. The adapter implements both to
   expose the opaque `SignalId`s of `WorldObservation` as if they were
   host sensors — same opacity, same boundary, different physical
   origin.
2. **Resource acquisition.** `OrganismRuntime` already accepts
   `resource_habitats: dict[str, SharedHabitat]` (`symbiont/core/runtime.py`)
   and generates an `INTAKE` opportunity for each, decided by the cognition
   itself via `autonomous_action_step()` — not by the orchestrator. The
   adapter synchronizes the `_resources` of a `SharedHabitat` per resource
   with the real pool of `WorldEnvironment` in each tick
   (`SharedHabitat.set_environment_resources`, already public) and, after the
   organism's decision, debits the real pool of `WorldEnvironment` for
   the quantity effectively consumed (`WorldEnvironment.acquire`). The
   decision to acquire remains entirely the organism's.
3. **Hazard exposure.** `OrganismRuntime.apply_environmental_damage(amount)`
   (`symbiont/core/runtime.py`) already exists exactly for this: "a bounded
   physical perturbation from the supplied habitat", `amount` bounded in
   `(0, 0.25]`. The adapter tosses a namespaced RNG coin per hazard and
   tick using `hazard_exposures()` as probability; if it hits, it applies
   a fixed quantum of damage. There is no imposition of goal or fitness — it is
   the same physical consequence that already existed for the real host,
   reused for the world.

`symbiont` does not gain any new method, type or parameter. The adapter
lives entirely in `symbiont_lab.world.adapter`.

### Scope of W3

A single organism, stationary, without communication or reproduction:

```
SingleOrganismGenesisRuntime(
    organism_id, world_seed, ground_truth, topology, start_cell
)
```

Each tick: propagates fields, renews resources of the occupied cell, synchronizes
the `SharedHabitat`s from `WorldEnvironment`, builds the
local `WorldObservation`, delivers it to the organism via the providers,
calls `runtime.tick()` and `runtime.autonomous_action_step()`, settles the
real acquisition against `WorldEnvironment`, and resolves hazard exposure.

Explicitly outside of W3: real movement (the organism never emits
`WorldAction.move`), multiple founders, communication, reproduction,
deterministic placement of founders (§7 — does not apply with a single
organism), and any mapping of the "immediate benefit with deferred damage"
of a resource (`ResourceLaw` still does not model that delayed effect;
hazard damage is the only path for real physiological damage in v1).

### Technical gates of W3

```
provider protocols unmodified          # DiscoveryProvider/ReadingProvider
                                          are implemented, never edited
no new ActionKind                      # grep of symbiont/core/behavior.py
                                          does not change
resource sync round-trips              # what the habitat consumes is
                                          debited from the real pool of
                                          WorldEnvironment, without duplicating or
                                          losing quantity
hazard damage stays within contract    # all apply_environmental_damage
                                          falls in (0, 0.25], never outside
organism death stops the run cleanly   # a dead organism does not produce
                                          phantom world ticks
full tick sequence runs without        # smoke: N ticks without unmodeled
  raising for a live organism            exception, with a real organism
```

### What remains v1, not v2

With W3, W01 and W02 (§8) can finally be preregistered and executed against
real data. Their result — whatever it is, including trivial convergence
like H0 — is what closes v1, not the existence of the adapter by itself.
