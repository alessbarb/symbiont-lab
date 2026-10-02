# Persistence, causal provenance and re-embodiment

Persistence answers “what survives?”. Provenance answers the harder question: “why does this surviving state exist?”. Symbiont treats them as related but different problems.

## Persistence products

Four different things are persisted, and they are not interchangeable:

| Term | What it is | Contains model weights? |
| --- | --- | --- |
| Runtime checkpoint | Serialized organism/runtime state | No — it references artifacts |
| Portable Symbiont bundle (`.symbiont`) | Runtime checkpoint plus the private-model artifacts it needs, with a hashing manifest | Yes |
| Body checkpoint | Body-owned physical state kept by the embodiment apparatus | Not applicable |
| Observer reconstruction | State rebuilt for display from telemetry or replay | Not organism state |

A raw runtime checkpoint is not a complete portable organism: restoring it
alone leaves an organism whose model registry names artifacts that are not
there.

## Checkpoint identity

`OrganismRuntime.checkpoint()` builds the organism payload, computes a state hash and records it as `checkpoint_lineage.checkpoint_id` together with the parent identifier and the identity scope. The hash covers the complete organism payload of the runtime that saved it — including modeled and private-model state — and excludes only `checkpoint_lineage`, `runtime_provenance` and the embodiment history the apparatus writes around the organism. Two saves of the same organism state therefore identify the same state whenever and under whatever version they were taken.

Restore verifies that identity on the payload exactly as it was loaded, before any migration, and fails closed on a mismatch. An authorized transform that legitimately produces a different state — re-embodiment, temporal decontamination, adopting canonical cognition — re-identifies the result: the new identifier chains from the one it replaced and names the transform, so an intended change is recorded rather than being indistinguishable from corruption.

Checkpoints saved by schema 10 and earlier carried an identifier that covered only base-runtime fields and was never checked. They are accepted without verification and migrate as before. That acceptance is recorded: every later save of such an organism carries `checkpoint_lineage.unverified_legacy_origin`, so a verifiable chain always says whether it begins at an unverified checkpoint. Uses that need a verified origin — confirmatory and held-out runs — refuse such organisms; the policy and its review point are in [Lifecycle Continuity Contract v1](../design/core/lifecycle-continuity-contract-v1.md) §6.1. The list of authorized transforms an organism has been through (`checkpoint_lineage.transforms`) is carried forward the same way instead of existing only on the transformed payload.

Bundle integrity is a separate contract: the bundle manifest proves the packaged bytes match, the checkpoint identity proves the accepted organism state matches its recorded save.

## Continuity classes

Every runtime field has exactly one continuity class, recorded with its owner, checkpoint field, restore path and re-embodiment behaviour in `src/symbiont/host/continuity.py` and validated against the live runtimes by its test:

- `MUST_PRESERVE` — acquired state that survives a same-organism restart intact.
- `MUST_RESET` — transient process state that must not cross a process boundary, because carrying it would fabricate continuity that did not occur.
- `MAY_RECOMPUTE` — a deterministic projection of preserved state.
- `MUST_REAPPLY_CONFIG` — apparatus configuration, recorded as provenance and reapplied before the organism resumes.
- `MUST_INVALIDATE_AUTHORITY` — knowledge survives but current execution authority is withdrawn.

## Restore

Restore must recreate mechanism-specific state while validating schema and compatibility. A field may be absent only when the schema that saved the checkpoint predates it or a documented migration defines the absence. A checkpoint saved by a current runtime that lacks a required field is rejected: loss must not silently become a healthy empty subsystem.

Runtime-only switches that shape future learning — cognitive plasticity, predictor promotion, kernel limits, the executive admission policy — are not organism state. Their effective values are recorded in `runtime_provenance.session_controls` and reapplied on restore; a continuation that runs with different values is recorded as a changed condition, not as restart equivalence.

Restore has two entry points with different meanings. `OrganismRuntime.from_checkpoint` is the historical restore: it reproduces the individual exactly as saved, including the absence of cognition in a checkpoint that predates it. `restore_resident_with_canonical_cognition` is the owner-facing restore used by the CLI and the resident launcher for every runtime layer: when genome and graph are absent it adopts the canonical ones and records the `canonical-cognition-adoption` transform. The same checkpoint can therefore yield two different organisms; a longitudinal experiment must choose the entry point deliberately.

### What a restart does and does not guarantee

A restart is not a biological event: the restored organism has exactly the state that was saved. Its *future*, however, is not identical to never having stopped, for two deliberate reasons:

- one-tick causal traces do not cross a process boundary, so the transition spanning the restart is never recorded and cognition has no previous-tick activations for its first update;
- every restore opens the organism-owned reacclimation gate, which pauses structural consolidation for a bounded number of ticks.

Inventing either would bridge a causal consequence that never happened in the restored timeline. Identity, genome, models, social knowledge and communication state are unaffected.

## Causal provenance

`src/symbiont/provenance.py` defines a transversal model built from `CausalRef` and `CausalEvent`. Every event can name a subject, immediate causes, produced references, the applied rule and bounded scalar parameters. Event identity is content-derived.

The organism keeps a bounded recent ring plus a frontier for live references. The frontier is checkpointed, so a currently live state can remain locally explainable even after old ring events have rolled out. Durable history belongs to the laboratory's append-only journal and is outward-only: it must never feed causal information back into the organism.

This distinction is essential:

```text
checkpoint state preservation
    != complete causal history preservation
```

The checkpoint can preserve the immediate causal frontier of live state without containing the laboratory's entire historical journal.

## Re-embodiment

Physics3D can restore an organism checkpoint into a fresh body. When no physical state is supplied, the runtime prepares a fresh embodiment checkpoint based on the new body contract rather than pretending the previous body's state still exists. Organism identity and organism time are retained while body identity changes.

Restart and re-embodiment are different contracts. On re-embodiment the Symbiont's own state — cognition, sensory learning, self-model, body schema, experience, private models, social knowledge — is preserved exactly. Body-owned physiology comes from the fresh Body, the previous `EmbodimentEpisode` is closed and archived, and current-Body execution authority is withdrawn: learned competences survive as knowledge, their execution bindings do not. Any adaptation to the new Body must be acquired through ordinary experience.

This is mechanical continuity. It says nothing about whether the retained knowledge helps in the new Body.

The reduced seed used by the clean-embodiment studies (`symbiont.core.orchestration.symbiont.Symbiont`, moved between Bodies by `Individual.transplant_to`) follows a different contract: it keeps identity, organism time, genotype and expression, restarts BodySchema, sensorimotor dynamics, causal evidence, controllability and agency from naive, and keeps competences without their effect grounding. The difference is declared per attribute in `REDUCED_SEED_REGISTER` and checked by its test. A result obtained with one semantics does not transfer to the other. The full table of lifecycle operations is in [Lifecycle Continuity Contract v1](../design/core/lifecycle-continuity-contract-v1.md).

Historical runs whose Body age was taken from the global tick can have that clock coordinate corrected when the legacy state makes it unambiguous. The correction is recorded, and it never claims to undo the senescence, wear or energy consequences already produced under the contaminated clock.

### Principal sources

- `docs/design/core/causal-provenance-v1.md`
- `docs/design/embodiment/longitudinal-reembodiment-v1.md`
- `docs/design/core/longitudinal-integrity-v1.md`
- `src/symbiont/provenance.py`
- `src/symbiont/host/continuity.py`
- `src/symbiont/host/checkpoint.py`
- `src/symbiont/core/orchestration/runtime.py::checkpoint`
- `src/symbiont_lab/observation/provenance_journal.py`
- `src/symbiont_lab/physics3d/runtime.py`
