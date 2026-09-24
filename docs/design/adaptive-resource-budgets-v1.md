# Adaptive Resource Budgets v1

Status: implemented.

## Purpose

Symbiont must remain finite, but fixed cardinalities must not define how far an
organism can develop. This design separates three different concepts that were
previously conflated:

```text
genome developmental budget
        ↓
initial phenotype / inherited starting capacity

adaptive runtime budget
        ↓
capacity the individual has actually developed

kernel / organism safety ceiling
        ↓
owner-controlled resource and serialization protection
```

A safety ceiling is not evidence that the organism has reached its natural
developmental limit.

## Cognitive graph

The genome still supplies `soft_node_budget`, `soft_edge_budget`, and
`sense_node_budget`. They are birth budgets.

`CognitiveBridge` now owns persistent adaptive node, edge and sense budgets.
When valid structural demand remains blocked at the current developmental
budget, capacity expands in bounded steps. Expansion never exceeds
`KernelLimits`.

Current kernel safety ceilings:

- nodes: 768
- concepts: 192
- edges: 6144
- tentative edges: 512
- structural mutations per consolidation: 16

Physics3D still starts at 192 nodes / 1536 edges / 128 senses. Existing
organisms therefore do not suddenly materialize extra structure; they earn
additional capacity only when endogenous evidence produces demand.

Adaptive budgets are checkpointed and exposed in Physics3D telemetry as
`node_budget`, `edge_budget`, and `sense_budget`.

## Longitudinal causal learning

`ExperienceLedger` remains a recent exact causal window. Evicted observed
transitions are now offered to `HistoricalExperienceArchive`, a deterministic
content-addressed reservoir.

The archive is bounded by both:

- record-count safety ceiling: 8192 by default;
- exact payload budget: 8 MiB by default.

Private-model corpora reserve space for recent live records and fill remaining
capacity with exact cross-lifetime archive samples. Episodic memory remains a
separate compact cognitive representation and never fabricates raw training
records.

Historical causal records are acquired lifetime state and are explicitly not
inherited by offspring.

## Motor development

Motor chunks already use similarity-based recurrence through
`_matched_primitive_sequence`. The old flat cardinalities could nevertheless
truncate a mature repertoire. They are now high safety ceilings:

- materialized primitives: 256
- primitive statistical families: 512
- horizon statistics: 2048
- effect relations per actuator candidate: 256

Evidence and recurrence remain the admission gates.

## Sensory and self-model development

Fixed low sensory cardinalities were raised to safety ranges while plasticity
continues to govern actual development:

- active sensors: 256
- nascent sensors: 32
- modalities: 16
- sources/sensor: 16
- transduction nodes/sensor: 32
- temporal depth: 256

Cognitive self-observation capacity is now derived from
`OrganismLimits.max_cognitive_channels_per_tick` rather than a duplicate
literal constant.

## Private model lineage

The private model registry starts at 64 records and can be configured up to
1024. Retired records are still reclaimed under pressure.

Model-generation counters no longer stop at generation 256. The remaining
2^31-1 bound is serialization protection, not a developmental target.

## Episodic memory

Episodic memory remains governed primarily by its 2 MiB byte budget. Flat
safety ceilings were raised so they are less likely to become the first
constraint:

- families: 4096
- records in one pending episode: 32
- retrieval candidates: 64
- replay items: 16
- interpretations/family: 128

The sparse v2 family representation remains intentionally compact.

## Persistence

Because graph plasticity, historical causal evidence and other learned state
can now legitimately exceed the old aggregate checkpoint size, host persistence
is protected by a higher 32 MiB safety ceiling. Subsystems retain their own
smaller budgets.

## Invariants

1. World/lab truth never expands a budget. Expansion reacts only to organism
   structural demand already admitted through normal evidence paths.
2. Kernel safety ceilings remain owner-controlled and non-learnable.
3. Developmental budget expansion is persistent across checkpoint/restore.
4. Old checkpoints without adaptive-budget state restore from their inherited
   genome budgets.
5. Increasing capacity never grants concepts, primitives, sensors, or models;
   it only removes an artificial cardinality blockade. Normal evidence gates
   still decide what is learned.
6. Acquired causal history is not inherited.
