# Emergent Sensory Modalities v1

**Status:** proposed / preregistration design
**Precondition:** Sensory Plasticity v1 closed in declared scope
**Purpose:** remove predeclared modality families and test whether distinct perceptual organizations emerge from a generic bounded receptor substrate.

## 1. Problem

Sensory Plasticity v1 proves autonomous receptor evaluation, selection, null rejection and regime reversal inside a designed search space. It does not prove emergent modalities.

Current designer priors remain:
- host SensorReading is scalar;
- modality.alpha, modality.beta and modality.gamma predeclare different transform families.

Therefore alpha->difference, beta->integrate and gamma->mix are adaptive choices inside a supplied taxonomy, not evidence that a modality emerged.

## 2. Scientific hypothesis

Starting from generic sample geometry, a common bounded primitive catalogue and no preassigned modality classes, a Symbiont can construct and retain different receptor organizations because they provide different causal predictive value in different environments.

Stronger hypothesis: receptor populations form reproducible functional clusters whose occupancy changes with environmental structure even though those clusters were not declared in the genome.

## 3. Core decision

modality_id stops being constitutional state for new receptors.

Canonical path:

    WORLD/HOST -> ObservableSource -> RawSample[geometry] -> ReceptorProgram -> Percept -> SENSE -> CognitiveGraph

A receptor owns sensor identity, source bindings, a bounded transduction program, parameters, temporal state, health, confidence, utility, selection credit, cost, lineage and maturity.

It does not own a designer-supplied modality class.

## 4. Generic RawSample geometry

New canonical envelope:

    source_id
    geometry
    values
    shape
    timestamp
    unit
    quality
    privacy_class

Geometry kinds are structural, never semantic:
- scalar: one finite numeric value;
- vector: fixed-width bounded tuple;
- event: sparse bounded occurrence;
- sequence: bounded ordered samples;
- field: small bounded N-dimensional grid.

Migration opens scalar first and vector second. Event, sequence and field remain closed until the generic machinery is validated.

Raw payloads are ephemeral. Checkpoints may persist receptor structure, bounded aggregate statistics, learned parameters, lineage and cold-start state, but not raw previous samples, field contents, sequences, provider labels or evaluator targets.

## 5. ReceptorProgram

A receptor is no longer one TransductionKind. It owns a small typed acyclic program represented purely as data.

Hard ceilings remain non-learnable: maximum nodes, inputs, graph depth, fan-in, temporal storage, mutations per window and checkpoint bytes.

No eval, callbacks, generated source code, dynamic bytecode or plugin execution are introduced.

## 6. Common primitive kernel

All receptors draw from the same primitive catalogue. Primitive availability is constrained only by geometry compatibility and hard kernel limits, never by modality.

Initial kernel:
- INPUT
- IDENTITY
- ABS
- CLIP
- DIFFERENCE
- EMA
- THRESHOLD
- MEAN
- WEIGHTED_SUM
- NORM

The kernel defines the physics of the digital sensory body. Organisms may compose primitives but cannot invent new executable primitive semantics in v1.

## 7. Structural plasticity

Allowed typed mutations:
- parameter_adjust
- duplicate_receptor
- insert_primitive
- remove_primitive
- rewire_edge
- bind_source
- unbind_source
- change_output
- prune_receptor

Every mutation commits atomically only if the graph remains acyclic, geometry-compatible and inside node/depth/fan-in/source/temporal/cost/checkpoint limits.

Mutation lineage keeps mutation_id, tick, sensor_id, parent_ids, kind, pre_digest, post_digest and cost. Raw sample values never enter mutation history.

## 8. Exploration and selection

The organism must not enumerate the whole graph space.

Development maintains a bounded nascent pool, explores around useful receptors while retaining a minimum exploration rate, gives new structures a grace period and uses the already validated predictive-credit mechanism for survival/pruning.

Incremental structural credit is required: a larger child must improve on its parent enough to justify its added cost. Positive utility alone is insufficient.

Evaluator labels never instruct which primitive, source combination or topology to build.

## 9. What counts as an emergent modality

A modality is not stored in SensorState.

For v1, a derived modality is an evaluator-side recurrent cluster of receptors that are similar in both structure and function.

Allowed clustering signature:
- input geometry;
- source cardinality;
- graph topology;
- temporal depth;
- primitive occupancy;
- response timescale;
- cross-source integration;
- functional ablation profile;
- cost profile.

Forbidden clustering inputs:
- human source names;
- target labels;
- environment labels;
- expected transform names;
- sensor IDs.

Clustering happens after development and never feeds back into the organism. Organism-side modality grouping is deferred to a separate future design.

## 10. Observatory

Observatory remains passive and uses an explicit four-layer visual boundary:

    WORLD / SIGNALS
          -> organism-owned RECEPTORS
          -> downstream COGNITION
          -> evaluator-derived modality interpretation

The current implementation exposes a dedicated Sensory Map perspective. It
shows opaque world signal bindings, current receptor state, substrate class,
transduction, maturity, utility, selection credit, cost, lineage and downstream
identity. It also draws discovered relations among external signals separately
from receptor lineage so world structure is not confused with body structure.

During migration, legacy `alpha/beta/gamma` are labelled as **current
predeclared substrate classes**, not as emergent modalities.

When ReceptorProgram lands, the same view extends with geometry, program node
count/depth and primitive occupancy. Any derived cluster id is
evaluator/phenotype-only and must never appear in Self view as organism
knowledge.

## 11. Migration sequence

Stage A: wrap every legacy scalar SensorReading as scalar RawSample and prove exact compatibility.

Stage B: represent each current one-step transform as a one-node ReceptorProgram. This is representation only, not a new scientific result.

Stage C: remove alpha/beta/gamma restrictions from new development. All receptors share the same primitive kernel. Legacy modality_id remains migration metadata only.

Stage D: open bounded insert/remove/rewire structural mutations after equivalence and replay are green.

Stage E: open vector geometry only after scalar structural discovery is validated.

## 12. Preregistered studies

### M01 — scalar program equivalence
One-node ReceptorProgram must reproduce the current scalar sensory path without regression.

### M02 — modality-label ablation
Remove alpha/beta/gamma from development while preserving the common primitive catalogue. Autonomous selection and regime reversal must remain positive.

### M03 — structural discovery
Use an environment whose useful relationship requires a two-step transform unavailable as a prebuilt receptor. Compare frozen one-node, random structural mutation, adaptive structural mutation and evaluator-only oracle best. Adaptive must beat frozen and random without evaluator feedback.

### M04 — structural ablation
Remove one internal primitive or edge from a selected multi-node receptor. Targeted ablation must degrade function more than matched same-cost ablation.

### M05 — complexity control
Use an environment where one node is sufficient. Adaptive development must not systematically grow deeper graphs without incremental utility.

### M06 — vector geometry
Expose an opaque bounded vector where no scalar component alone is sufficient. Adaptive receptor construction must beat scalar-only and frozen generic controls without component semantics.

### M07 — derived modality formation
Develop receptor populations from the same constitution across at least three environments. After development, freeze evaluator-side clustering.

Positive evidence requires:
1. more than one reproducible receptor cluster;
2. cluster identity uses no source/environment labels;
3. cluster occupancy or contribution changes with environment;
4. targeted cluster ablation gives environment-specific degradation;
5. random/frozen controls do not reproduce the effect;
6. separation exceeds preregistered null permutations.

Only M07 may close Sensory Modalities v1.

### M08 — same-world ontogeny
Repeat the same latent world with protocol-authorized microexperience differences. Convergence and divergence are both valid characterization outcomes.

## 13. Closure criteria

Emergent Sensory Modalities v1 closes only if:
1. scalar compatibility remains intact;
2. removing predeclared modality labels does not destroy autonomous plasticity;
3. at least one useful multi-node receptor is autonomously constructed;
4. its internal structure has causal support by ablation;
5. complexity controls reject gratuitous graph growth;
6. at least one non-scalar geometry works without component semantics;
7. multiple derived receptor clusters appear reproducibly;
8. cluster contribution depends on environment;
9. random/frozen/null controls do not explain clustering;
10. cost, checkpoint and replay remain bounded;
11. Observatory remains passive;
12. no evaluator or human semantic label enters organism-side learning.

Only then is the warranted claim:

> Symbiont developed distinct functional perceptual modalities from a generic bounded sensory substrate rather than receiving those modality classes from the designer.

## 14. Explicit non-claims

Even after closure this does not establish biological senses, consciousness, qualia, semantic recognition of the host, unrestricted self-programming, arbitrary code synthesis, universal representation learning or open-ended evolution.

## 15. Deferred

Until M01-M07 justify expansion, keep closed: event/sequence/field geometry, recurrent receptor programs, invention of new primitives, executable learned code, inheritance of acquired receptor programs, cross-organism receptor transfer, cultural transmission of sensory programs, organism-side modality naming, semantic grounding of modality clusters and active host action.

## 16. Architectural boundary

Target:

    generic world sample
            -> generic bounded receptor substrate
            -> developmental structural exploration
            -> organism-side predictive credit + cost/redundancy
            -> percept population
            -> derived functional organization

Not:

    designer chooses modality -> organism tunes it

That distinction is the scientific boundary between Sensory Plasticity v1 and Emergent Sensory Modalities v1.
