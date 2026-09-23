# Episodic Experience Memory v1

Status: implemented foundation and runtime integration.

## Purpose

Symbiont previously had two partial mechanisms:

- `ExperienceLedger`: bounded causal transition evidence for private-model learning;
- `MemoryConsolidator`: durable coarse regularities that intentionally discard recent detail.

Neither allowed the resident organism to retrieve a past experience because its
current state resembles a previous state. v1 adds a resident, bounded,
reinterpretable episodic layer without replacing the CognitiveGraph or the
private causal ledger.

## Architecture

```text
working dynamics
      |
      v
ExperienceLedger  -- immutable causal evidence
      |
      v
EpisodicExperienceMemory
      |  retrieval / reinterpretation / cognitive replay
      v
consolidated contingencies
      |
      v
CognitiveGraph / private predictive models
```

The factual core of an episode contains only organism-native opaque tokens
already present in `ExperienceRecord`. No Physics3D state, evaluator label,
world coordinate, anatomical label or semantic target is admitted.

## Invariants

1. Only `transition.*`, `OBSERVED`, non-`MODEL` records become lived episodes.
2. Model predictions and validations can never self-confirm through episodic memory.
3. Episode observations are immutable. Later concepts are stored as revisable
   interpretations, never by rewriting the factual core.
4. Consolidation requires support from independent temporal epochs.
5. Retrieval and prediction never execute actions.
6. Cognitive replay reactivates compact episode representations only; v1 has no
   autonomous motor replay.
7. Memory is bounded by `KernelLimits`.
8. Under pressure, redundant episodes are compacted before low-information
   exceptions are evicted.
9. Checkpoint restore fails closed on malformed or cross-organism state.
10. Observatory/Physics3D receives aggregate metrics only and has no memory-control path.

## Kernel limits

- `max_episodic_episodes`
- `max_episodic_episode_records`
- `max_episodic_retrieval_candidates`
- `max_episodic_replay_items`
- `max_episodic_checkpoint_bytes`
- `episodic_epoch_ticks`
- `episodic_min_consolidation_epochs`

These are kernel-owned ceilings, not learnable genome fields.

## Episode segmentation

A new episode begins when generic temporal evidence indicates a boundary:

- discontinuous tick range;
- passive/action regime transition;
- major context discontinuity;
- action identity change;
- hard episode-record ceiling.

No world-specific or locomotion-specific boundary is used.

## Retrieval

`retrieve(context_tokens, action_token, k)` ranks old episodes by similarity of
present organism-native context to stored initial/terminal context. Retrieval
counts are used only as a retention signal under memory pressure.

## Retrospective reinterpretation

`reinterpret(representation_id, support_tokens)` can associate a newly learned
opaque concept with old episodes. The episode core remains byte-for-byte
unchanged. Runtime integration derives support only from CognitiveGraph concept
lineage.

## Consolidation

Episodes are grouped by opaque action/effect signatures. A contingency is
materialized only after evidence spans at least
`episodic_min_consolidation_epochs` independent epochs. Context is represented
by recurrent organism-native tokens; no evaluator semantics enter.

Consolidated episodic co-occurrence is projected back into the normal
CognitiveGraph concept-formation path only for SENSE nodes already known by the
organism. Replay does not create graph nodes directly and cannot bypass
structural arbitration.

Live coactivation support and retrospective episodic support are maintained as
separate evidence channels. Concept birth uses:

```text
max(live_support, retrospective_support)
```

rather than their sum, preventing the same lived event from being counted twice.
Retrospective support is idempotent and can be retried safely when previously
unknown senses are later admitted to the graph.

## Cognitive replay

`cognitive_replay(...)` reconstructs compact internal episode representations
for retrieval/learning experiments. It cannot invoke actuators or select a
primitive.

## State-conditioned prediction

`predict_from_experience(context, action)` estimates consequences from similar
lived episodes. This is the precursor to the later:

```text
current state
-> retrieve
-> predict
-> autonomous action
-> observe
-> update
```

The action step remains intentionally absent in v1.

## Persistence

`episodic_memory_schema = 1` is checkpointed by
`ModeledOrganismRuntime.checkpoint()`. Pending not-yet-closed causal records are
also persisted, preventing checkpoint timing from changing episode boundaries.

## Passive telemetry

Physics3D `rich_state` exposes only aggregate metrics:

- episode count;
- pending record count;
- compressed episode count;
- interpretation count;
- consolidated contingency count;
- retrieval/replay counts;
- compaction/eviction counts;
- oldest/mean episode age.

## Scientific assay

`episodic_memory_utility.py` performs a held-out comparison between:

- state-conditioned episodic prediction;
- action-only outcome frequency;
- global outcome frequency.

This is observer-only. The scores never cross into the organism.

The key falsifiable gate is:

```text
P(outcome | current internal state, action, retrieved experience)
    >
P(outcome | action)
```

on held-out causal experience.

## Explicit non-goals

v1 does not add:

- walking, locomotion or displacement reward;
- target position or target velocity;
- manual primitive choice;
- evaluator-selected replay;
- motor replay;
- world/lab control over memory;
- semantic labels inside episodic state.
