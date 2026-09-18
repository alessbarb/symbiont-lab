# Adaptive Sensory System

**Status:** proposed  
**Base:** `alessbarb/symbiont-lab` `main` @ `81ee2d72ed466f7c5d416281dbaf47868bdfc3c3`  
**Scope:** source/signal/sensor/percept separation, sensory modalities, perceptual phenotype and cognition boundary  
**Supersedes:** nothing  
**Extends:** `docs/design/percepcion-y-embodiment.md`, `docs/design/cognicion-y-plasticidad.md`

## 1. Decision

Symbiont will stop treating an observable host capability as if it were a sense owned by the organism.

The canonical architecture distinguishes:

```text
WORLD / HOST
    │
    ▼
ObservableSource
    │ produces
    ▼
RawSample
    │ consumed by
    ▼
SensorySystem
    │
    ├── SensoryModality
    │       └── Sensor
    │
    ▼
Percept
    │
    ▼
SENSE node
    │
    ▼
CognitiveGraph
```

Normative boundaries:

> A source belongs to the environment.  
> A sensor belongs to the organism.  
> A percept belongs to the organism's experience.  
> A `SENSE` node belongs to cognition.

The following identities are explicitly forbidden as architectural invariants:

```text
source_id == sensor_id
signal_id == sensor_id
sensor_id == SENSE node id
1 source == 1 sensor
1 sensor == 1 cognitive representation
```

A compatibility implementation may temporarily use 1:1 cardinality, but it must not encode that cardinality as part of the permanent contract.

## 2. Current-state reconciliation

### `src/symbiont/host/contracts.py`

`Capability` currently represents “one sense a host can offer”. Under this design it is interpreted as an observable host surface:

```text
Capability ≈ ObservableSource
```

It is not an organism-owned sensory organ.

`CapabilityKind` remains acquisition-apparatus metadata. It is not semantic knowledge available to cognition.

### `src/symbiont/host/readings.py`

`SensorReading` currently represents a physical sample emitted by providers. Its future semantic meaning is:

```text
SensorReading ≈ RawSample
```

The name must be deprecated progressively because `Sensor` will become a separate organism-owned entity.

### `src/symbiont/host/percepts.py`

The current semantic mapping such as:

```text
compute.logical_cpu -> system_load
storage.disk_usage  -> storage_pressure
```

must no longer be the canonical scientific path into cognition.

Human-facing aliases may remain in apparatus or Observatory metadata, but they must never influence sensor selection, plasticity, `CognitiveGraph`, sensory fitness or `SignalKnowledge`.

### `src/symbiont/host/adaptive.py`

`SenseState` is a learned statistical description of one discovered source. Its normative responsibility becomes that of a `SourceModel`.

`SensoryRelation` currently relates capabilities and therefore remains a relation between sources, not between organism-owned sensors.

### `src/symbiont/core/attention.py`

`AttentionBudget` is generic enough to reuse, but the system will distinguish:

```text
source sampling allocation
```

from:

```text
perceptual/cognitive attention
```

### `CognitiveGraph`

`SENSE` nodes will consume percepts rather than physical sources.

## 3. Terminology

### 3.1 ObservableSource

A stable opportunity for observation offered by the apparatus.

Minimum conceptual fields:

```text
source_id
private capability binding
availability
acquisition metadata
```

It has no cognitive utility, plasticity, modality, learned meaning or organism-owned parameters.

Its existence does not imply that the organism is currently perceiving it.

### 3.2 RawSample

One observation produced by an `ObservableSource`.

```text
RawSample {
    source_id
    value
    unit
    monotonic_timestamp
    quality
}
```

`RawSample` is apparatus-owned and ephemeral.

Raw values are not persisted as durable sensory history beyond aggregate forms already allowed by existing contracts.

### 3.3 Signal

`signal.<opaque-id>` remains the organism-local epistemic identity through which the organism can accumulate knowledge about an observable source:

```text
ObservableSource
      ↓ private identity boundary
signal.<opaque-id>
```

`SignalKnowledge` continues to describe properties of the observed world. It does not describe properties of sensors.

### 3.4 SensoryModality

A modality is a family of possible transduction, not a human category such as vision, hearing or smell.

```text
SensoryModality {
    modality_id
    substrate_kind
    max_inputs
    temporal_capacity
    primitive_set
    complexity_ceiling
    cost_model
    plasticity_bounds
}
```

Different modalities must be structurally capable of different function families:

[
\mathcal{F}_A \neq \mathcal{F}_B
]

Two instances of the same function with different parameters are not sufficient to count as different modalities.

### 3.5 Sensor

A persistent, organism-owned and potentially plastic entity.

```text
SensorState {
    sensor_id
    modality_id
    source_ids
    transduction
    parameters

    born_tick
    age_ticks
    maturity_state

    health
    confidence
    utility
    redundancy
    acquisition_cost
    transduction_cost

    parent_sensor_ids
    structural_revision
}
```

Metric meanings remain separate:

- `health`: functional reliability of the apparatus.
- `confidence`: organism-side confidence in its output.
- `utility`: demonstrated downstream contribution.
- `redundancy`: information already supplied by other sensors.
- `cost`: acquisition and transduction resources.

`utility` must never be derived directly from `health`.

### 3.6 Percept

The result of applying a sensor to one or more `RawSample` values.

Initial contract:

```text
Percept {
    sensor_id
    value
    uncertainty
    quality
}
```

A later vector form is allowed:

```text
Percept {
    sensor_id
    channels[]
    uncertainty[]
}
```

Percepts do not carry human semantic names derived from capabilities.

### 3.7 SENSE node

A `SENSE` node is cognition's input boundary.

It consumes percepts, not sources.

The permanent architecture allows many-to-many mappings:

```text
sensor.01 ─┐
sensor.07 ─┼── SENSE.21
sensor.11 ─┘
```

and:

```text
sensor.04 ── SENSE.32
          └─ SENSE.91
```

The first rollout may preserve 1:1 wiring for compatibility, but this must not become a kernel invariant.

## 4. Ownership boundaries

### Apparatus-owned

```text
providers
Capability
ObservableSource
RawSample
provider identity
unit
platform semantics
human aliases
```

### Organism-owned

```text
opaque signal identity
SourceModel
SensorySystem
SensoryModality expression
SensorState
Percept
sensory lineage
sensory self-model
```

### Cognition-owned

```text
SENSE
CONCEPT
STATE
PREDICTOR
GATE
READOUT
```

### Evaluator-owned

```text
ground truth
experimental labels
cross-treatment fitness comparisons
human interpretation of emerging sensor function
```

Evaluator-owned information must never feed into organism decisions.

## 5. Sensory modalities

The first version will expose a small closed set of structurally different substrates without programming their meaning.

Illustrative differences:

```text
modality.alpha
    max_inputs = 1
    short temporal depth
    cheap high-frequency response

modality.beta
    max_inputs = 1
    deeper temporal state
    stronger integration/decay

modality.gamma
    bounded multi-channel mixing
    moderate temporal depth
    higher transduction cost
```

The organism never receives labels such as “fast”, “integrative” or “multichannel”; these are evaluator descriptions only.

The modality constrains what sensors may become. It does not determine which sources they consume.

## 6. Closed transduction primitive set

Sensors do not execute generated Python or arbitrary expressions.

The kernel exposes a closed primitive catalogue. Initial recommendation:

```text
input
delay
weighted_sum
difference
integration
decay
normalize
threshold
saturate
inhibit
mix
```

Each transducer is a validated bounded DAG.

Example:

```text
source.x(t)
 ├───────────────┐
 │               ▼
 │            delay(1)
 │               │
 └──── difference┘
         │
      normalize
         │
       output
```

This may behave like a change detector without any semantic type called `ChangeDetector`.

Rules:

- bounded operation count;
- bounded depth;
- bounded number of inputs;
- no arbitrary recursion;
- no dynamic loops;
- no callbacks;
- no imports;
- no direct host access;
- deterministic execution under identical state and input;
- fully structural serialization.

## 7. Sensory phenotype

The organism's expressed modalities, sensors, acquired parameters, lineages and functional relations constitute its `SensoryPhenotype`.

Two organisms with the same genome may therefore develop:

[
P_A \neq P_B
]

even while sharing the same available sources.

This is an explicit target capability, not an accidental implementation effect.

## 8. Sensor lifecycle

Minimum lifecycle:

```text
nascent
→ immature
→ established
→ specialised
```

Alternative paths:

```text
immature → unproductive → pruned
established → redundant → pruned
established → degraded
degraded → recovered
```

A newly created sensor cannot count immediately as mature evidence. A minimum maturation period is required.

Pruning must not be based only on instantaneous utility.

## 9. Duplication and divergence

A useful sensor may create a bounded variant:

```text
sensor.17
    ↓ duplicate
sensor.42
```

The copy preserves lineage:

```text
parent_sensor_ids = ["sensor.17"]
```

Initially:

[
S_{42}\approx S_{17}
]

then bounded mutation may drive divergence.

After evaluation:

- both survive if they contribute complementary information;
- the new sensor may replace the old if materially superior;
- the new sensor is pruned if redundant or useless;
- both may persist after functional divergence.

## 10. Sensory fitness

The organism does not receive a “good sensor” label.

Fitness is built only from causally available organism-side information:

```text
predictive contribution
downstream contribution
information novelty
reliability
redundancy
resource cost
```

Abstract form:

[
F_s =
aP_s +
bD_s +
cN_s +
dQ_s -
eR_s -
fC_s
]

Initial coefficients are declarative kernel/genome parameters and must not be tuned retrospectively against study outcomes.

Predictive contribution should use ablation or incremental comparison where possible, not raw correlation.

## 11. Budgets

`SensorySystem` has independent hard limits:

```text
max_modalities
max_active_sensors
max_nascent_sensors
max_sources_per_sensor
max_transduction_nodes
max_temporal_depth
max_sensor_mutations_per_window
max_sensor_checkpoint_bytes
```

Total cost is conceptually separated:

[
C_{total}
=
C_{acquisition}
+
C_{transduction}
+
C_{attention}
]

Existing `CapabilitySamplingOutcome` continues to measure acquisition. The sensory layer adds transduction cost. Cognitive attention remains separate.

## 12. Plasticity stages

Capability is opened sequentially:

```text
Stage 0  identity sensors
Stage 1  parameter adaptation
Stage 2  duplication
Stage 3  parameter divergence
Stage 4  transduction DAG mutation
Stage 5  source rewiring
Stage 6  multi-source receptors
Stage 7  modality divergence/evolution
```

Each stage requires independent validation before the next becomes part of canonical studies.

## 13. Source knowledge vs sensory self-knowledge

`SignalKnowledgeEngine` continues to own:

```text
knowledge about external signals
```

It will not own:

```text
sensor utility
sensor lineage
sensor health
sensor redundancy
sensor maturity
```

Those belong to a new `SensorySelfModel`, integrated with the existing `SelfModel` / `BodySchema` where appropriate.

Therefore:

[
K_{world} \neq K_{perception}
]

## 14. BodySchema

The current `part.sense.*` representation must progressively move from capability-derived parts to organism-owned sensor parts.

Existing fields remain useful:

```text
health_class
confidence_class
cost_class
maturity_class
recency_class
```

Part identity must derive from the sensor rather than directly from `capability_id`.

BodySchema does not export platform semantics, raw values or aliases as organism self-knowledge.

## 15. Cognition boundary

Final invariant:

> `CognitiveGraph` consumes percepts and never directly consumes `Capability`, provider metadata or `RawSample`.

Canonical path:

```text
ObservableSource
 → RawSample
 → Sensor
 → Percept
 → SensoryNormalizer
 → SENSE
 → CognitiveGraph
```

The current `SensoryNormalizer` remains a cognition-boundary stabilizer. It is not itself a sensor and does not count as sensory specialisation.

## 16. Traceability

The scientific apparatus must reconstruct:

```text
CONCEPT
  ← SENSE
  ← Percept
  ← Sensor
  ← signal.<opaque-id>
  ← ObservableSource
```

This genealogy is outward-only and may never become a command/control path from Observatory.

## 17. Inheritance

V1 separates:

```text
genetic sensory capacity
```

from:

```text
lifetime sensory phenotype
```

The genome may encode:

- available modalities;
- sensory budgets;
- limits;
- plasticity rates;
- structural predispositions.

V1 does not inherit:

- acquired sensors;
- learned source bindings;
- acquired transduction parameters;
- percept history.

Inheritance of acquired sensory structure is deferred.

## 18. Non-goals

This design does not:

- create human senses;
- claim phenomenal experience or consciousness;
- assign semantic meaning to signals;
- use an LLM/SLM to decide perception;
- allow generated code execution;
- permit unbounded sensor growth;
- turn correlation into function;
- introduce host action;
- weaken existing safety boundaries.

## 19. Architecture acceptance gate

The architecture is minimally valid when it can stably represent:

```text
1 source
→ 2 sensors
→ 2 distinct percept streams
→ 2 SENSE inputs
```

without duplicating the external source or changing the meaning of `SignalKnowledge`.

Two sensors over the same `signal_id` must be able to differ in:

```text
modality
parameters
cost
utility
lineage
```

Only then can Symbiont be said to possess a sensory apparatus distinct from its observable sources.
