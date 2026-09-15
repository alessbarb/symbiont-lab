# PR5 — Observatory Body Schema Projection

Status: implemented for review, 2026-09-15.

PR5 closes the first complete Self-observation loop started by PR3 and PR4:

```text
sampling outcomes
      │
      ▼
  SelfModel
      │
      ▼
BodySchemaEngine
      │ export_representation()
      ▼
Observatory adapter
      │ snapshot v3
      ▼
frontend boundedBodySchema()
      │
      ▼
state.bodySchema
      │
      ▼
projectSelfSchema()
      │
      ▼
renderSelf()
```

The core research invariant is unchanged:

> Observatory may know more about a Symbiont than the Symbiont knows about itself, but it must never pretend that privileged knowledge belongs to the organism.

## Scope

PR5 transports and renders the sensory BodySchema learned in PR4.

It does not:

- add new BodySchema learning;
- infer missing body parts from topology;
- infer health from current percept quality;
- infer dependencies from CognitiveGraph edges;
- infer global integrity from cognition or safety state;
- expose the private BodySchema checkpoint salt;
- add cognitive/memory regions to Self;
- add Self geometry to the organism model.

Those remain future BodySchema phases.

## Snapshot versioning

Historical contracts remain stable.

### v1

```text
cognition   forbidden
body_schema forbidden
```

### v2

```text
cognition   required
body_schema forbidden
```

### v3

```text
body_schema required
cognition   optional
```

This is deliberate. Self-perception and structural cognition are orthogonal capabilities. A body schema must not imply cognition, and cognition must not imply a body schema.

The v3 wire field is:

```json
{
  "organism": {
    "body_schema": {
      "schema_version": 1,
      "state": "partial",
      "parts": [],
      "dependencies": [],
      "global_state": {}
    }
  }
}
```

The complete contract lives in `observatory/body_schema.schema.json`.

## Publication boundary

The resident and replay recorder may publish only:

```python
runtime.body_schema.export_representation(
    current_tick=runtime.tick_count
)
```

They must never publish:

```python
runtime.body_schema.export(...)
```

because the private checkpoint export contains the organism-local `id_salt` used to preserve opaque part identity across restart.

The adapter is a second trust boundary even though the core already provides an observer-safe representation. `_body_schema_state()` rebuilds the wire payload from an allow-list and never forwards the input object directly.

If the adapter receives a private checkpoint payload containing `id_salt`, or a structurally contradictory BodySchema, it fails closed to:

```json
{
  "schema_version": 1,
  "state": "undeveloped",
  "parts": [],
  "dependencies": [],
  "global_state": {}
}
```

It does not partially serialize questionable self-knowledge.

## Browser trust boundary

`projection/body-schema.js` is a pure zero-import module shared by live/replay flows.

`boundedBodySchema()` accepts only the closed PR4 observer contract:

- BodySchema schema version 1;
- state `undeveloped` or `partial`;
- no unknown top-level fields;
- maximum 256 parts;
- unique opaque part ids matching `part.sense.<32 lowercase hex>`;
- kind `sense` only;
- bounded integer classes;
- no dependencies;
- empty global state;
- no private salt or source capability metadata.

Malformed Self is rejected, not repaired from other Observatory state.

`bodySchemaToWire()` is the inverse used by browser replay export. It converts only already bounded internal Self state back to the v3 wire shape.

## State lifecycle

`state.bodySchema` is independent from `state.topology` and `state.cognition`.

It is cleared immediately when:

- switching live instances;
- loading a replay before the first replay snapshot is ingested.

This prevents a transient cross-individual composition where organism B is selected while Self still belongs to organism A.

During snapshot ingestion, `state.bodySchema` is assigned before `renderIndividualPerspective()` executes. Self therefore never renders one snapshot behind.

## Self projection

`projectSelfSchema()` remains pure and zero-import.

It consumes only bounded BodySchema state and emits presentation semantics:

```text
part opaque id
kind
existence ratio
health ratio
confidence ratio
cost ratio
maturity ratio
recency class/label
```

It does not read or import:

- topology;
- cognition;
- percepts;
- beliefs;
- host capability names.

A malformed input degrades to `undeveloped` rather than borrowing truth from Phenotype.

## Rendering

`renderSelf()` may read only `state.bodySchema` as organism-owned content.

The central Self view shows:

- number of self-known sensory parts;
- opaque part identity;
- existence confidence;
- health;
- confidence;
- maturity;
- cost;
- quantized recency.

It explicitly does not label the part with a host capability or topology node name. Native progress elements provide an accessible quantitative representation, and the panel remains scrollable when many parts are learned.

The external Observatory panels remain scientific instrumentation and are outside the central Self epistemic claim.

## Replay

Python replay recording publishes BodySchema via the same observer-safe core export used by live resident mode.

Browser replay import accepts v1, v2 and v3 snapshots.

Browser replay export:

- emits v3 when `state.bodySchema` exists;
- preserves the bounded Self representation;
- does not reconstruct cognition from current Observatory state;
- emits v1 when no BodySchema exists.

Thus replay cannot silently convert external Phenotype knowledge into organism-owned Self knowledge.

## Invariants

1. **Self comes only from BodySchema.**
2. **No private checkpoint salt crosses the Observatory boundary.**
3. **No raw capability id is introduced by PR5.**
4. **No topology/cognition/percept/belief fallback exists.**
5. **Malformed Self fails closed to undeveloped.**
6. **v1 and v2 retain their historical semantics.**
7. **v3 requires Self but not Cognition.**
8. **Instance/replay switches clear stale Self before rendering.**
9. **Replay preserves Self without synthesizing Cognition.**
10. **The human layout remains presentation; no geometry is written back into BodySchema.**

## Acceptance

PR5 is complete when automated/static coverage demonstrates:

- body-schema wire schema is closed and bounded;
- snapshot v1/v2/v3 gating is explicit;
- resident uses `export_representation()`;
- adapter strips/rejects private or contradictory inputs;
- browser normalizer rejects salt, unknown fields, duplicate ids, invalid classes, dependencies and >256 parts;
- `projectSelfSchema()` produces a real partial Self projection;
- malformed projector input returns undeveloped;
- `renderSelf()` reads `state.bodySchema` and no privileged phenotype state;
- BodySchema is cleared on instance/replay transitions;
- BodySchema is assigned before the individual dispatcher renders;
- browser replay can round-trip a v3 Self surface;
- historical project_tick callers without BodySchema still produce v1/v2.
