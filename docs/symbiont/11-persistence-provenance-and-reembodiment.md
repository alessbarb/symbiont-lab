# Persistence, causal provenance and re-embodiment

Persistence answers “what survives?”. Provenance answers the harder question: “why does this surviving state exist?”. Symbiont treats them as related but different problems.

## Checkpoint identity

`OrganismRuntime.checkpoint()` builds the organism payload, computes a state hash and then adds checkpoint lineage metadata. The state hash explicitly excludes `checkpoint_lineage` and `runtime_provenance`; two saves of the same organism state should therefore identify the same state even if they were produced at different moments or versions.

Checkpoint lineage records the parent checkpoint hash, allowing save history to be followed without pretending that the save event itself is organism state.

## Restore

Restore must recreate mechanism-specific state while validating schema and compatibility. A successful deserialisation is not enough: restored state must continue to produce the same observable causal history from the restoration point where the contract requires that guarantee.

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

Physics3D can restore an organism checkpoint into a fresh body. When no physical state is supplied, the runtime prepares a fresh embodiment checkpoint based on the new body contract rather than pretending the previous body's state still exists. Organism identity is retained while body identity changes.

The scientifically important question for each persisted mechanism is whether it is organism-general, embodiment-specific or body-specific. The answer determines whether it should survive unchanged, survive as historical memory, require reacclimation or be reset.

### Principal sources

- `docs/design/core/causal-provenance-v1.md`
- `docs/design/embodiment/longitudinal-reembodiment-v1.md`
- `src/symbiont/provenance.py`
- `src/symbiont/core/orchestration/runtime.py::checkpoint`
- `src/symbiont_lab/observation/provenance_journal.py`
- `src/symbiont_lab/physics3d/runtime.py`
