---
id: design.general.adaptive-experience-replay-v1
title: "Adaptive Experience Replay V1"
document_type: design
domain: cognition
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Adaptive Experience Replay v1 (L7.2)

Status: implemented foundation.

## Goal

L7.1 made the decision to learn organism-owned. L7.2 makes the *amount* of
replay/consolidation work organism-owned as well.

The world is not advanced during model training. The same causal
`ExperienceLedger` remains the sole private replay source.

## Learning pressure

For every endogenous training plan, the organism derives two bounded pressures:

- **experience pressure** — fraction of the accumulated-new-experience trigger
  already reached, capped at 1.0;
- **contradiction pressure** — recent independently observed contradiction ratio
  of the active private model, used only after the minimum validation evidence
  gate is satisfied.

The replay pressure is:

```text
max(experience_pressure, contradiction_pressure)
```

No evaluator score, task reward, body label, locomotion target, or wall-clock
signal participates.

## Compute request

Replay pressure controls only how much bounded training work the organism asks
the substrate to execute:

```text
requested_epochs = 2 + round(6 * replay_pressure)   # 2..8
requested_steps  = 12 + round(36 * replay_pressure) # 12..48
```

The existing training authority remains an upper-bound gate and the trainer's
held-out evaluation/early stopping remain intact.

This changes computational effort, not the evidence set or the objective.

## Scientific boundary

L7.2 does **not**:

- duplicate or synthesize experience;
- oversample evaluator-selected episodes;
- insert model-generated predictions into training evidence;
- advance Physics3D while replay is running;
- modify authoritative cognition concurrently;
- assign external importance labels.

The worker remains an execution substrate. It receives the exact bounded
request authored by the organism.

## Observability

Physics3D telemetry now exposes the last organism-authored:

- replay reason;
- replay pressure;
- requested epochs;
- requested steps.

These values are passive observability only.

## Next gate

L7.3 should test whether replay improves sample efficiency under matched
experience:

- same causal experience budget;
- replay enabled vs replay-budget ablation;
- held-out predictive loss;
- spontaneous sensorimotor competence;
- time/ticks to leave undirected babbling.

The evaluator may measure these outcomes but must not feed them back as rewards
or curricula.
