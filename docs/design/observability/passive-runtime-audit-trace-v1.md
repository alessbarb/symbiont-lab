# Passive Runtime Audit Trace v1

**Status:** Proposed design; not approved for implementation.  
**Scope:** Read-only diagnostic trace for generative-cognition reconciliation and embodied energy trajectories.  
**Roadmap relationship:** Candidate supporting work for A9 only after owner acceptance; it does not amend the canonical roadmap or authorize a scientific/mechanism change.

## 1. Problem

Existing organism bundles preserve useful snapshots and bounded experience history, but they do not necessarily preserve the event-level joins needed to answer:

1. Which prospective predictions were later executed, and why did each factual outcome reconcile or fail to reconcile?
2. How did physical energy, resource costs, replenishment, homeostatic response and vitality evolve before a Body became dormant or died?

In the examined organism, the retained data show private-SLM hypotheses targeting `primitive.*`, action outcomes carrying `command.*` identifiers, and zero GC comparisons. The bundle does not preserve enough provenance to attribute every unreconciled hypothesis to execution, identity, model, transition, or retention-window causes. Similarly, the final Body checkpoint establishes energy depletion but not its per-tick causal trajectory.

This design addresses missing observability only. It does not presume that either observed outcome is a defect.

## 2. Goals and non-goals

### Goals

- Preserve causal provenance across prediction, intention, commitment, command, transition, factual outcome and reconciliation.
- Record per-tick energy and physiological transitions with explicit coverage and missing-data markers.
- Keep the trace outside organism state and prevent it from influencing organism behavior.
- Make the artifact bounded, versioned, attributable to an exact run and usable for post-run audits.
- Distinguish observed non-matches from events that cannot be evaluated due to missing or expired evidence.

### Non-goals

- Repair or change Generative Cognition, Executive Intention, motor selection, physiology, or energy accounting.
- Add success thresholds, scientific acceptance criteria, or roadmap milestones.
- Turn generated predictions into factual evidence.
- Recover historical identity links or per-tick energy data absent from existing artifacts.
- Add an Observatory/UI dependency or import from `symbiont` into `symbiont_lab`.

## 3. Design principles

1. **Observe after the fact.** The recorder receives immutable event snapshots after the source operation has completed. No organism decision may read from it.
2. **Preserve identities.** Store original IDs exactly as emitted. Never rewrite `command_id` as `competence_id`, infer one from the other, or use string similarity as a causal join.
3. **Record relations explicitly.** Where a source event contains both IDs, write a typed relation linking them with the source event reference.
4. **Absence is not a negative observation.** Missing rows, expired hypotheses and truncated windows produce `unknown`/coverage states, not claims that an action did not occur.
5. **Factual authority stays canonical.** Only the existing factual path may supply observed outcomes and evidence references to the recorder. Recorder output is never fed back into reconciliation.
6. **Bounded and separate.** The trace is a sidecar artifact, not checkpoint state, organism memory, a new ledger, or an unbounded event store.

## 4. Artifact and run identity

The output is an append-only sidecar associated with one run, for example:

```text
<trace-root>/<run-id>/agency-trace.jsonl
<trace-root>/<run-id>/energy-trace.jsonl
<trace-root>/<run-id>/manifest.json
```

The exact root is an implementation/deployment decision and must follow existing run-artifact ownership and retention rules. The manifest records:

```text
schema_version
run_id
organism_id
software_commit
software_version
initial_checkpoint_hash
final_checkpoint_hash
configuration_hash
started_at / ended_at
first_tick / last_tick per stream
event_count per stream
truncation and gap summary
SHA-256 of each stream
```

Manifest values must come from existing run/checkpoint provenance. A value that is unavailable is `null`, not inferred.

## 5. Agency trace

### 5.1 Event model

Use a discriminated JSONL event record. Each record has:

```text
schema_version
run_id
organism_id
symbiont_tick
embodiment_epoch
event_seq
event_type
source_ref
payload
```

`event_seq` is a monotonic recorder-local sequence used only for ordering; it is not organism state or a causal identity. `source_ref` identifies the immutable source event where available.

Minimum `event_type` values:

- `gc_hypothesis_created`
- `gc_hypothesis_status_changed`
- `action_intent_formed`
- `action_commitment_activated`
- `motor_command_issued`
- `factual_transition_observed`
- `gc_reconciliation_attempted`
- `trace_gap`

Each event contains only fields available at that seam. Missing fields are represented as `null`; unrelated identity namespaces are not collapsed.

### 5.2 Required provenance fields

| Event | Required payload fields |
|---|---|
| Hypothesis created/status changed | `hypothesis_id`, `target_id`, `source_model_ids`, predicted outcomes, status, source episode IDs |
| Intent formed | `intent_id`, `competence_id`, `anticipated_effect_id` |
| Commitment activated | `commitment_id`, `intent_id`, `competence_id`, `controller_id` |
| Command issued | `command_id`, `commitment_id`, `competence_id`, `controller_id`, `embodiment_id` |
| Factual transition | `transition_id`, `competence_id`, `observed_effect_id`, evidence refs |
| Reconciliation attempted | `action_id`, `model_ids`, outcome tokens, evidence refs, matching active hypothesis IDs, result per hypothesis |

The factual reconciliation event must be emitted at the existing call boundary, using the exact input values supplied to `note_factual_outcome()`. It must not reconstruct those arguments independently.

### 5.3 Per-hypothesis reconciliation result

For every active hypothesis evaluated by a factual call, record one outcome:

```text
reconciled_supported
reconciled_contradicted
not_target_match
not_model_match
not_active
not_examined
```

Where the current code does not expose a reason or candidate set, record `not_examined` or `unknown` rather than simulating the matching algorithm in the recorder. A later pure analysis may derive a candidate comparison, clearly labeled as derived.

`action_not_executed` is not a valid conclusion from timeout alone. It may be recorded only if an authoritative execution/commitment lifecycle event explicitly establishes non-execution or termination.

### 5.4 Retention/window coverage

The manifest and `trace_gap` events report missing sequence ranges, recorder failures, truncation and startup/restart boundaries. Hypotheses that disappear from an active working set are not treated as reconciled or as failed unless the source lifecycle reports that status.

## 6. Energy trace

Emit one `energy_tick` record per Body tick, including:

```text
body_tick
energy_before
energy_after
energy_capacity
replenishment_by_channel
cost_by_channel
metabolic_reserve_by_channel
resource_pressure
vital_state_before
vital_state_after
resting_requested
homeostatic_action
motor_activity_summary
structural_integrity
absorbed_material
```

Values must be captured from the canonical accounting/state transitions already used by the runtime. This trace must not introduce new energy categories, recalculate pressure, or infer costs from mechanical-work summaries. If a field is not available at the chosen source seam, the implementation must either add a passive emission where the canonical value is produced or omit it with explicit coverage metadata; it must not calculate a substitute with different semantics.

One record per tick may be expensive. Any aggregation or sampling would weaken temporal claims and therefore requires an explicit design revision. Initial implementation should prefer complete per-tick capture with bounded runs and explicit size limits.

## 7. Recorder failure and resource bounds

- Recorder I/O must not block or change organism decisions beyond a documented, bounded instrumentation cost.
- The failure policy must be selected before implementation: fail the run, disable tracing with an explicit incomplete-artifact marker, or buffer within a strict limit. Silent dropping is prohibited.
- No unbounded in-memory queue. No writes to the organism checkpoint.
- Flush cadence, maximum bytes, rotation, fsync behavior and crash recovery must be defined for the selected run environment.
- Trace contents use opaque IDs and necessary factual tokens only. Do not store model prompt/context payloads or external semantic labels unless a separately approved protocol requires them.

## 8. Validation and acceptance

Implementation is not accepted until all of the following pass:

1. **No-feedback structural check:** organism packages do not import or query the recorder, and recorder output is not an input to cognition, action, physiology, checkpoint restore or replay.
2. **Identity preservation tests:** generated records preserve original command, competence, intent, commitment, transition, target and model IDs independently.
3. **Reconciliation boundary tests:** trace records exactly the actual call arguments and actual result; a distinct action/model cannot be reported as a match by recorder logic.
4. **No invented negatives:** expired/missing data produces an explicit gap/unknown classification.
5. **Energy provenance tests:** logged before/after, cost, replenishment and pressure values equal their canonical source values at that tick.
6. **Determinism/non-interference comparison:** with the same pinned inputs and seed, tracing on/off produces identical organism trajectory and checkpoint hashes, apart from allowed run metadata. If byte-identical checkpoints are impossible because of explicitly permitted metadata, compare a documented canonical state projection and justify the exclusion.
7. **Bounded resource test:** exercise configured maximum run/trace size and recorder failure policy.
8. **Artifact integrity:** manifest counts, sequence ranges and hashes validate; incomplete traces cannot be labeled complete.

These are engineering/observability gates, not evidence that GC, agency, energy regulation or re-embodiment is scientifically adequate.

## 9. Rollout

1. Review this design and obtain owner approval for observability scope and failure policy.
2. Inspect current telemetry/event seams and produce a source-to-field mapping before implementation.
3. Implement the recorder behind an explicit run-level opt-in; keep default behavior unchanged.
4. Run focused contract tests and a bounded non-scientific smoke comparison for non-interference.
5. Only after those checks, use it in a separately governed organism run. Pin code, bundle, configuration and run inputs; report missing trace coverage.
6. Do not modify GC behavior or interpret the trace as a scientific pass/fail result without a separate owner-reviewed proposal.

## 10. ADR decision

An ADR is **not required for this proposal**. This document describes a proposed diagnostic capability and deliberately makes no accepted architectural decision. An ADR becomes appropriate if implementation establishes a durable cross-package contract or requires a lasting choice about event identity, authority, retention, failure semantics, or canonical evidence flow. Such an ADR must record the decision and alternatives; it must not be used to imply approval of a scientific mechanism change.

## 11. Roadmap tracking

Keep the roadmap unchanged while this document is proposed and unapproved. The roadmap remains the canonical source for priority and accepted work; this design is supporting detail only.

If the owner later accepts implementation as ordinary apparatus observability, track one bounded task under A9 only if the A9 baseline inventory establishes that the trace is in scope. Link this document from that task and mark its status there; do not create a new milestone, B0 sub-milestone, or O5 criterion by implication.

If the audit shows that the trace requires changing factual identity flow, learning, agency behavior, physiological rules, or scientific criteria, stop and return with evidence. That is a separate owner decision and may require scientific classification, protocol review, and an ADR. Do not reclassify it as A9 merely to avoid that review.

