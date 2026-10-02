---
id: audit.current-state-2026-10-02
title: "Current-State Architecture Audit — 2026-10-02"
document_type: audit
domain: core
status: current
canonical: false
implementation_status: findings-resolved-pending-owner-decisions
date: 2026-10-02
source_commit: 2ac4296dfcd5b3f1f250a47b9cf00f84a4d3627c
follow_up_base_commit: 3246a39d05b2fd75452d804c50e43acc2b110265
language: en
---

# Current-State Architecture Audit — 2026-10-02

## 1. Scope

This audit reconstructs the system from `main` — code and active paths first,
documentation afterwards as a contrast — and does not accept names, ADRs or
tests as sufficient proof on their own. It follows:

```text
birth
-> runtime
-> checkpoint
-> restore / restart
-> re-embodiment
-> observer projection
-> repository governance
```

The forensic source is `main@2ac4296d`, read on 2026-10-02.

No code was modified during the audit. The audit is kept separate from any
correction: sections 2 to 12 are the audit as taken and are not rewritten.
Section 13 records what was done afterwards for each finding.

It follows the
[Longitudinal Integrity Audit](2026-10-02-longitudinal-integrity-audit.md)
taken earlier the same day at `main@922adcce`. Several findings of that audit
are resolved at this commit; §9 records which.

### 1.1 Summary

The longitudinal core is now reasonably well protected, and several critical
problems documented earlier the same day no longer exist in the code. At this
commit the system has:

- verifiable checkpoint identity in schema 11;
- explicit rejection of current checkpoints that lack required state;
- a formal ownership/continuity register of runtime attributes;
- restart with verified semantic conservation of identity, experience, models,
  cognitive graph and social state;
- Physics3D re-embodiment that starts from the previous organism and replaces
  Body state, not the organism;
- CognitiveGraph, experience, private models and sensorimotor knowledge
  preserved through re-embodiment;
- `main` protected by an active GitHub ruleset;
- a single required gate, `governed-ci-gate`, with no bypass configured.

The longitudinal architecture is nevertheless not closed. The most serious
remaining problem is no longer an evident loss of state: it is that several
semantics of "Symbiont" and several lifecycle paths exist that do not mean
exactly the same thing. Canonical Physics3D re-embodiment preserves knowledge;
the reduced `Symbiont` used by clean-embodiment studies does not preserve it in
the same way. Different experiments can therefore run under apparently
identical terminology.

## 2. Findings register

| ID | Finding | Severity | Certainty | Status |
| --- | --- | --- | --- | --- |
| F-01 | Two longitudinal semantics of "Symbiont": the reduced `Symbiont` rebuilds embodiment-specific inference on `begin_new_embodiment()`, the canonical Physics3D path does not | high | confirmed | open |
| F-02 | Current Physics3D re-embodiment does not erase cognition; the earlier destructive-reset suspicion is rejected | resolved-positive | confirmed | closed |
| F-03 | Checkpoint identity is verified and required fields are enforced for the current schema | resolved-positive | confirmed | closed |
| F-04 | Schema 10 checkpoints are deliberately accepted with unverified identity | medium | confirmed | open — explicit compatibility boundary |
| F-05 | Restart deliberately loses the transition that crosses the process boundary | medium | confirmed | open — must stay in the scientific contract |
| F-06 | "Restore" has two semantics: historical restore and owner-facing restore with canonical-cognition adoption | medium | confirmed | open |
| F-07 | The `observatory` namespace contains both the passive observer and the organism launcher | medium | confirmed | open |
| F-08 | A capture-manifest write failure is silently swallowed in `observatory/resident.py` | medium | confirmed | open |
| F-09 | "World" is a family of environments, not a single runtime abstraction | medium | very likely | open |

## 3. Real architecture

The architecture that exists is not simply `World -> Body -> Symbiont -> UI`.
It is closer to:

```text
                       ┌─────────────────────┐
                       │ Genome / Germline   │
                       └──────────┬──────────┘
                                  │
                                  ▼
┌────────────┐        ┌─────────────────────────────┐
│ Providers /│───────▶│ OrganismRuntime             │
│ Body/World │        │                             │
└────────────┘        │ Perception                  │
                      │ Cognition / CognitiveGraph  │
                      │ Memory                      │
                      │ Agency / sensorimotor       │
                      │ Physiology                  │
                      │ Development                 │
                      │ Social                      │
                      └──────────────┬──────────────┘
                                     │
              ┌──────────────────────┼────────────────────┐
              ▼                      ▼                    ▼
       ModeledRuntime       PrivateModelRuntime      checkpoint
                                   │                    │
                                   ▼                    ▼
                         Experience / models      organism.symbiont
                                                  + model artifacts
```

Physics3D adds a second lifecycle, in which the separation
Symbiont ≠ Body ≠ Embodiment is explicit:

```text
Longitudinal Symbiont
        │
        ├── Embodiment episode A ── Body A
        │
        ├── Embodiment episode B ── Body B
        │
        └── Embodiment episode C ── Body C
```

The main mechanism lives in:

- `src/symbiont/core/orchestration/runtime.py`
- `src/symbiont_lab/physics3d/runtime.py`
- `src/symbiont_lab/physics3d/reembodiment.py`
- `src/symbiont/host/continuity.py`

## 4. Detailed evidence

### F-01 — two semantics of Symbiont

`OrganismRuntime` is the main cognitive runtime. In parallel,
`src/symbiont/core/orchestration/symbiont.py::Symbiont` exists and is not
equivalent to it; its own docstring calls it the "Minimal autonomous seed used
by clean embodiment studies." The two classes must not be treated as two names
for the same organism.

The reduced `Symbiont` keeps `symbiont_id`, genome, germline, gene expression,
`total_ticks`, output history and `competence_library`.

`begin_new_embodiment()` calls `_reset_embodiment_state()`, which rebuilds:

- `SensorimotorDynamicsModel`;
- `BodySchemaEngine`;
- `ActionDomain`;
- `AgencyAcquisition`;
- causal evidence;
- controllability;
- agency;
- signal mapping.

Historical competences additionally receive `competence.effect_id = None`: they
survive, but lose factual authority over the current body.

This may be a scientifically valid semantics, but it is not "the Symbiont is
preserved as is", and it differs from the canonical Physics3D path (F-02).

### F-02 — Physics3D re-embodiment no longer erases cognition

`prepare_fresh_embodiment_checkpoint()` begins with
`result = deepcopy(dict(previous))`: the operation starts from the previous
organism and then selectively replaces what belongs to the new Body.

`_detach_body_specific_cognition()` encodes the rule that the CognitiveGraph is
longitudinal Symbiont state and must survive every Body replacement intact, and
the code returns the preserved bridge.

`_carry_sensorimotor_v2_knowledge()` preserves competences, effects, causal
evidence, exploration memory, composition, acquired dimensions and
`AgencyAcquisition`, and replaces only execution authority: surface binding,
execution bindings, active commitment, pending execution and pending
proprioception.

```text
Identity                         PRESERVED
global tick                      PRESERVED
Genome                           PRESERVED
expression                       PRESERVED
CognitiveGraph                   PRESERVED
ExperienceLedger                 PRESERVED
EpisodicMemory                   PRESERVED
PrivateModelRegistry             PRESERVED
model ancestry                   PRESERVED
competences                      PRESERVED
causal evidence                  PRESERVED
sensorimotor knowledge           PRESERVED

LivingBodyState                  NEW
physiology                       NEW
metabolism                       NEW
homeostasis                      NEW
execution bindings               INVALIDATED
in-flight motor commitment       DISCARDED
actuator authority               NEW
```

Supported by `tests/integration/test_reembodiment_continuity.py` and by real
schema 10 compatibility in
`tests/compatibility/checkpoint_v10/test_real_v10_checkpoints.py`; this is not
merely an artificial round trip.

### F-03 — checkpoint identity is now verified

`verify_checkpoint_identity(payload)` and
`require_current_schema_fields(payload, layer=...)` run before normalization and
restore. `verify_checkpoint_identity()` is documented as "Fail closed unless a
checkpoint matches the identity it recorded."

This corrects LI-01. `require_current_schema_fields()` removes LI-02 for current
schemas: a required field missing from a current-schema payload no longer
silently becomes a fresh subsystem.

For schema 11, a tampered checkpoint fails restore. Legacy schemas follow a
separate migration policy (F-04).

### F-04 — schema 10 keeps a deliberately lower trust level

The tests state it explicitly:

```python
verify_checkpoint_identity(payload)
# legacy identifier: accepted unverified
```

A schema 10 checkpoint can enter, is migrated and restored, and its next
checkpoint is written as schema 11; from then on it belongs to the verifiable
chain.

This is not a defect while it remains an explicit compatibility boundary. It
does mean that "every checkpoint has a cryptographically verified identity" is
false: current ones do, some accepted historical ones do not.

### F-05 — restart is not an uninterrupted run

`tests/integration/test_restart_equivalence.py` develops a non-trivial organism
before the restart. It checks a non-empty graph, more than 10 experiences,
episodic memory, an ACTIVE private model, social knowledge, the replay guard and
narrative; it then serializes, builds a new runtime and restores.

Semantically conserved: organism id, tick, cognitive nodes, experience ids, the
ACTIVE model and its state, social knowledge and replay protection. This is
stronger evidence than `checkpoint == restore(checkpoint)`.

The test also records that "Exactly one transition is absent": the experience
whose window opened before the restart and would have closed after it. The
pending frame belongs to transient `MUST_RESET` state.

This is not an identity defect, but:

```text
restart ≠ uninterrupted execution

restart = same organism
        + same consolidated knowledge
        + explicit discontinuity in in-flight experience
        + reacclimation
```

Any scientific claim must keep that distinction.

### F-06 — restore can be a transformation

`restore_resident_with_canonical_cognition()` restores a historical checkpoint
that had no genome or cognitive graph and adds the modern canonical cognition,
recording `transform="canonical-cognition-adoption"`. Generic restore reproduces
the same checkpoint historically.

```text
historical restore ≠ owner-facing / live restore
```

The transform is not silent at lineage level. A longitudinal experiment must
nevertheless choose the entry point deliberately, because restoring the same
checkpoint through the two entry points can produce different organisms.

### F-07 — `observatory` holds both observer and launcher

`observatory/server.py` defines itself as a passive consumer.
`observatory/resident.py` is not a passive UI: it constructs
`OrganismRuntime(...)` or calls `restore_resident_with_canonical_cognition(...)`,
owns the optional Private SLM path, and reads
`runtime.experience_ledger.records` directly to build corpus and tokenizer.

No evidence was found that the web UI writes cognition, so this audit does not
conclude that Observatory contaminates the organism. It does conclude:

```text
namespace observatory ≠ strictly presentation
```

Any package-based inference of the form "it is in `observatory`, therefore it is
passive" is false.

### F-08 — silent failure when writing the capture manifest

`observatory/resident.py` contains:

```python
try:
    ...
    write_capture_manifest(manifest_path, manifest)
except Exception:
    pass
```

This does not damage the organism. It can destroy observational evidence without
failing the run:

```text
organism works
+ instrumentation fails
+ reader interprets missing observation as missing capability
```

The failure must become an explicit error or explicit telemetry.

### F-09 — World is a family of environments

No evidence supports a single canonical World. These remain active:

- `symbiont_world`;
- Physics3D;
- LocalHabitat;
- SocialHabitat;
- SharedHabitat;
- experimental apparatus such as `CausalBody`.

"World" is currently an architectural concept rather than a single technical
authority. `symbiont_world` still has consumers and studies; nothing should be
removed before those are traced.

## 5. Cognition: existence versus efficacy

The runtime is not a single cognitive mechanism. At least these families are
active:

```text
CognitiveGraph
CognitiveBridge
prediction / ShadowPrediction
MemoryConsolidator
EvidenceRevisionLedger
SelfModel
attention
sensorimotor acquisition
competence development
causal evidence
controllability
agency
prospective/executive admission
ResidentGenerativeCognition
ExperienceLedger
EpisodicExperienceMemory
PrivateModelRegistry
private model inference
social evidence
```

Mechanically demonstrated:

- the components exist, receive data, are serialized and are restored;
- some alter decisions;
- models can move SHADOW → ACTIVE;
- ancestry is preserved;
- generative cognition has persistent state;
- sensorimotor learning produces effects and competences.

Not demonstrated by the runtime alone:

- that generative cognition improves behaviour;
- that ancestry improves learning;
- that the private model is causally useful;
- that the CognitiveGraph has general utility;
- that transferred competences are useful in another body;
- that executive outcome learning improves decisions.

## 6. Governance result

At audit time GitHub reported:

```text
ruleset: Protect main governed publication
enforcement: active
target: main
bypass actors: []

rules:
  no deletion
  no non-fast-forward
  required status: governed-ci-gate
```

The earlier statement "main has no branch protection or ruleset" is therefore
rejected for the current state.

`agentctl run start` accepts `--input-mode snapshot` and
`--input-mode protocol-generated`, so E8 and protocols that build their input
deterministically no longer need an invented external snapshot.

| Invariant | State |
| --- | --- |
| `main` requires the gate | guaranteed |
| human bypass without the gate | not available under the current ruleset |
| SCIENTIFIC work uses the governed launcher | partially guaranteed |
| run provenance | strong |
| execution fingerprint | implemented |
| protocol-generated input | implemented |
| equivalence is a universal classifier | not guaranteed, correctly |
| green CI means all scientific evidence ran | false |

`2ac4296d` still showed a global `pending` status when queried although the
commit was already on `main`. The ruleset requires the check on the publication;
it does not turn each later SHA into a claim that every possible scientific
experiment ran.

## 7. Invariants

| Invariant | State |
| --- | --- |
| organism identity survives restart | guaranteed |
| identity survives Physics3D re-embodiment | guaranteed |
| CognitiveGraph survives re-embodiment | guaranteed |
| experience and model registry survive | guaranteed |
| learned sensorimotor state survives | guaranteed on the canonical Physics3D path |
| previous execution authority is reused | correctly not guaranteed |
| Body state survives a Body change | correctly contradicted |
| every historical checkpoint verifies identity | not guaranteed |
| restart equals uninterrupted execution | contradicted |
| every `Symbiont` has identical longitudinal semantics | contradicted |
| the web UI creates knowledge | not found |
| the `observatory` package is purely passive | contradicted |
| `World` has a single runtime authority | not demonstrated |
| existence of generative cognition demonstrates utility | not guaranteed |
| private-model ancestry improves learning | not guaranteed |
| `main` can be written bypassing every gate | contradicted at this commit |

## 8. Divergences

The main divergence:

```text
intended concept:
  the Symbiont keeps all acquired knowledge

canonical Physics3D re-embodiment:
  very close to that rule

clean-embodiment Symbiont:
  reinitializes part of the embodiment-specific inference
```

This audit does not claim that either implementation is wrong. It does claim
that they cannot keep being treated as the same semantics without specifying
which knowledge belongs to the organism and which authority belongs to the
embodiment.

## 9. Relation to the earlier audit

The
[Longitudinal Integrity Audit](2026-10-02-longitudinal-integrity-audit.md)
stored the same day already contains findings that are resolved at
`main@2ac4296d`:

| Earlier finding | State at this commit |
| --- | --- |
| LI-01 | resolved — see F-03 |
| LI-02 | resolved for current schemas — see F-03 |
| LI-03 / LI-05 | resolved |
| GOV-01 | resolved — see §6 |

That audit must be updated or have those findings marked resolved so later
readers do not work from an outdated photograph. Done: it now carries a
resolution record per finding.

## 10. Required follow-up

Cleanup and refactoring do not come first. In order:

1. **Unify the longitudinal contract.** Decide whether
   `core/orchestration/symbiont.py::Symbiont` must really differ from
   `OrganismRuntime` on re-embodiment, and either document and test it as such
   or converge it. (F-01)
2. **Close the Observatory/runtime boundary.** Separate the launcher/resident
   from the observational layer and remove the `except Exception: pass` around
   evidence/manifest writing. (F-07, F-08)
3. **Build an executable continuity matrix.** `src/symbiont/host/continuity.py`
   is the base. Extend it to verify by property
   `state -> checkpoint -> restore -> re-embodiment -> checkpoint`, not only
   field presence. (F-01, F-05, F-06)
4. **Test functional transfer.** Knowledge is known to survive; when it is
   useful after a body change is not. (§5)
5. **Audit World as an independent concept.** Determine which environments are
   apparatus, which constitute World, and whether `symbiont_world` still has an
   exclusive responsibility. (F-09)
6. **Only then simplify legacy.**

The planning index is [`docs/roadmap.md`](../../../docs/roadmap.md); the
continuity contract is
[Longitudinal Integrity v1](../../../docs/design/core/longitudinal-integrity-v1.md).

## 11. Conclusion

The organism no longer appears fundamentally fragile against checkpoint, restart
and re-embodiment. Recent corrections closed several serious holes, and the main
Physics3D path now has a reasonably coherent longitudinal separation.

The main risk has moved: Symbiont has good local guarantees but still more than
one operational definition of what belongs to the organism, what belongs to the
embodiment and what "preserving knowledge" means. While that ambiguity exists,
two apparently equivalent experiments can be studying organisms with different
longitudinal rules, which is scientifically more dangerous than an imperfect UI
or code debt.

## 12. Claims this audit does not make

This audit does not establish:

- that either re-embodiment semantics is incorrect;
- that Observatory contaminates the organism;
- that `symbiont_world` should be removed;
- that accepting unverified schema 10 identity is a defect;
- that preservation of knowledge proves useful cross-body transfer;
- that private-model ancestry improves learning;
- that generative cognition improves organism behaviour;
- that a green gate means every scientific experiment ran.

Those remain implementation or experimental questions and require separate
evidence.

## 13. Resolution record

Recorded after the audit, against `main@3246a39d`. "Resolved" means the code or
contract change exists with a test that fails if it regresses; it is not owner
acceptance. Decisions that are the owner's are listed, not taken.

| ID | Resolution | Evidence | Left to the owner |
| --- | --- | --- | --- |
| F-01 | The reduced seed's transplant semantics are declared per attribute in `REDUCED_SEED_REGISTER`; each attribute where it discards or ungrounds what canonical re-embodiment keeps is marked. The module and class docstrings no longer present the seed as the same longitudinal contract. | `tests/unit/host/test_reduced_seed_register.py`; [Lifecycle Continuity Contract v1](../../../docs/design/core/lifecycle-continuity-contract-v1.md) §7 | Whether the two semantics converge. Changing the seed changes the apparatus of the embodiment falsification studies. |
| F-02 | No action: resolved-positive. | `tests/integration/test_reembodiment_continuity.py` | — |
| F-03 | No action: resolved-positive. | `tests/unit/host/test_strict_restore.py` | — |
| F-04 | Acceptance of an unverified legacy checkpoint is now recorded durably: every later save carries `checkpoint_lineage.unverified_legacy_origin`. | `tests/unit/core/test_canonical_birth.py`; contract §6 | Whether and when legacy checkpoints stop being accepted. |
| F-05 | The discontinuity is stated in one place as part of the contract and stays pinned by the restart test. | `tests/integration/test_restart_equivalence.py`; contract §5 | — |
| F-06 | One adoption path for every runtime layer (`runtime_class`); the resident launcher's hand-inlined copy is removed. `checkpoint_lineage.transforms` is carried into every later save, so an adopted organism stays identifiable after its next checkpoint. Before this the transform existed only on the in-memory payload. | `tests/unit/core/test_canonical_birth.py`; contract §4 and §6 | — |
| F-07 | The resident and replay launchers moved to `symbiont_lab.cli.observed_resident` and `symbiont_lab.cli.observed_replay`. No `observatory` module constructs, restores or drives an organism. A second launcher found during the fix (`main` inside `observatory/adapter.py`) was moved as well. | `tests/experimental_integrity/test_observatory_passive_boundary.py` | — |
| F-08 | A manifest write failure is reported on stderr and makes the launcher exit non-zero after the organism is saved. The organism is not stopped by an observer failure. | `tests/unit/lab/test_observed_resident_manifest.py` | — |
| F-09 | Every environment family is inventoried with owner, role, consumers and state. Nothing was removed. Stale World specification paths in docstrings were corrected. | [World Responsibility Map v1](../../../docs/design/world/world-responsibility-map-v1.md) | Location of the habitat classes, status of Physics3D surroundings, retirement of legacy environments, reserved meaning of "World". |

Follow-up items of §10:

| Item | State |
| --- | --- |
| 1. Unify the longitudinal contract | Contract written and executable; convergence is the owner's decision. |
| 2. Close the Observatory/runtime boundary | Done (F-07, F-08). |
| 3. Executable continuity matrix | Done: `test_the_whole_lifecycle_holds_per_register_entry` checks state → checkpoint → restore → checkpoint → re-embodiment → restore → checkpoint per register entry. |
| 4. Functional transfer | Not run. The preregistration draft exists and is unapproved: [Re-embodiment Functional Transfer v1](../../../docs/design/experimentation/reembodiment-functional-transfer-v1.md). Running it needs owner approval of the apparatus and numbers. |
| 5. Audit World | Done as an inventory (F-09). |
| 6. Simplify legacy | Not started, by design: it follows the owner decisions above. |

One further defect of the F-08 kind was found while fixing it: with
`--enable-slm` the resident launcher added an `apparatus` block to the snapshot
that the closed snapshot schema rejected, so a schema-validating consumer would
have dropped every snapshot of such a run. The block is now part of the closed
contract (`apparatus.slm_service`, bounded) and checked by
`tests/unit/lab/test_observed_resident_manifest.py`.

Two entry points changed as a consequence of F-07: `python observatory/resident.py`
and `python observatory/adapter.py` no longer exist; the launchers are
`python -m symbiont_lab.cli.observed_resident` and
`python -m symbiont_lab.cli.observed_replay`. Accepted ADR-0018 still names the
old path and is not edited here.
