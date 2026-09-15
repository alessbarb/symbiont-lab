# PR4 — Sensory Digital Body Schema

Status: implemented for review, 2026-09-15.

Implements Phase 4 of `docs/design/digital-body-schema-and-emergent-morphology.md` and follows PR3's Phenotype/Self perspective seam. PR4 is an organism-side change only: it creates learned sensory self-structure but does **not** yet publish it through Observatory. Publication/rendering remains PR5.

## Research objective

The organism should begin to learn a bounded answer to:

> Which sensory functions appear to be persistent parts of me, and how are those parts doing?

PR4 must not answer that question by copying administrative runtime truth. In particular, CognitiveGraph nodes, topology, provider metadata and the host manifest are not BodySchema evidence.

The sole evidence source in PR4 is the existing `SelfModel.export()` representation. That evidence is already organism-owned, bounded and quantized:

- cost class;
- health class;
- confidence class;
- maturity class;
- recency class.

Therefore the PR4 flow is:

```text
sampling outcomes
      │
      ▼
  SelfModel
      │ bounded/quantized evidence
      ▼
BodySchemaEngine
      │
      ├── private durable checkpoint
      └── observer-safe self representation (not wired until PR5)
```

## Scope

PR4 learns only `SENSE` body parts.

It does not learn:

- cognitive regions;
- memory regions;
- readout regions;
- functional dependencies;
- self/environment boundary membership beyond the learned sensory-part set;
- causal relations;
- organism identity/lineage;
- geometry.

Those remain later phases.

Consequently the only reachable BodySchema states in PR4 are:

```text
undeveloped  — no sensory parts have enough SelfModel evidence yet
partial      — at least one sensory part has been learned
developed    — unreachable until later BodySchema phases define completion
```

## Part representation

Each learned sensory part exports:

```json
{
  "part_id": "part.sense.<opaque-id>",
  "kind": "sense",
  "existence_confidence_class": 0,
  "health_class": 0,
  "confidence_class": 0,
  "cost_class": 0,
  "maturity_class": 0,
  "recency_class": 0
}
```

All quantities remain discrete. PR4 introduces no raw readings or continuous host telemetry.

`existence_confidence_class` is not an independent privileged signal. It is a deterministic rescaling of SelfModel maturity onto the existing 16-class confidence vocabulary: maturity is the evidence that a sensory function has persisted long enough to be represented as part of the self.

## Opaque identity

A raw host capability id must never become a BodySchema `part_id`.

A fixed unkeyed hash is also insufficient because equal capability ids would become linkable between organisms. Each `BodySchemaEngine` therefore owns a random 128-bit private identity salt, persisted only in its durable checkpoint.

Conceptually:

```text
private per-organism salt + sense_id
              │
              ▼
            SHA-256
              │
              ▼
part.sense.<128-bit opaque id>
```

Properties:

- stable for one organism across ticks and checkpoint restore;
- different between independently created organisms even for the same source sense id;
- source capability id never appears in the BodySchema representation;
- private salt never appears in the observer-safe representation.

## Persistence vs observation API

The API intentionally separates two exports:

```python
BodySchemaEngine.export(current_tick=...)
```

is the **private durable checkpoint** shape. It includes the private `id_salt` required to preserve part identity after restart.

```python
BodySchemaEngine.export_representation(current_tick=...)
```

is the **observer-safe organism-owned representation** intended for PR5. It never includes `id_salt` or source capability ids.

This separation is a hard boundary: PR5 must consume `export_representation()`, not `export()`.

No host checkpoint schema-version bump is required. `body_schema` is a core subsystem namespace added by `OrganismRuntime`, like other runtime-owned namespaces. Historical checkpoints without the key restore a fresh undeveloped BodySchema and can learn it again from the restored SelfModel on subsequent ticks.

## Recency semantics

The presence of an entry in `SelfModel.export()` does not itself constitute fresh sensory evidence. SelfModel can continue exporting an established but idle sense.

When BodySchema consumes SelfModel evidence, it reconstructs a conservative representative `last_evidence_tick` from SelfModel's quantized `recency_class`. Repeated projection of the same stale entry therefore does not rejuvenate the body part.

## Longitudinal bound

`MAX_BODY_PARTS = 256` is a lifetime bound, not merely a per-tick input bound.

SelfModel itself is bounded, but a persistent BodySchema could otherwise accumulate more than 256 old parts as the sensory repertoire changes over time. When the persistent set exceeds the bound, pruning is deterministic and retains, in order:

1. freshest evidence;
2. stronger existence/maturity evidence;
3. stronger confidence;
4. stable lexical `part_id` tie-break.

This is self-model memory pressure, not evidence that a pruned part never existed.

## Global sensory-body summaries

PR4 exports only two derived summaries:

```text
self_model_confidence_class
integrity_class
```

They are the rounded means of the retained parts' confidence and health classes respectively. They introduce no new evidence source and are recomputed from parts.

Future physiology fields such as stress, maintenance load, dormancy pressure or viability are not fabricated in PR4.

## Runtime integration

`OrganismRuntime` owns one `BodySchemaEngine`.

Within a tick, all ordinary and second-look sampling outcomes update `SelfModel` first. Only after those updates does BodySchema consume:

```python
self._self_model.export(current_tick=self._tick_count)
```

No manifest, topology, CognitiveGraph or provider object is passed to the engine.

Checkpoint flow:

```text
runtime.checkpoint()
  └── body_schema = BodySchemaEngine.export(...)

runtime.from_checkpoint()
  └── BodySchemaEngine.restore(...)
```

Historical checkpoint without `body_schema`:

```text
restore → undeveloped BodySchema → next tick → learns from restored/current SelfModel evidence
```

## Invariants

1. **No administrative introspection.** BodySchema receives only SelfModel export evidence in PR4.
2. **No raw capability names in the representation or checkpoint part records.**
3. **No cross-organism stable part identifiers.** Fresh organisms use different private salts.
4. **No false freshness.** Reprojecting a stale SelfModel entry cannot rejuvenate it.
5. **Bounded for the organism lifetime.** Persistent parts never exceed 256.
6. **No fabricated dependencies.** `dependencies` is always empty in PR4 and non-empty checkpoint dependencies are rejected.
7. **No premature completion.** `developed` is rejected until later phases define what completeness means.
8. **Observer export cannot contain the private identity salt.**
9. **Old checkpoints remain loadable.** Missing `body_schema` means undeveloped, not error.
10. **Geometry remains Observatory-only.** BodySchema stores no coordinates or visual shape.

## Acceptance

PR4 is complete when tests demonstrate:

- fresh BodySchema is undeveloped;
- established SelfModel evidence creates opaque sensory parts;
- same organism/sense keeps stable identity;
- separate organisms do not share part ids for the same source sense;
- health/confidence/cost/maturity/recency stay quantized;
- stale evidence is not rejuvenated;
- cumulative sense churn remains bounded;
- checkpoint round-trip preserves private identity namespace and learned parts;
- observer representation omits the salt and raw source ids;
- historical checkpoints without BodySchema restore cold and learn later;
- runtime learns BodySchema through SelfModel evidence alone;
- dependencies and `developed` remain unavailable in this PR.

## Explicit PR5 hand-off

PR5 may add an Observatory wire schema and adapter projection, but it must project only:

```python
runtime.body_schema.export_representation(current_tick=runtime.tick_count)
```

It must not serialize the private checkpoint export, and it must not reconstruct missing Self data from topology/cognition/percepts/beliefs.
