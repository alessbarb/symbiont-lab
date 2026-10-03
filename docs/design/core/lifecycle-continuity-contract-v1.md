---
id: design.core.lifecycle-continuity-contract-v1
title: "Lifecycle Continuity Contract v1"
document_type: design
domain: core
status: proposed
canonical: false
implementation_status: implemented
date: 2026-10-02
depends_on:
  - docs/governance/constitution.md
  - docs/design/core/longitudinal-integrity-v1.md
source_audit: research/audits/current/2026-10-02-current-state-architecture-audit.md
language: en
---

# Lifecycle Continuity Contract v1

## 1. Purpose

[Longitudinal Integrity v1](longitudinal-integrity-v1.md) established that state
survives. The
[current-state audit](../../../lab/research/audits/current/2026-10-02-current-state-architecture-audit.md)
found that what "survives" means is still decided in more than one place: two
re-embodiment semantics, two restore semantics, and a restart that is not an
uninterrupted run.

This document is the single description of every lifecycle operation and of what
each one does to each kind of state. It adds no mechanism of its own. Every rule
below is stated once in an executable register and checked by a named test; the
prose only says where to look.

It records the code as it is. Where two paths differ, the difference is declared
here and pinned by a test. Whether they should converge is an owner decision
(§8).

## 2. Who owns what

| Owner | Meaning | Lifetime |
| --- | --- | --- |
| Symbiont | The longitudinal subject: identity, organism time, genome and expression, cognition, experience, models, social knowledge, learned sensorimotor knowledge | The organism's whole life, across restarts and Bodies |
| Body | Physical and physiological state of one Body | One Body |
| Embodiment | One continuous period of one Symbiont in one Body: the episode, its execution authority and its in-flight motor state | One episode; closed and archived when the Body changes |
| Process | Handles, caches and one-tick traces of one running process | One process |
| Apparatus | Configuration and history written around the organism by the Lab | Recorded as provenance, reapplied by the launcher |

## 3. State classes

Each runtime attribute has exactly one continuity class and one re-embodiment
treatment in `src/symbiont/host/continuity.py::REGISTER`.

| Question | Class in the register | On restart | On canonical re-embodiment |
| --- | --- | --- | --- |
| Belongs to the Symbiont and may never be erased | `MUST_PRESERVE` with `Reembodiment.PRESERVED` | restored exactly | carried exactly |
| Belongs to the Body and is replaced | `MUST_PRESERVE` with `Reembodiment.REPLACED` | restored exactly (same Body) | taken from the fresh Body |
| Belongs to the Embodiment and is closed | `APPARATUS_FIELDS` (`embodiment_episode`) | restored | closed and archived; a new episode starts |
| Kept as historical knowledge without authority over the current Body | `MUST_INVALIDATE_AUTHORITY` with `Reembodiment.INVALIDATED` | restored | knowledge carried, execution bindings and in-flight commitment withdrawn |
| May be recomputed | `MAY_RECOMPUTE` | rebuilt from preserved state | rebuilt |
| Must be reset or invalidated | `MUST_RESET` | never crosses the process boundary | not applicable |
| Apparatus configuration | `MUST_REAPPLY_CONFIG` | recorded in provenance and reapplied | reapplied |

`lab/tests/unit/host/test_continuity_register.py` fails when a runtime attribute or
checkpoint field is unclassified.

### 3.1 BodySchema is retained knowledge, not current-body authority

`body_schema` is a bounded learned representation (sensory-part, cognitive-region,
dependency, and body-boundary evidence). The checkpoint does not currently tag
each item with a body/episode provenance class. Therefore a preserved BodySchema
after re-embodiment is a longitudinal prior that may be stale or inapplicable;
it is not a verified description of the new Body. Current physical facts come
from the new Body's sensors and physiology. Execution authority is separately
withdrawn by the action-domain transition. A consumer must not use preserved
BodySchema entries as actuator bindings or as proof of present anatomy.

Evidence scope: `lab/tests/integration/test_reembodiment_continuity.py` verifies
BodySchema preservation through the register lifecycle and verifies execution
bindings are not valid after restore. It does not establish that every
BodySchema consumer handles all retained evidence as a fallible prior, nor that
retained BodySchema improves adaptation. Per-item body provenance remains an
open design limitation, not a demonstrated semantic guarantee.

## 4. Lifecycle operations

| Operation | Entry point | What it is | What it is not |
| --- | --- | --- | --- |
| Save | `OrganismRuntime.checkpoint()` / `save()` | State identity over the whole organism payload, chained to its parent | A copy of the Body, the weights or the Lab journal |
| Restart | `<Runtime>.from_checkpoint(payload)` on the same Body | The same organism with the state that was saved | An uninterrupted run (§5) |
| Historical restore | `OrganismRuntime.from_checkpoint(payload)` | Reproduces the individual exactly as saved, including the absence of cognition in a cognition-less checkpoint | An upgrade |
| Owner-facing restore | `restore_resident_with_canonical_cognition(payload, runtime_class=...)` | Historical restore plus the `canonical-cognition-adoption` transform when genome and graph are absent | A neutral restore: it can produce a different organism from the same checkpoint (§6) |
| Canonical re-embodiment | `symbiont.core.embodiment.transition.prepare_fresh_embodiment_checkpoint` | The Symbiont moved into a fresh Body; knowledge carried, authority withdrawn | A reset of cognition |
| Reduced-seed transplant | `Individual.transplant_to` → `CleanEmbodimentSeed.begin_new_embodiment` | The clean-embodiment apparatus: identity, time, genotype and expression kept; embodiment-specific inference restarted from naive | Canonical re-embodiment (§7) |
| Temporal decontamination | `symbiont_lab.physics3d.reembodiment.migrate_temporal_domains` | Corrects a contaminated clock coordinate and records it | A reconstruction of the physiology already produced under that clock |

Every operation that changes organism state without the organism living through
it is an authorized transform. It re-identifies the checkpoint and names itself
in `checkpoint_lineage.transforms`.

## 5. Restart is not an uninterrupted run

A restart preserves the organism and its consolidated state. Its future is not
the future of a run that never stopped:

- one-tick causal traces are `MUST_RESET`, so the transition whose window spans
  the process boundary is never recorded;
- every restore opens the reacclimation gate, which pauses structural
  consolidation for `kernel_limits.reacclimation_ticks`.

```text
restart = same organism
        + same consolidated knowledge
        + one unrecorded transition
        + reacclimation
```

`symbiont/tests/integration/test_restart_equivalence.py` fixes the set of fields that may
differ from an uninterrupted run and asserts that exactly one transition is
absent. A claim of restart equivalence stronger than this is not supported.

## 6. Checkpoint history that outlives the save

Two facts about an organism's past are not properties of one save:

- `checkpoint_lineage.transforms` — the authorized transforms it has been
  through;
- `checkpoint_lineage.unverified_legacy_origin` — some ancestor checkpoint was
  accepted without a verifiable identity. Schema 10 and earlier recorded an
  identifier that covered only base-runtime fields and was never checked; such a
  checkpoint is still accepted, deliberately, as a compatibility boundary.

Both are carried into every later save (`lineage_history` in
`src/symbiont/host/checkpoint.py`, restored into the runtime and written back by
`checkpoint()`). Before this, a transform was visible only on the in-memory
payload that was restored and vanished at the organism's next save, and nothing
recorded that a verifiable chain began at an unverified checkpoint.

Consequences:

- "every checkpoint has a verified identity" is false; "every checkpoint saved by
  a current runtime has a verified identity, and says whether its history starts
  at an unverified one" is true;
- an experiment that needs historical reproduction must use the historical
  restore, and can check afterwards that `transforms` does not contain
  `canonical-cognition-adoption`;
- owner-facing launchers share one adoption path for every runtime layer, so the
  CLI and the resident launcher cannot adopt differently.

Tests: `symbiont/tests/unit/core/test_canonical_birth.py`,
`tests/compatibility/checkpoint_v10/`.

### 6.1 Legacy admission policy (owner, 2026-10-02; issue #276)

1. **Admission.** Checkpoints saved by schema 10 and earlier remain restorable.
   No retirement date is set.
2. **Marking.** Every later save of such an organism carries
   `unverified_legacy_origin`; it cannot be shed by saving, transforming or
   re-embodying.
3. **Refusal where origin matters.** `require_verified_origin(payload)` fails
   closed. The governed launcher applies it to scientific inputs:
   `agentctl run start` refuses `confirmation` and `held-out` scopes when the
   snapshot organism has an unverified origin, and also when its origin cannot
   be determined. Only an explicit verified origin passes.
4. **Evidence.** A snapshot manifest records `unverified_legacy_origin`, and the
   run receipt (`execution.json`, `scientific_input.snapshot`) carries it, so any
   result can be traced to a verified or an unverified subject.
5. **No indefinite admission by accident.** `LEGACY_ADMISSION_REVIEW_AT_SCHEMA`
   (currently 13) names the checkpoint schema at which this policy must be
   decided again. A test fails when the schema reaches it, until the legacy path
   is retired or the review version is deliberately moved.

Retirement, when decided, is an explicit import step: a one-time migration that
produces a current-schema checkpoint still marked `unverified_legacy_origin`,
after which direct restore of schema 10 can be removed. It is not designed
further here because nothing has been retired.

Inventory at the time of the decision (this workstation, repository state
directories and `~/.local/state/symbiont`): one real organism of schema 10,
`org-2df92a9d8fda` (saved at tick 16366), with its bundle and five retained
checkpoints. The fixtures under `tests/compatibility/checkpoint_v10/` are real
schema-10 payloads kept for the compatibility tests.

Tests: `tests/unit/host/test_legacy_admission_policy.py`,
`tests/unit/lab/experiments/test_snapshot_origin.py`,
`tests/unit/test_checkout_isolation.py::test_run_start_requires_a_verified_origin_for_confirmatory_scopes`.

## 7. Two transplant semantics

Canonical re-embodiment and the reduced seed's transplant answer the question
"what belongs to the organism?" differently for embodiment-specific inference.

| State | Canonical re-embodiment (`OrganismRuntime`) | Reduced seed (`CleanEmbodimentSeed`) |
| --- | --- | --- |
| Identity, organism time, genome, expression | preserved | preserved |
| BodySchema | preserved | reset to naive |
| Sensorimotor dynamics, effects, causal evidence, controllability, agency | preserved as knowledge | reset to naive |
| Competences | preserved | preserved, effect grounding cleared |
| Execution bindings, surface, in-flight commitment | invalidated | reset |
| CognitiveGraph, experience, private models, social knowledge | preserved | not part of the reduced seed |

The reduced seed is the apparatus of the clean-embodiment studies
(`symbiont_lab.studies.embodiment`). Its semantics are declared per attribute in
`REDUCED_SEED_REGISTER`; every attribute where it discards or ungrounds something
canonical re-embodiment keeps is marked `diverges`.
`symbiont/tests/unit/host/test_reduced_seed_register.py` checks that the register covers
every attribute of the class, that the declared divergences are exactly the real
ones, and that a transplant treats each attribute as declared.

Rule for claims: a result obtained with the reduced seed says nothing about
retained knowledge after canonical re-embodiment, and the reverse. A study must
name which of the two it used.

### 7.1 Decision and enforcement (owner, 2026-10-02; issue #273)

The divergence is intentional and stays. The reduced seed is the subject of the
clean-embodiment falsification apparatus; converging it would change that
apparatus and the comparability of its recorded results. It is no longer called
"Symbiont": the class is `CleanEmbodimentSeed`, and `symbiont.core` exports no
`Symbiont` class.

Per divergent state item:

| State | Canonical owner | In the reduced seed |
| --- | --- | --- |
| BodySchema | Symbiont-owned knowledge | treated as embodiment-owned, restarted |
| Sensorimotor dynamics, effects, causal evidence, controllability, agency | Symbiont-owned knowledge | treated as embodiment-owned, restarted |
| Competence effect grounding | Symbiont-owned knowledge | cleared; the competence itself is kept |
| Execution bindings, surface, in-flight commitment | embodiment-owned authority | embodiment-owned authority |

Each contract has an identifier, `LongitudinalContract` in
`src/symbiont/host/continuity.py`:

- `canonical-reembodiment-v1` — `OrganismRuntime` and its subclasses;
- `reduced-seed-transplant-v1` — `CleanEmbodimentSeed` / `Individual`.

Both classes carry it as `LONGITUDINAL_CONTRACT`. Every module that builds a
subject declares the same constant at module level, the experiment runner writes
it to the run manifest (`longitudinal_contract`; `null` for protocols that build
no longitudinal subject), and
`tests/experimental_integrity/test_longitudinal_contract_declaration.py` fails
when a module that imports either subject does not declare its contract or
imports subjects of both.

Users of the reduced seed at the time of the decision:
`studies.embodiment.{causal_revision_sequence, heredity_leakage_challenge,
integrity_gates, label_invariance}`, `studies.genetics.genome_causal_validation`
and `symbiont_lab.world.adapter` (the `experimental_clean` World path). Users of
canonical re-embodiment: `symbiont_lab.physics3d.{runtime, reembodiment}`.

## 8. Owner decisions

1. **Convergence.** Decided 2026-10-02: no convergence; see §7.1. A later
   decision to converge or retire the seed is a SCIENTIFIC change with its own
   apparatus-impact record.
2. **Legacy sunset.** Decided 2026-10-02: admitted without a date, refused
   where a verified origin is required, and reviewed at a named schema version;
   see §6.1.
3. **Functional transfer.** Preservation is established; usefulness is not. The
   unapproved preregistration draft is
   [Re-embodiment Functional Transfer v1](../experimentation/reembodiment-functional-transfer-v1.md).

## 9. Executable references

| Rule | Register | Test |
| --- | --- | --- |
| Every runtime attribute is classified | `REGISTER` | `lab/tests/unit/host/test_continuity_register.py` |
| Current-schema checkpoints fail closed | `required_checkpoint_fields` | `symbiont/tests/unit/host/test_strict_restore.py` |
| Whole lifecycle per register entry: state → checkpoint → restore → checkpoint → re-embodiment → restore → checkpoint | `REGISTER` | `lab/tests/integration/test_reembodiment_continuity.py::test_the_whole_lifecycle_holds_per_register_entry` |
| Restart differs from an uninterrupted run only on the declared surface | — | `symbiont/tests/integration/test_restart_equivalence.py` |
| Transforms and unverified legacy origin are durable | `lineage_history` | `symbiont/tests/unit/core/test_canonical_birth.py` |
| Reduced-seed transplant contract and its divergences | `REDUCED_SEED_REGISTER` | `symbiont/tests/unit/host/test_reduced_seed_register.py` |

## 10. Claims this contract does not make

- that either transplant semantics is the scientifically correct one;
- that preserved knowledge is useful in a new Body;
- that a restart is equivalent to never having stopped;
- that a checkpoint of unverified legacy origin is untrustworthy, or trustworthy.
