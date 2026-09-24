# Episodic Experience Memory v2

Status: implemented replacement for v1 after Physics3D run evidence showed that
raw ExperienceRecord-shaped episodes exhausted the byte budget, produced no
recurrence, and could not address CognitiveGraph SENSE identities.

## Why v2 exists

A 4.5k-tick Physics3D run showed:

- about 2 MiB of episodic state held only a few dozen retained episodes;
- thousands of evictions occurred;
- recurrence and compaction remained at zero;
- stored episodes used raw `signal.*` vocabulary while the CognitiveGraph used
  `sensor.identity.*` nodes;
- reinterpretation and consolidated contingencies therefore remained absent.

v2 treats that as a representation failure, not a reason to increase memory.

## Separation of responsibilities

```text
ExperienceLedger
  exact causal records
  bounded raw private-model evidence
  never reconstructed from episodic memory

EpisodicExperienceMemory
  sparse cognitive families
  direct CognitiveGraph SENSE/CONCEPT identities
  compact provenance hashes
  recurrence / prototypes / exceptions / consolidation
```

The episodic layer no longer duplicates raw training records after they leave
the causal ledger.

## Cognitive projection

At experience time `PrivateModelOrganismRuntime` captures from the actual
`CognitiveBridgeResult`:

- up to 16 highest-activation SENSE node identities;
- up to 8 active CONCEPT identities;
- bounded internal physiological tokens;
- the organism's opaque action / learned primitive identity.

After the next state is observed, the causal transition outcomes are projected
to a compact effect description.

This means episodic memory and the CognitiveGraph now share the same identity
space. No post-hoc `signal.* -> sensor.identity.*` translation exists.

## Effect projection

Raw outcome tokens remain in `ExperienceLedger`. Long-horizon memory derives
only generic effect structure:

- balance of positive/negative changes;
- change spread;
- coarse change intensity;
- a bounded number of channel-direction identities;
- bounded internal outcome tokens.

Effect-family comparison weights global shape more strongly than exact channel
identity. Small continuous differences therefore need not create unrelated
episodes.

## Episodic families

An `ExperienceEpisode` in schema v2 is a recurring family, not a raw event
dump. It stores:

- stable family id;
- first/last occurrence;
- bounded independent occurrence ticks;
- action identity;
- support counts for SENSE, CONCEPT, internal and effect features;
- up to four bounded exception projections;
- up to eight compact provenance exemplars;
- bounded evidence/source ids;
- recurrence, novelty and surprise.

A prototype is reconstructed from features supported by at least 40% of family
occurrences (with bounded top-feature fallback).

## Similarity

State similarity is a weighted combination of only the components actually
present:

```text
SENSE     0.42
CONCEPT   0.28
internal  0.15
action    0.15
```

Empty categories do not contribute artificial perfect similarity.

Family admission additionally requires compatible effect shape. Retrieval uses
state only; future consequences never leak into retrieval queries.

## Prototype + exceptions

Compatible occurrences update family feature support instead of creating new
episodes. Borderline-but-compatible variants are retained as up to four
exceptions. Retrieval compares the query against both prototype and exceptions.

Thus compaction preserves variability without retaining telemetry-sized copies.

## Provenance

Each retained provenance step stores only:

- tick offset;
- original `record_id`;
- original causal `content_hash`;
- bounded evidence references;
- source kind.

The original raw context and outcomes remain authoritative only in the causal
ledger. Episodic memory cannot fabricate an old ExperienceRecord for SLM
training.

## Consolidation

A family becomes a consolidated contingency only after its retained occurrence
ticks span at least `episodic_min_consolidation_epochs` independent epochs.

The contingency exposes direct CognitiveGraph `sense_ids` and `concept_ids`.
Retrospective support enters the ordinary CognitiveBridge concept-production
path. It does not create graph nodes directly and remains non-additive with
live support:

```text
concept evidence = max(live support, retrospective support)
```

## Retrospective reinterpretation

New concepts can index old families against:

- prototype SENSE ids;
- existing CONCEPT ids;
- internal state;
- effect features;
- prior interpretations.

The family projection itself is not rewritten.

## Checkpoints and restart

`episodic_memory_schema = 2`.

Schema v1 checkpoints are migrated into compact v2 families on restore.
Pending episode state is deliberately not persisted: restart is a causal
segmentation boundary and must not join pre-restart and post-restart experience.

## Resource goals

The existing 2 MiB kernel ceiling remains in place. The design goal is that the
same budget holds hundreds of distinct compact families, with recurrent
experience increasing family recurrence rather than byte growth.

The implementation exposes:

- family count;
- pending observations;
- recurrent-family count;
- total occurrences;
- mean recurrence;
- exception count;
- checkpoint bytes;
- interpretations;
- consolidated contingencies;
- retrieval/replay counts;
- compactions / evictions;
- mean / oldest family age.

## Validation gates for the next Physics3D run

The next run should show, relative to the v1 run:

1. hundreds rather than tens of retained families under the same byte ceiling;
2. recurrent-family count > 0;
3. compaction count > 0;
4. mean recurrence > 1 for at least part of the run;
5. eviction rate materially lower;
6. consolidated contingencies > 0 once independent evidence accumulates;
7. direct CognitiveGraph SENSE ids present in episodic families;
8. reinterpretations possible as concepts develop.

Autonomous cognitive replay and motor replay remain downstream gates. v2 first
has to demonstrate useful memory structure.
