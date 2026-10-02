---
id: audit.longitudinal-integrity-2026-10-02
title: "Longitudinal Integrity Audit — 2026-10-02"
document_type: audit
domain: persistence
status: current
canonical: false
implementation_status: findings-resolved
date: 2026-10-02
source_commit: 922adcce49336a7cc1863757767f9eb2a8a4a8bc
follow_up_base_commit: 545fd5c2eb1257961605c5f6e94b169174b9c9a6
language: en
---

# Longitudinal Integrity Audit — 2026-10-02

## 1. Scope

This audit reconstructs the current Symbiont lifecycle from code and tests rather
than assuming documentation is correct. It follows state through:

```text
runtime
-> checkpoint construction
-> durable/bundle persistence
-> restore
-> restart
-> re-embodiment
-> observer projection
```

The primary forensic source was `main@922adcce`. Before this follow-up
documentation was prepared, `main` advanced to `545fd5c2`; that later commit
changes roadmap/governance documentation but does not invalidate the runtime
findings listed here.

No code was modified during the audit.

## 2. Findings register

| ID | Finding | Severity | Status |
| --- | --- | --- | --- |
| LI-01 | Internal `checkpoint_lineage.checkpoint_id` is generated but not recomputed and verified by generic restore | critical | confirmed |
| LI-02 | Current-schema missing acquired fields can be interpreted through compatibility defaults as fresh state | critical | confirmed |
| LI-03 | Core `_epistemic_ledger` is not serialized | critical | confirmed |
| LI-04 | `exchange_guard` is parsed on restore but not passed into the reconstructed runtime; `exchange_sequence` is also not restored | high | confirmed |
| LI-05 | Two organism-side social epistemology systems coexist with different ownership and persistence semantics | high | confirmed |
| LI-06 | Runtime-only cognitive plasticity and predictor-promotion switches return to defaults after restart unless the launcher reapplies them | high | confirmed |
| LI-07 | Raw runtime checkpoints do not contain private-model weight artifacts; the portable `.symbiont` bundle does | medium | confirmed |
| GOV-01 | `main` has no branch protection or repository ruleset, so governed publication is a convention/tool path rather than an unavoidable repository property | critical | confirmed |
| GOV-02 | Green CI means the applicable validation plan passed; it does not mean every scientific suite or experiment ran | medium | confirmed |
| EQ-01 | Equivalence is strong evidence only inside available scenario coverage; recent changes can legitimately be `NOT_ASSESSABLE_SNAPSHOT_SET` | medium | confirmed |
| EMB-01 | Current re-embodiment preserves Symbiont-owned cognition and resets current-Body authority; the historical destructive-reset suspicion is not supported by current code | resolved-positive | confirmed |
| EMB-02 | Historical global-tick/body-age contamination can be coordinate-migrated, but already-produced senescence/wear/energy consequences cannot be reconstructed away | medium | confirmed |
| ARCH-01 | `World` currently denotes multiple active environment families rather than one runtime architecture | medium | confirmed |
| OBS-01 | Physics3D replay reconstruction is explicitly marked as reconstructed in the viewer | resolved-positive | confirmed |

## 3. Detailed evidence

### LI-01 — lineage hash is not an authenticity check on restore

`OrganismRuntime.checkpoint()` computes a state hash and writes it as
`checkpoint_lineage.checkpoint_id`.

Generic `from_checkpoint()` validates only that the stored identifier is a
string and then uses it as the next parent lineage value. It does not recompute
the hash of the supplied state and compare the result.

Therefore a modified current checkpoint can retain an old lineage identifier and
still enter restore.

The portable Physics3D bundle mitigates byte-level corruption independently by
hashing `runtime.json` in its manifest. That bundle-level protection does not
turn the generic runtime lineage identifier into a validated state identity.

### LI-02 — migration compatibility can mask current-state loss

Many restore paths use the pattern:

```text
field present -> restore field
field absent  -> construct default / infer legacy state
```

This is necessary for historical migrations, but the current payload does not
consistently distinguish:

```text
field absent because the source schema predates it
```

from:

```text
field absent from a schema that was required to contain it
```

The second case must not silently become a new subsystem.

### LI-03 — core social epistemic state is intentionally omitted

The base runtime checkpoint currently contains an explicit TODO instead of
serializing `_epistemic_ledger`.

That ledger contains claims, source states, reconciliations and replayed-evidence
tracking and is used by organism-side social communication paths. Its loss is
therefore loss of acquired organism state, not only loss of telemetry.

### LI-04 — exchange replay state is disconnected during restore

The checkpoint writes both `exchange_guard` and `exchange_sequence`.

Restore reconstructs an `ExchangeReplayGuard` and populates its seen-set, but
the reconstructed value is not supplied to the new runtime constructor.
Likewise the stored sequence is not supplied. The new runtime therefore starts
with a fresh guard and sequence defaults.

### LI-05 — social epistemology has two organism-side authorities

The base runtime owns a social evidence ledger under
`symbiont.core.social`.

The modeled runtime owns a second social evidence system under
`symbiont.modeling`.

They have different consumers, data models and persistence behavior. One is
checkpointed and one currently is not. This is incompatible with Constitution
§17 item 129 — a capability must not have two sources of truth — unless a clear
non-overlapping responsibility boundary is formally established.

### LI-06 — restart equivalence depends on external reapplication of runtime switches

Cognitive plasticity and predictor promotion are initialized to enabled and are
explicitly not checkpointed. A longitudinal experiment that disables either
switch is not restart-equivalent unless its launcher or protocol deterministically
reapplies the same runtime configuration.

This may remain an apparatus-owned configuration choice, but its provenance and
restore contract must be explicit.

### LI-07 — checkpoint and portable organism are different persistence products

Private-model metadata, lineage and registry state live in the organism
checkpoint. Model weight artifacts remain outside the raw checkpoint.

The portable Physics3D `.symbiont` bundle packages those artifacts and hashes
them. Documentation and APIs must therefore avoid treating a raw runtime
checkpoint and a complete portable organism bundle as interchangeable terms.

## 4. Re-embodiment result

Current `prepare_fresh_embodiment_checkpoint()` starts from the previous
organism state and replaces Body-owned physiology and current execution
authority while retaining Symbiont-owned cognition.

The current implementation preserves, among other things:

- organism identity and time;
- genome and expression state;
- learned sensory state;
- SelfModel and BodySchema;
- CognitiveBridge/CognitiveGraph;
- generative cognition;
- experience and episodic memory;
- private-model registry and ancestry;
- learned sensorimotor effects, competences and causal evidence.

It resets or replaces current-Body state such as:

- living Body state;
- metabolism/homeostasis/physiology;
- current actuator surface authority;
- execution bindings;
- in-flight motor state.

The older helper that degraded an active private model at re-embodiment remains
present but has no current consumer.

The earlier hypothesis that the current re-embodiment transform itself erases
the whole cognitive core is therefore rejected for current `main`.

## 5. Governance result

At audit time GitHub reported:

```text
main.protected = false
rulesets = []
```

The `agentctl` candidate flow and promotion workflow enforce strong rules for
the recommended path, including refusing automatic promotion of SCIENTIFIC,
CONSTITUTIONAL and FROZEN changes. They do not make a direct write to `main`
technically impossible for an actor with write permission.

This is tracked separately as a governance-control-plane decision because fixing
it changes repository enforcement, not organism science.

## 6. Required follow-up

The runtime findings are governed by
[Longitudinal Integrity v1](../../../docs/design/core/longitudinal-integrity-v1.md).

Repository-side enforcement is proposed separately in
[ADR-0057](../../../docs/adr/ADR-0057-enforce-governed-main-publication.md).

The planning index records both workstreams in
[`docs/roadmap.md`](../../../docs/roadmap.md).

## 7. Claims this audit does not make

This audit does not establish:

- that every possible checkpoint corruption is exploitable;
- that all restore defaults are wrong;
- that either social evidence implementation is scientifically superior;
- that branch protection alone is sufficient scientific governance;
- that preservation of knowledge proves useful cross-body transfer;
- that private-model ancestry improves learning;
- that generative cognition improves organism behavior.

Those remain implementation or experimental questions and require separate
evidence.

## 8. Resolution record

Sections 1 to 7 are the audit as taken at `main@922adcce` and are not rewritten.
This section records the state of each finding at `main@3246a39d`, after
[Longitudinal Integrity v1](../../../docs/design/core/longitudinal-integrity-v1.md)
was implemented and closed by the owner on 2026-10-02. Do not work from the
findings above without reading it.

| ID | State | Where |
| --- | --- | --- |
| LI-01 | Resolved. Restore recomputes and verifies the state identity before migration and fails closed. | `verify_checkpoint_identity`; `tests/unit/host/test_strict_restore.py` |
| LI-02 | Resolved for current schemas. A current-schema checkpoint that lacks a required field is rejected. | `require_current_schema_fields` |
| LI-03 | Resolved by ARCH-1 Option A: the core ledger was removed from the organism runtime and the modeled ledger, which is checkpointed, is the single owner. | [Social Epistemology Ownership v1](../../../docs/design/core/social-epistemology-ownership-v1.md) |
| LI-04 | Resolved. The replay guard and the exchange sequence are restored. | `tests/integration/test_communication_restart.py` |
| LI-05 | Resolved by ARCH-1 Option A. | same record as LI-03 |
| LI-06 | Resolved. Session controls are recorded in `runtime_provenance` and reapplied; a changed value is recorded as a changed condition. | `tests/integration/test_restart_configuration.py` |
| LI-07 | Resolved as terminology: runtime checkpoint and portable bundle are separate, defined terms. | `docs/glossary.md` |
| GOV-01 | Resolved. An active ruleset requires `governed-ci-gate` on `main` with no bypass actors. Closed by the owner as GOV-1. | ADR-0057 |
| GOV-02 | Stands as a standing limit, not a defect: a green gate means the applicable validation plan passed. | — |
| EQ-01 | Stands. Equivalence remains evidence only inside available scenario coverage. No workstream is open for it. | — |
| EMB-01 | Resolved-positive, unchanged. | `tests/integration/test_reembodiment_continuity.py` |
| EMB-02 | Stands as a recorded limit: the clock coordinate is corrected and recorded; physiology already produced is not reconstructed. | `migrate_temporal_domains` |
| ARCH-01 | Recorded as an inventory; decisions are the owner's. | [World Responsibility Map v1](../../../docs/design/world/world-responsibility-map-v1.md) |
| OBS-01 | Resolved-positive, unchanged. | — |

The later
[Current-State Architecture Audit](2026-10-02-current-state-architecture-audit.md)
supersedes this document as the description of the system.
