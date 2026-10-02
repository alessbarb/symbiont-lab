---
id: design.core.social-epistemology-ownership-v1
title: "Social Epistemology Ownership v1"
document_type: design
domain: core
status: proposed
canonical: false
implementation_status: analysis-only
date: 2026-10-02
depends_on:
  - docs/governance/constitution.md
  - docs/design/core/longitudinal-integrity-v1.md
source_audit: research/audits/current/2026-10-02-longitudinal-integrity-audit.md
source_commit: 60eb9a04
language: en
---

# Social Epistemology Ownership v1

## 1. Purpose

This is the consumer/ownership matrix required by
[Longitudinal Integrity v1 §7](longitudinal-integrity-v1.md) and tracked as
roadmap workstream ARCH-1. It answers audit finding LI-05: two organism-side
social evidence systems coexist with different persistence semantics.

It records what the code does at `main@60eb9a04`, classifies every
responsibility, and states the decision the owner must take. It does **not**
take that decision, choose a scientifically preferred model, or change code.

## 2. The two systems

| | Core ledger | Modeled ledger |
| --- | --- | --- |
| Class | `symbiont.core.social.ledger.SocialEvidenceLedger` | `symbiont.modeling.culture.SocialEvidenceLedger` |
| Runtime attribute | `OrganismRuntime._epistemic_ledger` | `ModeledOrganismRuntime._social_evidence_ledger` |
| Present on | every runtime | modeled and private-model runtimes only |
| Claim type | `core.social.ledger.SocialClaim`: opaque `payload`, `source_id`, root/parent id sets, `freshness` | `modeling.culture.SocialClaim`: proposition tokens, source and immediate sender, root evidence and parent claims, tick classes, epistemic status, confidence class, transmission and mutation depth |
| State | claims, per-source `SourceEvidenceState`, reconciliations, seen-evidence set | claim graph with ancestry, composite graph, held claims, bounded local assessments, cost counters |
| Bounds | none | `max_claims`, `max_assessments`, `max_composites`, depth and size limits |
| Checkpointed | **no** (`runtime.py` carries a `# TODO` instead) | yes, `social_evidence_ledger`, schema version 1 |
| Restored | no: rebuilt empty | yes, `SocialEvidenceLedger.restore` |
| In `checkpoint_id` | no | no (added after the base runtime hashes its payload) |

Both classes are named `SocialEvidenceLedger` and both claim types are named
`SocialClaim`. They share no code.

## 3. Consumer matrix

### 3.1 Core ledger

| Consumer | Operation | Reachable on `OrganismRuntime`? |
| --- | --- | --- |
| `OrganismRuntime.__init__` (`cultural_heritage`) | writes claims inherited from a parent | yes; the only caller is `ResidentOrganism` budding |
| `OrganismRuntime.receive_communication` | writes one claim per envelope entry | yes; called by `symbiont_lab.world.population` when delivering committed messages |
| `OrganismRuntime.broadcast_claims` | reads `reconciliations`, emits each reconciled claim once | called every tick when a social habitat and a channel are attached, but see §3.3 |
| `OrganismRuntime.export_cultural_heritage` | reads `reconciliations` to build offspring heritage | called by `ResidentOrganism` budding, but see §3.3 |
| `core.cognition.agent.Agent` | owns a separate instance; receives, reconciles and broadcasts claims | no: `Agent` is the legacy simulation agent, not the organism runtime |
| `core.cognition.reasoning`, `curiosity`, `metacognition` | read `open_questions()` / `unresolved_claims()` | only through `Agent` |
| `symbiont.simulation.engine` | reads source reliability and open questions for evaluation breakdowns | only through `Agent` |
| `symbiont_lab.studies.heritage.*` (`stress`, `longitudinal`, `ecological_shift`) | construct or pass a ledger into the legacy simulation | no |
| regression and integrity tests (`tests/regression/audits/v021`, `v024`, `tests/experimental_integrity/test_evidence_replay.py`) | exercise `record_local_reconciliation` and replay rejection directly | no |

### 3.2 Modeled ledger

| Consumer | Operation |
| --- | --- |
| `ModeledOrganismRuntime.autonomous_cultural_step` | `CulturalPolicy` selects retain/drop/transmit/validate/compose/retire over the ledger |
| `ModeledOrganismRuntime.originate_social_claim` / `receive_social_claim` / `transmit_social_claim` | create, receive and forward claims with ancestry |
| `ModeledOrganismRuntime.compose_cultural_claims` / `transmit_cultural_composite` | build and forward composites |
| `ModeledOrganismRuntime.cultural_observations` | observer projection of claims and composites |
| `ModeledOrganismRuntime.checkpoint` / `from_checkpoint` | persist and restore |
| `symbiont_lab.integration.integrated_habitat` | counts claims and composites for habitat telemetry |
| `symbiont_lab.studies.learning.autonomous_cultural_agency` | reads composites for the study result |
| `symbiont_lab.studies.learning.cultural_foundation`, `cumulative_culture` | drive ledgers directly through `SocialChannel` |
| `symbiont_lab.reproduction.runtime` | gives each materialized child an empty ledger |

### 3.3 Finding: the core ledger is write-only inside the organism runtime

`broadcast_claims` and `export_cultural_heritage` iterate
`_epistemic_ledger.reconciliations`. The only writer of that mapping is
`SocialEvidenceLedger.record_local_reconciliation`, and no code path of
`OrganismRuntime`, `ModeledOrganismRuntime` or `PrivateModelOrganismRuntime`
calls it. Its callers are the legacy `Agent` and tests.

Consequences on any organism runtime today:

- claims delivered by `receive_communication` and inherited through
  `cultural_heritage` accumulate in `_epistemic_ledger.claims` without bound;
- they are never assessed, so `reconciliations` stays empty;
- `broadcast_claims` therefore returns no message and
  `export_cultural_heritage` returns an empty list, although the tick still
  charges `0.05 × targets` of cognition for the broadcast attempt and
  `receive_communication` charges `0.02` per message;
- nothing in the runtime reads the accumulated claims.

So the state lost on restart under LI-03 is real acquired input (received
claims), but it currently has no downstream effect on organism behaviour.

## 4. Responsibility classification

Using the vocabulary of Longitudinal Integrity v1 §7:

| Responsibility | Core ledger | Modeled ledger | Classification |
| --- | --- | --- | --- |
| Hold socially received claims with provenance | partial: ids and sets, opaque payload, unbounded | full: bounded ancestry graph | **overlapping**: one capability, two owners |
| Local assessment of a claim against own evidence | defined (`record_local_reconciliation`) but unreachable from the runtime | `assess`, `LocalAssessment`, policy-driven validation | **overlapping**; only the modeled side is live |
| Retransmission to peers | `broadcast_claims` (never fires) | `retransmit`, policy-driven | **overlapping**; only the modeled side is live |
| Cultural inheritance to offspring | `export_cultural_heritage` → `cultural_heritage` (always empty) | none at the ledger; reproduction gives the child an empty ledger | core-only path, inert |
| Per-source reliability (`SourceEvidenceState`) | yes | no equivalent; confidence is per claim | **distinct**, but reachable only through legacy `Agent` |
| Replay rejection of already-counted evidence (`seen_evidence`) | yes | ancestry graph rejects duplicate claim ids | **overlapping** in intent |
| Composition of claims into cumulative culture | none | `CompositeGraph` | modeled-only |
| Evaluation metrics for the legacy simulation engine | yes | none | **legacy migration-only**: belongs to `Agent`/`simulation`, not to the organism runtime |

Reading of the matrix:

- For the organism runtime, receiving, assessing and retransmitting social
  claims is **one capability with two owners**. Constitution §17 item 129 is
  not satisfied by the current boundary.
- The core ledger is canonical only for the legacy `Agent` simulation, where
  it is fully wired and tested.
- Inside the organism runtime the core ledger is fed but inert, and the modeled
  ledger is the only live, bounded and persisted social epistemology.

## 5. Options for the owner decision

The decision is the owner's. Each option states what it implies for LI-P2.

### Option A — modeled ledger is canonical for the organism runtime

The core ledger stays as the legacy `Agent`/simulation model and is removed
from `OrganismRuntime`. Structured communication delivered by
`receive_communication` is routed to the modeled ledger (or rejected on a
runtime that has none), and `broadcast_claims` / `export_cultural_heritage`
are retired from the runtime or re-expressed over the modeled ledger.

- LI-P2: nothing new to persist; LI-03 closes by removing the unpersisted
  state rather than by serializing it.
- Cost: base `OrganismRuntime` loses its (inert) social-claim path; resident
  budding loses the heritage argument it never populated.
- Risk: `symbiont_lab.world.population` delivers messages to base runtimes;
  the routing rule for a runtime without a modeled ledger must be explicit.

### Option B — core ledger is canonical

The core ledger gains a checkpoint contract, bounds and a live reconciliation
path, and the modeled ledger's responsibilities are migrated onto it.

- LI-P2: serialize the core ledger permanently and migrate
  `social_evidence_ledger` payloads.
- Cost: largest change; the modeled ledger carries ancestry, composites and
  policy integration the core ledger does not have.

### Option C — intentionally distinct

Declare the core ledger the owner of *per-source reliability* and the modeled
ledger the owner of *claim ancestry and culture*, and remove every overlapping
operation from one side so the boundary is non-overlapping.

- LI-P2: persist both, each for its own responsibility.
- Cost: requires wiring a live reconciliation path into the runtime so the
  core ledger's reliability state is actually produced; otherwise it persists
  state nothing reads.

### Recommendation

Option A matches the code as it runs: it makes the only live, bounded and
persisted system the single owner and removes state that is acquired but never
used. It is a recommendation, not a decision; Options B and C are coherent if
the owner intends the core reconciliation model to become live.

## 6. Minimum immediate protection (independent of the decision)

Longitudinal Integrity v1 §7.2 requires that no acquired social knowledge of
the active organism disappears silently on restart, whatever is decided.

Until the decision is recorded, LI-P2 may serialize `_epistemic_ledger` and
`_last_broadcast_reconciliations` as an **interim** measure, marked as such in
code and in the continuity register. Under Option A that field becomes
migration-only and is dropped; under B or C it becomes permanent. It must not
be left as two indefinitely checkpointed overlapping models (§16).

Not blocked by this decision: the exchange replay guard and sequence (LI-04)
belong to `social.exchange`, are shared by both paths, and can be repaired
independently.

## 7. Decision record

| Field | Value |
| --- | --- |
| Decision | _pending owner_ |
| Chosen option | _pending_ |
| Date | _pending_ |
| Follow-up | LI-P2 scope is fixed by the chosen option |
