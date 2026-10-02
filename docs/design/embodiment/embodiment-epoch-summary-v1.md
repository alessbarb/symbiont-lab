---
id: design.embodiment.embodiment-epoch-summary-v1
title: "Embodiment Epoch Summary V1"
document_type: design
domain: embodiment
status: proposed
canonical: false
implementation_status: partial
migrated_on: 2026-09-25
last_reviewed: 2026-10-02
language: en
---
# Embodiment Epoch Summary v1

**Status:** proposed observational-contract delta; not a parallel embodiment architecture.
**Base architecture:** [Embodiment v2](embodiment-v2.md).
**Scope:** observer-owned summaries of closed embodiment episodes.

This design remains active because core/Embodiment v2 and Physics3D have distinct
summary records, persistence paths, and consumers. Their overlap does not yet
constitute one adopted cross-runtime contract. This document specifies the
small residual contract to reconcile them; it does not authorize runtime work
or an experiment.

## 1. Ownership and authority

A summary is an observational record about a closed embodiment. It has no
authority over Symbiont identity, cognition, memory retrieval, decisions, action
selection, or scientific interpretation. It is not a substitute for raw
telemetry or a claim that retained knowledge is useful.

## 2. Common minimum contract

Every runtime implementing this contract records, where observable:

| Field | Meaning |
| --- | --- |
| `epoch` | Stable episode ordinal/identifier within the owning history. |
| `contract_fingerprint` | Fingerprint of the embodied contract, not a claim of morphological equivalence. |
| `started_at_symbiont_tick`, `ended_at_symbiont_tick` | Inclusive/exclusive boundaries must be specified consistently by the runtime; unknown boundaries remain unknown. |
| `duration_body_ticks` | Physical age accumulated by this Body during its lifetime, ending at closure. It is not global Symbiont time. |
| `end_reason` | Directly observed lifecycle outcome. Use `unknown` when the reason is not uniquely established; do not infer cause from correlation. |
| `body_vital_state` | Observed terminal state, without inferred causal explanation. |
| `body_schema_state` | Observer-facing schema/state summary, not a sensory or cognitive input. |
| `reacclimation_summary` | Episode-local reacclimation measurements, when the runtime records them; absence is explicit, not zero. |

Runtime-specific extensions (for example physiology, work, or private-model
state) are permitted only with documented definitions and provenance. They are
not silently promoted to common fields.

### Duration semantics

`duration_body_ticks` and `embodiment_ticks` are not aliases. Body duration is
physical age for one Body and continues across a same-body resume; it resets
for a fresh Body. `embodiment_ticks` is episode-local active coupling time. A
runtime must not substitute one for the other. If a legacy record cannot
establish either value, preserve it as unknown rather than deriving it from
Symbiont ticks.

`terminal_facts` is optional. Include it only for directly observed terminal
conditions that add information beyond `end_reason`; do not encode inferred
causes or grow unstructured strings to carry causal claims.

## 3. Existing persistence and retention

The current implementations remain runtime-specific:

| Runtime | Record / persistence | Current bounded retention |
| --- | --- | --- |
| Core / Embodiment v2 | `EmbodimentEpisodeSummary` in `EmbodimentArchive` | Up to 32 summaries (`max_summaries`). |
| Physics3D | `embodiment_epoch_summaries` in Physics3D state | Up to 16 summaries. |

These paths and limits are not a unified persistence contract. The proposed
common checkpoint policy is to retain **at least the 16 most recent closed
summaries** in each runtime. A runtime may retain more (core currently retains
up to 32); this contract does not require truncating existing history. This
minimum is not uniformly validated across both paths. Older summaries are not
guaranteed to survive in a checkpoint. Any external evidence archive is
separate and must preserve its own provenance; checkpoint retention must not
be described as complete bodily history.

## 4. Schema and derivation provenance

Before cross-schema comparison is implemented, serialized records must
distinguish summary format from source checkpoint format. The proposed names
are `summary_schema_version`, `summary_revision`, and
`derived_from_checkpoint_schema`:

- `summary_schema_version` identifies the summary record format;
- `summary_revision` identifies a correction/re-derivation of that summary;
- `derived_from_checkpoint_schema` records source checkpoint schema when known.

Do not silently rewrite historical values. Unknown source schemas stay unknown;
revision history must be explicit where records are corrected. The existing
runtime field names/versions remain as-is until a separately authorized
migration defines compatibility.

## 5. Passive-observation acceptance boundary

Implementation of this contract requires a boundary test showing summary
serialization/persistence is not consumed by sensory input, cognition, memory
retrieval, the action selector, or organism identity/authority. A source-level
dependency assertion or equivalent focused test should fail if a summary becomes
an operative input. No such test or unified boundary is claimed by this
proposal; it is residual work, not authorization to change runtime code.

## 6. Relationship to prior designs

Embodiment v2 is the architectural base; Physics3D is a runtime-specific
extension. This design covers only the observational summary delta. It does not
supersede [Longitudinal Re-embodiment v1](longitudinal-reembodiment-v1.md),
close its scientific questions, or establish transfer benefit. Reconsider
supersession only after the common contract, persistence/provenance behavior,
retention policy, and passive-observation boundary are adopted and evidenced.
