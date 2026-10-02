---
id: design.core.longitudinal-integrity-v1
title: "Longitudinal Integrity v1"
document_type: design
domain: core
status: closed
canonical: false
implementation_status: implemented
date: 2026-10-02
depends_on:
  - docs/governance/constitution.md
  - docs/design/embodiment/embodiment-v2.md
  - docs/design/embodiment/longitudinal-reembodiment-v1.md
source_audit: research/audits/current/2026-10-02-longitudinal-integrity-audit.md
language: en
---

# Longitudinal Integrity v1

## 1. Purpose

This specification defines the remediation gate required before Symbiont can
claim that a durable restart continues the same organism without silently
losing, inventing or reinterpreting acquired state.

It does not redesign cognition and does not change the ontology established by
Embodiment v2.

The scope is:

~~~text
same Symbiont
-> durable checkpoint/bundle
-> process boundary
-> restore
-> optional new Body
-> continued life
~~~

The governing Constitution already requires that restoration continue the same
individual when specified, must not fabricate absent memories, must reject
cross-tick inconsistency, and must preserve causal continuity. This design turns
those existing invariants into explicit executable contracts.

## 2. Non-goals

Longitudinal Integrity v1 does not:

- make raw runtime checkpoints and portable bundles identical artifacts;
- make every transient microstate survive restart;
- preserve current-Body execution authority across re-embodiment;
- turn imagined or predicted state into observed evidence;
- choose a scientifically preferred social epistemology model;
- prove that retained knowledge is useful;
- authorize new capability experiments;
- relax backward compatibility by silently rewriting historical evidence.

## 3. State classes

Every persisted or intentionally non-persisted runtime field relevant to
continuity must be assigned exactly one continuity class.

### 3.1 MUST_PRESERVE

The field belongs to the same organism and must survive a same-organism restart
semantically intact.

Examples include acquired cognition, learned relationships, private-model
registry state, episodic memory and organism identity.

### 3.2 MUST_RESET

The field represents transient process state that must not cross a process
boundary because carrying it would fabricate continuity that did not occur.

Examples may include one-tick causal traces and in-flight host/process handles.

### 3.3 MAY_RECOMPUTE

The field is a deterministic projection of preserved authoritative state and may
be rebuilt without inventing knowledge.

The authoritative inputs and the deterministic reconstruction rule must be
documented.

### 3.4 MUST_REAPPLY_CONFIG

The field is apparatus/runtime configuration rather than acquired organism
state. It need not be serialized into the organism, but a governed continuation
must reapply and record it before the organism resumes.

Cognitive-plasticity and predictor-promotion switches are current examples.

### 3.5 MUST_INVALIDATE_AUTHORITY

The knowledge itself survives, but current execution authority must be withdrawn
because the external contract changed.

Current-Body execution bindings on re-embodiment are the primary example.

No field may remain unclassified once this gate closes.

## 4. Checkpoint authenticity contract

### 4.1 Current checkpoint identity

When a checkpoint carries checkpoint_lineage.checkpoint_id, generic restore
must verify that the supplied state corresponds to that identifier before it is
accepted as the same saved state.

The canonical check must use the same state-hash definition used when the
checkpoint was created.

Expected behavior:

~~~text
load payload
-> identify source schema
-> apply only authorized structural normalization needed to interpret that schema
-> verify stored state identity at the correct representation boundary
-> reject mismatch
-> restore
~~~

The implementation must not accidentally validate a transformed state against a
hash that described a different representation. The exact pre-/post-migration
hash boundary must therefore be fixed in tests and documented in code.

### 4.2 Bundle integrity remains separate

The portable .symbiont bundle already validates the bytes of runtime.json and
model artifacts through manifest hashes.

Bundle integrity and organism state lineage are independent contracts:

~~~text
bundle hash
    proves package bytes match the manifest

checkpoint lineage hash
    proves the accepted organism state matches its recorded save identity
~~~

Neither substitutes for the other.

## 5. Schema-aware strict restore

Compatibility defaults are allowed only when the declared source schema
predates the field or when a documented migration explicitly defines the
absence.

For a current schema, required acquired-state fields must not disappear
silently.

The normalization layer must make this distinction explicit.

Target conceptual result:

~~~text
source_schema = N
migrations = [N->N+1, ...]
required_fields_for_source_or_normalized_schema = {...}
~~~

Then:

~~~text
required field absent unexpectedly
-> CheckpointError
~~~

not:

~~~text
required field absent unexpectedly
-> construct fresh subsystem
~~~

### 5.1 Migration rule

A migration may:

- rename representation;
- add a field that provably did not exist;
- derive a deterministic projection from retained authoritative information;
- discard contaminated historical state when the migration explicitly records
  that information cannot be truthfully recovered.

A migration must not:

- manufacture learned evidence;
- fabricate provenance;
- infer a lost memory from evaluator truth;
- silently convert corruption into a healthy empty subsystem.

## 6. Complete organism-state ownership register

Create one machine-testable register mapping all longitudinal state to:

- owner;
- continuity class;
- checkpoint field;
- restore path;
- migration support;
- re-embodiment behavior;
- whether the field contributes to state identity.

The register must cover at least:

- identity and organism tick;
- genome and expression;
- sensory/adaptive learning;
- SelfModel;
- BodySchema;
- CognitiveGraph/CognitiveBridge;
- memory consolidator;
- generative cognition;
- signal knowledge;
- metabolism/physiology where relevant to same-Body restart;
- sensorimotor v2;
- effects, causal evidence, competences, composition and action dimensions;
- experience ledger;
- historical experience archive;
- episodic memory;
- private-model registry;
- tokenizer/model ancestry;
- social epistemic state;
- communication replay guard and sequence;
- cultural/symbolic/sequence state;
- executive/prospective state;
- embodiment archive and episode identity.

## 7. Social epistemology consolidation gate

The current runtime contains two organism-side social evidence systems with
different persistence semantics.

Before implementing a permanent persistence patch, perform a consumer/ownership
matrix for both systems.

The review must classify every responsibility as one of:

~~~text
canonical social epistemology
distinct non-overlapping responsibility
legacy migration-only responsibility
retired
~~~

### 7.1 Decision rule

If both systems represent the same scientific responsibility, one canonical
owner must be chosen and the other migrated/retired.

If they are intentionally different, their boundary must be explicit enough to
show that Constitution §17 item 129 — one source of truth per capability — is
not violated.

### 7.2 Minimum immediate protection

Regardless of the final consolidation decision, no acquired social knowledge
that is part of the active organism may silently disappear on restart.

## 8. Communication restart contract

The persisted communication anti-replay and sequencing state must round-trip
when communication is enabled.

Required tests:

1. accept a new envelope;
2. checkpoint;
3. restore in a new runtime;
4. reject replay of the already-seen envelope;
5. emit the next outbound message using the continued sequence rather than
   restarting at zero.

The test must cross a real serialization boundary rather than reusing the same
Python object graph.

## 9. Runtime configuration provenance

Runtime-only switches may remain outside organism state if they are genuinely
apparatus configuration.

A governed restart must nevertheless record and reapply them before the first
continued tick.

At minimum, the continuation receipt/configuration must make the effective
values of these controls explicit:

- cognitive plasticity enabled/disabled;
- predictor promotion enabled/disabled;
- any equivalent session-scoped switch that changes future learning or model
  lifecycle.

A continuation with different effective configuration is a changed condition,
not exact restart equivalence.

## 10. Raw checkpoint versus portable organism bundle

The project must use distinct terms.

### Runtime checkpoint

A serialized organism/runtime state representation. It may reference artifacts
stored elsewhere.

### Portable Symbiont bundle

A self-contained transport package for the declared portable organism state,
including required private-model artifacts and their integrity hashes.

Documentation, CLI output and tests must not use the two terms interchangeably
when artifact completeness matters.

## 11. Restart-equivalence test

Add a canonical integration contract that develops non-trivial state before
crossing the process boundary.

Minimum structure:

~~~text
create organism
-> acquire representative state in every MUST_PRESERVE family
-> checkpoint
-> serialize
-> destroy original runtime
-> restore
-> compare semantic continuity
-> continue both control and restored branches under deterministic conditions
-> compare declared future-equivalence surface
~~~

The test must not merely compare JSON.

It must verify:

- identity;
- learned-state presence and meaning;
- replay/sequence continuity;
- model and ancestry continuity;
- episodic continuity;
- social-state continuity;
- expected reset of transient fields;
- reapplication of runtime-only configuration.

The comparison surface must be explicit and bounded.

## 12. Re-embodiment continuity test

The restart contract and the re-embodiment contract are distinct.

A second canonical test must:

~~~text
develop organism in Body A
-> record Symbiont-owned state fingerprint
-> replace with Body B
-> verify MUST_PRESERVE state survives
-> verify MUST_INVALIDATE_AUTHORITY state loses current authority
-> continue experience
-> verify old knowledge may be revised but was not erased by the transform
~~~

This is a mechanical continuity test. It does not establish transfer benefit.

## 13. Historical contaminated checkpoints

The existing body-age decontamination migration may correct coordinate identity
when the legacy state makes that unambiguous.

It must continue to record that already-produced physiology cannot be
retroactively reconstructed.

No migration may claim to undo historical:

- senescence;
- wear;
- metabolic consumption;
- death pressure;
- other causal consequences already produced under the contaminated clock.

Those runs remain scientifically limited for claims depending on those effects.

## 14. Test matrix

### Unit

- state hash recomputation and mismatch rejection;
- current-schema required-field rejection;
- migration-only absence accepted only for old schemas;
- exchange guard restore;
- exchange sequence restore;
- continuity-class register validation.

### Compatibility

- every supported historical schema migrates deterministically;
- a modern payload with the same missing field fails where its historical
  predecessor legitimately migrates;
- legacy temporal contamination retains explicit provenance.

### Integration

- cold restart semantic equivalence;
- private-model artifact resolution through the portable bundle;
- same-Body restart preserves Body/Embodiment identity;
- new-Body re-embodiment preserves organism state and invalidates Body authority;
- communication replay remains rejected after restart.

### Experimental integrity

- observer ON/OFF does not change continuity outcome;
- restart does not silently toggle a governed learning condition;
- no evaluator information is used to repair missing organism state.

## 15. Acceptance gate

Longitudinal Integrity v1 is closed only when all of the following are true:

1. current checkpoints with lineage verify their recorded state identity or fail
   closed;
2. current-schema loss of required acquired state cannot silently instantiate a
   fresh subsystem;
3. every longitudinal field is assigned a continuity class;
4. active social epistemic knowledge round-trips or has been migrated to its
   accepted canonical owner;
5. exchange replay protection and sequence survive restart;
6. runtime-only causal configuration is provenance-recorded and deterministically
   reapplied;
7. raw checkpoint and portable bundle semantics are documented and tested;
8. cold restart equivalence passes with developed cognition;
9. re-embodiment continuity passes while current-Body authority is correctly
   withdrawn;
10. historical temporal contamination remains explicitly bounded rather than
    being presented as repaired physiology.

**Disposition — CLOSED (positive), 2026-10-02, by owner decision.** Mechanical
longitudinal continuity is established within this specification's documented
scope. Focused validation on `main@032ebd35` ran the gate-mapped restore,
continuity, restart, communication, configuration, persistence, re-embodiment,
and experimental-integrity suites: `280 passed`. This is not a full-suite claim.

The closure does not assert:

- future-state equivalence after restart; one-tick causal traces reset and
  reacclimation resumes;
- retrospective identity verification for checkpoints before schema 11;
- checkpoint-identity coverage of apparatus-owned embodiment history, whose
  integrity depends on the portable bundle;
- useful transfer, adaptive advantage, or scientific value of retained state.

## 16. Implementation order

~~~text
LI-P0  state ownership inventory + continuity classes
  ->
LI-P1  checkpoint identity verification + strict current-schema restore
  ->
LI-P2  communication/social persistence repair
  ->
LI-P3  runtime configuration provenance/reapplication
  ->
LI-P4  canonical restart-equivalence integration test
  ->
LI-P5  re-embodiment continuity integration test
  ->
LI-P6  terminology/docs cleanup + legacy removal only after consumers are proven absent
~~~

The social epistemology ownership decision may block LI-P2. It must not be
bypassed by checkpointing both overlapping models indefinitely.

## 17. Scientific follow-up after mechanical closure

Mechanical preservation is not evidence of useful transfer.

After this gate closes, separate preregistered work may test:

- whether mature prior cognition improves reacclimation in a new Body;
- whether private-model inference changes behavior causally;
- whether model ancestry improves learning under matched budgets;
- whether generative cognition contributes causal behavioral value.

Those questions remain outside this specification.

## 18. Implementation record

This section records where each gate item is implemented and tested. The owner
closure and its limits are recorded in §15; implementation status does not imply
scientific acceptance.

| Gate item | Implementation | Evidence |
| --- | --- | --- |
| 1. Lineage identity verified or fail closed | `host/checkpoint.py`: `checkpoint_state_hash`, `verify_checkpoint_identity`, `stamp_checkpoint_identity`; schema 11 | `tests/unit/host/test_strict_restore.py`, `tests/compatibility/migrations/test_host_checkpoint_v10_identity_migration.py` |
| 2. No silent fresh subsystem on current-schema loss | `host/checkpoint.py`: `require_current_schema_fields` | `tests/unit/host/test_strict_restore.py` |
| 3. Every field has a continuity class | `host/continuity.py` | `tests/unit/host/test_continuity_register.py` |
| 4. Active social epistemic knowledge round-trips or lives in its canonical owner | ARCH-1 Option A: the core ledger is removed from the organism runtime; the modeled ledger is the single owner, persisted and inside checkpoint identity | `tests/integration/test_restart_equivalence.py`, `tests/integration/test_communication_restart.py`, `tests/unit/host/test_continuity_register.py` |
| 5. Exchange replay protection and sequence survive | `core/social/exchange.py`: `ExchangeReplayGuard.restore`; runtime restore | `tests/integration/test_communication_restart.py` |
| 6. Runtime-only configuration recorded and reapplied | `runtime_provenance.session_controls`, `changed_since_restore` | `tests/integration/test_restart_configuration.py` |
| 7. Checkpoint and bundle semantics documented and tested | `docs/glossary.md`, `docs/symbiont/11-persistence-provenance-and-reembodiment.md` | `tests/unit/lab/physics3d/test_persistence.py` |
| 8. Cold restart equivalence with developed cognition | — | `tests/integration/test_restart_equivalence.py` |
| 9. Re-embodiment continuity, Body authority withdrawn | transforms re-identify their output | `tests/integration/test_reembodiment_continuity.py` |
| 10. Temporal contamination stays bounded | `physics3d/reembodiment.py`: `migrate_temporal_domains` | `tests/unit/lab/physics3d/test_reembodiment.py` |

Experimental-integrity tier: `tests/experimental_integrity/test_longitudinal_integrity.py`.

### Decisions taken during implementation

- **Hash boundary (§4.1).** Identity is verified on the payload as loaded,
  before normalization. It covers the complete organism payload of the saving
  runtime and excludes `checkpoint_lineage`, `runtime_provenance` and the
  embodiment history written by the apparatus. Schema 10 and earlier covered
  only base-runtime fields and were never checked; they are accepted
  unverified.
- **Authorized transforms.** Re-embodiment, temporal decontamination and
  canonical-cognition adoption re-identify the state they produce, chaining to
  the identifier they replace and naming the transform.
- **Which checkpoints are "current" (§5).** Strictness follows the schema the
  saving runtime declared, recorded in both the lineage block and
  `runtime_provenance` and carried unchanged through transforms. A transform
  gives a schema-10 checkpoint a verifiable identity but never makes it a
  current one: it still lacks the fields only schema 11 writes and keeps its
  migration defaults. Real schema-10 payloads are kept under
  `tests/compatibility/checkpoint_v10/` and exercised through every transform.
- **Runtime configuration (§9).** Recorded as provenance rather than organism
  state, so it does not enter state identity.

### What gate item 8 does and does not establish

A cold restart is identical at the boundary. Its future is not identical to an
uninterrupted run once cognition is developed, for two deliberate resets:
one-tick causal traces are not carried across a process boundary (§3.2), and
every restore opens the reacclimation gate. The test fixes the fields that may
differ and requires every other field to stay identical. Narrowing that surface
— carrying one-tick traces, or skipping the gate on a same-Body restart — would
be a design change and is not made here.

### Open

- Apparatus-owned embodiment history is outside checkpoint identity; its
  integrity relies on the portable bundle manifest.
- After ARCH-1 Option A no organism runtime emits exchange envelopes, so the
  preserved outbound sequence is never advanced. Whether the envelope transport
  stays in the runtime is recorded as open in
  [Social Epistemology Ownership v1](social-epistemology-ownership-v1.md) §8.
