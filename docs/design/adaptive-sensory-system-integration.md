# Adaptive Sensory System — Integration & Migration

**Status:** proposed  
**Depends on:** `adaptive-sensory-system.md`  
**Base:** `main` @ `81ee2d72ed466f7c5d416281dbaf47868bdfc3c3`

## 1. Migration principle

The new architecture must be introduced without attributing to sensory plasticity any change caused merely by refactoring.

The first mandatory condition is:

[
Behaviour_{before} = Behaviour_{after}
]

for compatibility mode.

Therefore the first implementation introduces an `IdentitySensorySystem` where:

[
Percept(x)=x
]

before any adaptive sensory capability is enabled.

## 2. Target package structure

Add:

```text
src/symbiont/sensory/
    __init__.py
    types.py
    modalities.py
    transduction.py
    sensor.py
    system.py
    plasticity.py
    fitness.py
    checkpoint.py
    limits.py
```

Responsibilities:

- `types.py`: immutable exchange types such as `SourceObservation`, `Percept`, `SensorOutput`, `SensorLineage`.
- `modalities.py`: validated modality definitions and constraints.
- `transduction.py`: closed primitive catalogue and deterministic transduction-DAG execution.
- `sensor.py`: `SensorState`, lifecycle and individual state.
- `system.py`: `SensorySystem`, source→sensor→percept routing.
- `plasticity.py`: bounded mutation, duplication, divergence and pruning.
- `fitness.py`: allowed organism-side utility metrics.
- `checkpoint.py`: persistence, validation and migration.
- `limits.py`: hard non-learnable ceilings.

## 3. Host-layer migration

Current path:

```text
Capability
→ SensorReading
→ synthesize_percepts()
```

Target path:

```text
Capability
→ ObservableSource binding
→ RawSample
→ SensorySystem
→ Percept
```

`HostSampler` remains responsible only for acquisition.

It must not know about:

```text
SensorState
SensoryModality
sensor utility
sensor lineage
cognitive nodes
```

## 4. Rename strategy

To reduce risk:

### Phase A

Keep current types while documenting transitional semantics:

```text
SensorReading   # deprecated semantic meaning: RawSample
SenseState      # deprecated semantic meaning: SourceModel
```

### Phase B

Introduce new types and explicit adapters.

### Phase C

Migrate callers.

### Phase D

Remove old names only when:

- no downstream imports remain;
- historical checkpoints are covered;
- migration tests pass;
- Observatory no longer depends on old semantics.

A repository-wide rename must not be combined with the first adaptive-plasticity implementation.

## 5. Percept migration

`DEFAULT_PERCEPT_NAMES` ceases to be canonical for cognition.

Compatibility mode may retain legacy semantic percepts only for historical tests.

The new scientific path is:

```text
RawSample
→ identity Sensor
→ opaque Percept
```

Human aliases such as `system_load` or `storage_pressure` may survive only in projection/human metadata.

A structural test must verify that such aliases never enter:

```text
SensorySystem fitness
CognitiveGraph
SignalKnowledge
plasticity
sensor mutation
```

## 6. SourceModel migration

`SenseState` becomes functionally a `SourceModel`.

Preserved state:

```text
samples
available_samples
mean
m2
delta_ewma
last_seen_tick
```

Removed responsibilities:

```text
percept_name
sensor identity
sensor utility
```

The current `utility` derived from variability and motion must be renamed conceptually to a source-level acquisition signal such as `sampling_interest`.

A variable source may be worth sampling while a particular sensor over that source remains useless.

## 7. Sampling vs attention

Two explicit decisions exist per tick.

### 7.1 Source sampling

Inputs:

```text
SourceModel
acquisition cost
uncertainty
availability
probing pressure
```

Output:

```text
selected source_ids
```

This operates before `HostSampler`.

### 7.2 Perceptual attention

Inputs:

```text
Percept
sensor confidence
sensor cost
cognitive uncertainty
```

Output:

```text
selected percept/sense inputs
```

This operates after `SensorySystem`.

The generic `AttentionBudget` implementation may be reused internally, but the two domains must not share IDs or accounting.

## 8. Runtime tick order

Canonical order:

```text
1. discover/update ObservableSources
2. update source availability
3. allocate source sampling budget
4. HostSampler obtains RawSamples
5. update SourceModels
6. update acquisition health/cost
7. SensorySystem transduces RawSamples
8. emit Percepts
9. update SensorState health/confidence/cost
10. allocate perceptual attention
11. normalize attended Percepts
12. feed SENSE nodes
13. CognitiveGraph tick
14. resolve predictive contribution
15. update sensory fitness
16. apply bounded sensory plasticity
17. update SensorySelfModel / BodySchema
18. SignalKnowledge observes world-level signal evidence
19. checkpoint/public projection boundary
```

The precise `SignalKnowledge` call point may preserve its existing temporal contract, but transformed sensor output must never be reintroduced as if it were a new external signal.

## 9. Identity sensory bridge

The first implementation creates one fixed identity sensor per admitted source:

```text
source.A
   ↓
sensor.identity.A
   ↓
percept.A
```

Properties:

```text
one source
identity transform
fixed modality
no mutation
no duplication
no pruning
```

The resulting behavior must reproduce the previous path within the explicit tolerances already allowed by current checkpoint semantics.

This bridge becomes the permanent regression baseline.

## 10. Cognitive bridge migration

The new cognition API accepts percept-space input such as:

```text
Mapping[percept_id, float]
```

or another bounded typed equivalent.

It must not directly accept:

```text
SensorReading
Capability
source
provider
unit
```

`SENSE` node IDs are independent from source IDs.

An initial deterministic mapping:

```text
sensor_id → sense_node_id
```

is acceptable for rollout but must not prevent later many-to-many mappings.

## 11. SensoryNormalizer

`SensoryNormalizer` remains at the cognition boundary.

The distinction is normative:

```text
Sensor
    transforms information

SensoryNormalizer
    stabilizes scale for CognitiveGraph
```

Normalization does not count as sensory specialisation.

## 12. Checkpoint contract

Add a durable block:

```text
sensory_system {
    schema_version
    modalities
    sensors
    next_sensor_id
    lineage
    aggregate fitness state
}
```

Do not persist:

```text
current RawSamples
current Percepts
raw temporal histories
host semantic aliases
provider IDs as learned meaning
evaluator labels
```

Minimal temporal state needed by bounded transducers may be persisted only if it is required for functional continuity, bounded, versioned, privacy-safe and documented.

## 13. Migration from historical checkpoints

A checkpoint without `sensory_system` migrates to:

```text
sensory_system:
    modalities = default identity substrate
    sensors = deterministic identity sensors for restored known sources
```

Specialised sensors must not be reconstructed retrospectively from:

```text
SenseState
SignalKnowledge
Narrative
CognitiveGraph weights
```

No history means no acquired specialisation.

## 14. Fingerprint

Constitutional sensory capacity belongs in the effective configuration and fingerprint:

```text
sensory modality definitions
sensory budgets
primitive catalogue version
max temporal depth
max sensor complexity
plasticity ceilings
mutation bounds
```

Acquired phenotype does not:

```text
sensor states acquired during life
current source bindings
sensor age
learned utility
transient percepts
```

Rule:

> possible capacity = constitution; acquired structure = phenotype.

## 15. BodySchema migration

The current `part.sense.*` representation remains backward compatible during rollout.

The new normative meaning must become an organism-owned sensor rather than a direct capability representation.

Existing classes remain useful:

```text
health_class
confidence_class
cost_class
maturity_class
recency_class
```

Outward-only projection may link a body part to `sensor_id` and `modality_id`, while Self view remains free of platform semantics.

## 16. Observatory contract

Add a structured `sensory_phenotype` section.

Example:

```json
{
  "modalities": [],
  "sensors": [],
  "summary": {
    "active": 0,
    "immature": 0,
    "specialised": 0,
    "degraded": 0
  }
}
```

Each public sensor exposes bounded state only:

```text
sensor_id
modality_id
source_count
age_class
maturity
health_class
confidence_class
utility_class
redundancy_class
cost_class
lineage_parent_ids
downstream_count
```

Raw values and unnecessarily precise learned coefficients remain private unless a later research contract explicitly justifies them.

## 17. Observatory UI

Separate three domains visually:

```text
ENVIRONMENT
    signals/sources

PERCEPTION
    modalities
    sensors
    phenotype

COGNITION
    SENSE
    concepts
    predictors
```

Navigation:

```text
source/signal
→ sensors using it

sensor
→ source lineage
→ perceptual state
→ downstream SENSE nodes

concept
→ contributing SENSE
→ sensors
→ signals
```

All navigation remains passive.

## 18. Backward compatibility

For at least one schema version:

- older snapshots continue to load;
- missing `sensory_phenotype` means legacy/unknown, never invented sensors;
- historical replay preserves historical meaning;
- old fixtures are not silently rewritten on disk.

## 19. Implementation sequence

### Phase 1 — vocabulary boundary

- introduce source/sample types;
- semantically deprecate `SensorReading`;
- extract `SourceModel`;
- preserve behavior.

### Phase 2 — identity sensory system

- add `symbiont.sensory`;
- add `SensorySystem`;
- identity modality;
- `SensorState`;
- opaque percepts;
- checkpoint support;
- equivalence tests.

### Phase 3 — cognition boundary

- cognition consumes percepts;
- split sampling and attention;
- remove `DEFAULT_PERCEPT_NAMES` from the scientific input path.

### Phase 4 — Observatory / BodySchema

- sensory phenotype;
- traceability;
- schema compatibility.

### Phase 5 — parameter plasticity

- bounded parameters;
- initial fitness;
- maturity.

### Phase 6 — duplication/divergence/pruning

- lineage;
- competition;
- redundancy.

### Phase 7 — heterogeneous modalities

- multiple substrates;
- experimental evaluation.

### Phase 8 — multisource

- 2+ source sensors;
- dedicated limits.

### Phase 9 — inherited modality evolution

Only after scientific closure of lifetime sensory plasticity.

## 20. Regression gates

Adaptive plasticity cannot open until all are true:

1. identity-sensor mode reproduces the previous path;
2. historical checkpoints restore;
3. replay remains deterministic within the existing contract;
4. `SignalKnowledge` is unchanged by identity sensors alone;
5. `CognitiveGraph` imports no providers;
6. human semantic aliases do not enter cognition;
7. Observatory remains outbound-only;
8. resource bounds remain satisfied.

Architectural migration and new scientific capability are separate deliverables.
