# PR6 — Learned Cognitive Regions and Functional Dependencies

Status: implementation contract, 2026-09-15.

Implements the final PR in the six-PR sequence from
`docs/design/digital-body-schema-and-emergent-morphology.md` (§6, §10
Phase B/C, §31 Phases 5–6, §36).

PR6 extends the organism-owned BodySchema created in PR4 and transported by
PR5. It must not collapse Phenotype truth into Self knowledge.

## Research invariant

> CognitiveGraph topology is administrative truth. BodySchema cognitive
> regions are learned hypotheses about internal organization.

Therefore this is forbidden:

```python
body_schema.parts = cognitive_graph.nodes
body_schema.dependencies = cognitive_graph.edges
```

The BodySchema must never receive graph node ids, graph edges, topology
revisions, or arbitrary references to `CognitiveGraph`.

## Evidence boundary

`CognitiveBridge` already produces one bounded dynamic activation result per
organism tick. A pure core projector converts only that dynamic frame into a
bounded organism-internal observation before BodySchema sees it:

```text
CognitiveBridgeResult.activations
    │ dynamic activation only
    ▼
project_cognitive_self_observation()
    │ opaque channels only
    ▼
CognitiveSelfObservation
    │
    ▼
BodySchemaEngine
```

A cognitive self observation contains at most 32 currently active internal
channels. Each channel has only:

```text
channel_id      opaque internal evidence handle
activity_class  integer 1..15
```

The projector domain-separates and hashes the implementation node id before
the BodySchema boundary. Raw node ids never enter BodySchema. These channel
tokens are deliberately **not observer identity**: they may exist in the
private BodySchema learning checkpoint, but are never included in
`export_representation()` or Observatory. Public cognitive-region identity is
separately generated with the organism-private BodySchema salt, so two fresh
organisms do not expose a shared `part.region.*` identity merely because their
internal implementation once used the same node name.

This design deliberately avoids extending the CognitiveBridge checkpoint just
to store observer-invisible evidence aliases.

Only non-sensory activity may become a cognitive self channel. The runtime
filters every developed sensory identity — active or dormant — before the
projection. Mere graph existence is not evidence: inactive nodes are not
reported.

## Region learning

BodySchema keeps bounded, decaying support for observed opaque channels and
for their repeated coactivity.

A cognitive region may be created only after a channel has accumulated
repeated activity evidence. Strong repeated coactivity may group still-
unassigned eligible channels into a coarse region. A learned region has
longitudinal identity: later coactivity between two already-established
regions does **not** merge them. Instead it becomes evidence for a functional
relationship. An unassigned channel may join an established region only after
repeated coactivity evidence with that region.

This rule is important because an implementation that automatically merged
all later-coactive regions would destroy the very entities between which PR6
needs to learn `co_acts_with` and `precedes`.

Public region identity is organism-local and opaque:

```text
part.region.<32 lowercase hex>
```

The observer never receives private channel membership.

Region public fields are:

```text
part_id
kind = cognitive_region
existence_confidence_class 0..15
confidence_class           0..15
activity_class             0..15
maturity_class             0..7
recency_class              0..4
```

A cognitive region does not invent `health_class` or `cost_class`; PR6 has no
organism-owned evidence for those semantics.

Sensory parts keep the PR4 fields unchanged.

## Dependency learning

Dependencies are learned between cognitive regions only in PR6.

Allowed relation kinds:

```text
co_acts_with
precedes
```

`co_acts_with` is symmetric and stored with canonical endpoint ordering.
`precedes` is directed.

No graph edge is imported as a BodySchema dependency. In particular PR6 does
not claim `supports`, causality, inhibition, gating or predictive semantics.

For every candidate relation BodySchema tracks:

```text
support_count
opportunity_count
```

and derives:

```text
support_class    bounded evidence volume
confidence_class support / opportunity
```

A dependency is exported only after minimum repeated support and minimum
confidence. Evidence remains revisable: repeated opportunities without
support can lower confidence until a relation disappears from the exported
Self representation.

Temporal state used to infer `precedes` is intentionally ephemeral. The set
of regions active on the immediately preceding tick is **not checkpointed**.
After restore it starts empty, so a process restart cannot fabricate a
`precedes` relation across a discontinuity in execution.

## Bounds

```text
sensory parts                  <= 256
cognitive regions              <= 32
total public parts             <= 288
exported dependencies          <= 256
active cognitive channels/tick <= 32
```

Candidate/evidence state is also bounded. No raw activation history is stored.
The maximum dependency-candidate space is deliberately sized for at most 32
regions and remains within the existing 2 MiB plastic-checkpoint ceiling.

## BodySchema versioning

PR6 moves the BodySchema contract to schema version 2.

### v1

Historical PR4/PR5 contract:

```text
sense parts only
dependencies empty
global_state empty
```

### v2

```text
sense + cognitive_region parts
co_acts_with / precedes dependencies
global_state still empty
```

`BodySchemaEngine.restore()` must accept v1 checkpoints and migrate them
without changing existing sensory part identity. New exports use v2.

Snapshot schema remains Observatory v3: snapshot version means “Self is
present”; `body_schema.schema_version` evolves independently inside that
surface. Historical v3 replays carrying BodySchema v1 remain valid.

`developed` remains unreachable in PR6. The complete digital body still lacks
global physiology/integrity, so the schema remains `partial` whenever any
part is known.

## Checkpoint-private state

The BodySchema checkpoint may additionally retain bounded private learning
state needed for longitudinal cognition:

```text
region opaque channel membership
region evidence counts
candidate channel/coactivity support
dependency support/opportunity counts
```

None of those private fields may cross `export_representation()`.

The immediately-previous active-region set is not persistent for the temporal
reason described above. Legacy v1 checkpoints contain no cognitive learning
state and restore with empty cognitive learning state.

## Runtime integration

Within one organism tick:

```text
CognitiveBridge dynamic result
    ↓
project_cognitive_self_observation(...)
    ↓
CognitiveSelfObservation

sampling / second-look
    ↓
SelfModel evidence
    ↓
BodySchema.observe_self_model(...)

CognitiveSelfObservation
    ↓
BodySchema.observe_cognition(...)
```

`OrganismRuntime` may pass only the projected `CognitiveSelfObservation`, not
the graph and not the raw activation mapping itself. During cognition failure
or runtime reacclimation, no cognitive self evidence is consolidated.

If cognition is absent or produces no internal activity, the sensory body
continues unchanged.

## Observatory

PR5's snapshot v3 remains the transport.

`body_schema.schema.json`, `projection/body-schema.js`, the adapter and replay
logic accept both BodySchema v1 and v2.

Self rendering adds explicit sections:

```text
Sensory parts
Cognitive regions
Functional dependencies
```

Dependencies are textual/structural, not Euclidean organism geometry. The
renderer may assign local human labels such as “Cognitive region 3”, but those
labels are presentation only and are never written back to Symbiont.

Self still reads only `state.bodySchema`. There is no topology/cognition/
percept/belief fallback.

## Acceptance

PR6 is complete when tests demonstrate:

- raw cognitive node ids never appear in `CognitiveSelfObservation`;
- opaque channel tokens are stable for repeated dynamic observations;
- inactive graph nodes are not handed to BodySchema merely because they exist;
- sensory identities, including developed dormant senses, are excluded from cognitive channels;
- repeated internal activity can consolidate at least one opaque region;
- transient activity below threshold does not create a region;
- established regions retain identity when they later coactivate;
- repeated coactivity can learn `co_acts_with`;
- repeated lagged activation can learn `precedes`;
- graph edges alone do not create dependencies;
- dependency confidence can fall when unsupported opportunities accumulate;
- region/dependency bounds hold under churn;
- v1 BodySchema checkpoints restore without changing sensory ids;
- v2 checkpoint round-trip preserves learned regions/dependencies;
- restart cannot create `precedes` from pre-restart activity;
- observer export contains neither private salts nor cognitive channel ids;
- Observatory accepts BodySchema v1 and v2 in snapshot v3;
- Self renders cognitive regions/dependencies without reading Phenotype data;
- `global_state` remains empty and `developed` remains unreachable.
