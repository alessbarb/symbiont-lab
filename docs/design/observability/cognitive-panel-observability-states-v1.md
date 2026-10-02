---
id: design.observability.cognitive-panel-observability-states-v1
title: "Cognitive Panel Observability States v1"
document_type: design
domain: observability
status: proposed
canonical: false
implementation_status: implemented
date: 2026-10-02
depends_on:
  - docs/governance/constitution.md
source_audit: research/audits/current/2026-10-02-current-state-architecture-audit.md
language: en
---

# Cognitive Panel Observability States v1

## 1. Problem

An empty or zero panel in the Workbench was read as "this capability does not
exist". The same blank could mean that the mechanism is not part of the runtime,
is switched off, is not ready, had nothing to do on this tick, or that the
telemetry that would show it is missing, old or malformed. The generative
cognition panel said "Generative resident not observed" for all of them
(issue #277).

## 2. States

Every cognitive panel resolves to exactly one of:

| State | Meaning | Presented as current |
| --- | --- | --- |
| `absent` | the runtime has no such subsystem | yes |
| `disabled` | the subsystem exists and is switched off | yes |
| `not_ready` | enabled, but cannot run yet | yes |
| `idle` | ready, no activity in the frame shown | yes |
| `empty` | it ran and produced an empty result — a valid zero | yes |
| `active` | it ran and produced content | yes |
| `unavailable` | the stream is not delivering, or the run does not report the subsystem | no |
| `stale` | the frame shown is older than the stream can vouch for | no |
| `error` | the status or the snapshot is malformed | no |

Only the first six say something about the organism. The last three say
something about the observation, and a panel in one of them never shows counters:
a zero there would read as a measurement.

## 3. Where each fact comes from

```text
organism facts ─▶ lifecycle status ─▶ telemetry ─▶ projection ─▶ Workbench classifier ─▶ panel
                  (Lab, read-only)                  (pass-through)   (pure function)
```

- **Lifecycle** (`absent`, `disabled`, `not_ready`, `idle`, `active`) is derived
  in the Lab from public organism state, never inferred by the UI.
  `symbiont_lab.observation.subsystem_status.generative_status` reads the
  subsystem's budget, registered models, last workspace and tick counters and
  publishes `cognition.generative_status` beside the snapshot.
- **`empty` versus `active`** is decided by the panel's own content test on a
  current, active snapshot.
- **`unavailable` and `stale`** come from the stream state the Workbench already
  maintains (`streamState.status`, `streamState.stale`). A frame shown on purpose
  from history (replay) is judged by its own status, not by the live stream.
- **`error`** is raised when the lifecycle value is not one of the five, or the
  snapshot is not an object. The projection passes the status through unaltered,
  including a malformed one, so the error is visible instead of becoming a blank.

Generative lifecycle reasons:

| Lifecycle | Reason | Fact |
| --- | --- | --- |
| `absent` | `runtime_has_no_generative_cognition` | the organism has no `generative_cognition` |
| `disabled` | `zero_budget` | a generative budget limit is zero |
| `not_ready` | `no_generative_model` | no model is registered |
| `not_ready` | `no_pass_yet` | no pass has run |
| `idle` | `no_pass_this_tick` | the last pass is older than the current tick |
| `idle` | `pass_without_work` | the pass ran with no transition and no model query |
| `active` | `pass_with_work` | the pass ran with work |

## 4. Implementation

- `src/symbiont_lab/workbench/web/views/shared/observability-state.js`:
  `classifyObservability` (subsystems with a lifecycle), `qualifyEmpty` and
  `applyEmptyState` (panels that show accumulated data and have no lifecycle).
  Pure functions; no DOM access in the classifier, no fetch, no write.
- **Generative cognition panel** (Mind → Atlas): uses `classifyObservability`.
  Counters appear only for a current `active` pass; the element carries
  `data-observability` with the state.
- **Development, sensory phenotype, sensory topology, learned path and body
  representation panels**: their "nothing yet" messages go through
  `applyEmptyState`, so they read as a valid empty state only while a live stream
  is delivering, and as `unavailable` or `stale` otherwise.

The Observatory and the Workbench remain passive: the status is computed from a
read of organism state on the Lab side and nothing flows back.

Runs that predate the lifecycle status still display their snapshot; without
organism facts the classifier reports `unavailable` when there is no snapshot,
rather than guessing.

## 5. Tests

`tests/unit/lab/workbench/test_observability_state.py` executes the classifier
as the browser runs it and covers every state, checks the lifecycle against real
runtimes, and checks that a malformed status reaches the Workbench unaltered.

## 6. Limits

- Only generative cognition publishes a lifecycle status. Private-model
  inference, prospective agency and executive outcome learning have panels whose
  emptiness is qualified by stream state only; giving each a lifecycle status is
  the same pattern and is not done here.
- The telemetry path that carries the status is the Physics3D one. The resident
  launcher's snapshot contract is closed and does not carry it.
- Styling is minimal: the state is exposed as text and as a data attribute.
