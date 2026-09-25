---
id: design.general.autonomous-experience-replay-v1
title: "Autonomous Experience Replay V1"
document_type: design
domain: cognition
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Autonomous Experience Replay v1 (L7.1)

Status: implemented foundation.

## Goal

Increase learning per unit of embodied experience without giving the organism
semantic goals, evaluator rewards, body labels, or a laboratory-authored
training schedule.

The canonical Physics3D organism already owns a bounded `ExperienceLedger`
containing causal private transitions of the form:

```text
state(t) + action(t) -> independently observed state(t+1)
```

L7.1 reuses that existing ledger. It does **not** introduce a second episodic
memory.

## Ownership boundary

The organism owns:

- the causal experience ledger;
- the decision that enough new experience has accumulated to justify learning;
- the decision that independently validated model contradictions justify
  revision;
- the exact corpus selected for training;
- tokenizer construction;
- architecture/objective/requested-work request;
- metabolic opportunity cost of requesting training;
- the watermark preventing repeated requests over the same experience.

The substrate/laboratory owns only:

- whether compute is currently available;
- execution of the already-authored bounded `TrainingRequest`;
- artifact storage;
- independent held-out evaluation and promotion gate;
- attaching an accepted artifact through the existing typed inference bridge.

The laboratory must never create a training request when the organism returned
no learning plan.

## Endogenous triggers

The current constitutional policy is deliberately small and bounded.

### Bootstrap

Without an active private model, at least 64 independently observed temporal
transitions are required before a first request can be emitted.

### Revision

With an active model, a new request can be emitted when either:

1. at least 96 new causal transitions have accumulated since the last request;
   or
2. at least 32 new transitions have accumulated, at least 8 recent independent
   model validations exist, and the contradiction ratio in the bounded recent
   validation window is at least 0.35.

These are organism-side constitutional learning conditions, not evaluator
success criteria. They contain no task name, movement target, semantic sensor
label, locomotion objective, or external reward.

## Anti-self-confirmation

Only records satisfying all of the following may enter the replay/training
corpus:

- record id is a true `transition.*`;
- epistemic status is `OBSERVED`;
- source is not `MODEL`.

Model proposals and validation records remain in the ledger for audit and for
the endogenous revision trigger, but never become training examples for their
own successor.

## Incremental demand accounting

Demand checks run in O(1) during ordinary ticks.

The organism maintains bounded/incremental counters for:

- total causal transitions;
- causal transitions since the last request;
- latest causal-transition tick;
- recent supported/contradicted model validations.

Only when a gate is satisfied is the bounded ledger scanned to materialize the
actual corpus.

## Compute substrate semantics

Physics3D checks for organism-authored demand every completed cognition tick.
The local worker may defer service if another job is running or the substrate
cooldown is active.

A faster machine may therefore satisfy requests sooner and spend more wall-clock
compute on the organism without injecting knowledge into it.

The authoritative organism/cognition state remains single-threaded. Training
executes in the existing external process worker and returns only through the
existing artifact/evaluation/adoption boundary.

## Checkpoint continuity

The private learning watermark and bounded validation window are checkpointed.
Restoration therefore cannot reinterpret already-consumed experience as newly
accumulated evidence.

A checkpoint predating L7.1 is initialized conservatively:

- if an active model already exists, historical transitions are treated as
  already seen for scheduling purposes;
- without an active model, existing causal transitions remain eligible for a
  bootstrap request.

## Non-goals

L7.1 does not yet add:

- prioritized replay;
- learning-progress curiosity;
- counterfactual imagination;
- hierarchical skill planning;
- concurrent mutation of the authoritative cognitive graph;
- externally supplied rewards or curricula.

Those belong to later L7 stages and must build on this ownership boundary.
