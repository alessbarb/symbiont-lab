---
id: design.core.epistemic-ownership-and-claim-levels-v1
title: "Epistemic Ownership and Claim Levels v1"
document_type: design
domain: core
status: proposed
canonical: false
implementation_status: design
date: 2026-10-04
depends_on:
  - docs/governance/constitution.md
  - docs/design/core/lifecycle-continuity-contract-v1.md
language: en
---

# Epistemic Ownership and Claim Levels v1

## 1. Purpose and limits

The runtime has several representations that can encode evidence, relations,
predictions, or hypotheses. Similar-looking representations are not assumed to
be duplicates. This document makes no consolidation or promotion decision. It
sets the minimum inventory needed before changing an epistemic subsystem or
making a functional claim about it.

The inventory is a design contract, not proof that every row has been audited
end-to-end. Unknown ownership or consumption is recorded as unknown; it must
not be filled by inference from a class name or a checkpoint field.

## 2. Required ownership record

Before a subsystem is merged, extended, or described as functionally capable,
its owner must record:

| Field | Required question |
|---|---|
| Canonical representation | What state does this subsystem own, and what does it explicitly not own? |
| Assertion semantics | What proposition or estimate can it represent? |
| Evidence source | Which witnessed events or upstream records can support an entry? |
| Revision and invalidation | How can contradictory evidence revise, retract, age, or invalidate it? |
| Persistence boundary | Which serializer/checkpoint field owns it, and what continuity class applies? |
| Consumer | Which production decision reads it, and where is that path tested? |
| Authority boundary | Can it authorize action, mutate factual world state, or only propose/inform? |
| Evaluation | Which controlled comparison could show benefit, and what result would falsify it? |

An attribute in a checkpoint register establishes classification and persistence
behavior only. It does not establish evidence quality, consumer use, or utility.

## 3. Evidence levels for capability claims

Use the strongest level actually demonstrated, not the strongest level the code
could theoretically support.

| Level | Claim | Minimum evidence |
|---|---|---|
| E0 — Present | A representation or mechanism exists | Owner, bounds, and runtime construction are identified |
| E1 — Durable | State survives the declared lifecycle boundary | Round-trip/re-embodiment tests verify the owning field and identity boundary |
| E2 — Consumed | A production path reads it and a decision can depend on it | A traced consumer path plus a test that distinguishes the consumed from unused state |
| E3 — Useful | It improves a prespecified outcome | Controlled comparison, matched budgets, adequate repetitions, and a defined analysis |
| E4 — Causal | An intervention on it caused a specified outcome | Preregistered intervention/ablation with controls and the applicable scientific review |

E0/E1 are engineering properties. E2 is a functional integration property.
E3/E4 are empirical claims and cannot be inferred from unit tests, persistence,
code surface, or a successful campaign runner.

## 4. Initial subsystem inventory

This list is a set of distinct candidate owners to trace, not a claim that they
are equivalent or already have complete contracts:

| Candidate owner | Boundary to preserve while auditing | Required next evidence |
|---|---|---|
| CognitiveGraph / cognitive bridge | Graph structure and concept updates are not ground truth about the external world | Trace sources, revision path, checkpoint owner, and decisions consuming graph state |
| SignalKnowledge | Signal relations must not silently become causal or factual claims | Trace its evidence source and every production consumer; distinguish relation semantics from causal evidence |
| EvidenceRevisionLedger | Revision history must remain distinct from current accepted content | Identify canonical owner, lifecycle behavior, and consuming reconciliation path |
| Predictive learning / predictor credit | A prediction or credit estimate is not an observation | Trace target, outcome reconciliation, promotion/retirement, and decision consumer |
| Causal evidence / sensorimotor evidence | Interventions, observations, and derived causal candidates need explicit provenance | Trace the source event and ensure candidate relations are not promoted to world facts |
| Agency acquisition / competence effects | Acquired competence and its evidence are not execution permission | Trace acquisition evidence, persistence, action selection, and separately held execution bindings |
| Generative hypotheses | Counterfactual or generated hypotheses are proposals, not factual state | Trace factual reconciliation, rejection path, persistent state, and decision consumer |
| Private models and ancestry | Model persistence/lineage is distinct from model accuracy or lineage benefit | Verify checkpoint lineage; separately evaluate prediction quality and ancestry ablation |
| Episodic memory | Retained episode is not automatically retrieved or decision-relevant memory | Trace indexing, retrieval, consumption, and any compression/revision policy |
| Social evidence | A peer claim remains attributed to its source until evidence reconciliation | Trace publication, reception, assessment, persistence, reconciliation, and decision consequence |
| Symbol/sequence grounding | Grounding links require explicit observation/interaction provenance | Trace the grounding event and downstream consumers; separate labels from validated referents |
| Provenance | Provenance records how a state/result was produced; it is not evidence for the claim itself | Verify propagation and ensure consumers do not treat metadata as factual support |

The rows deliberately do not prescribe a common data model. A merge is allowed
only after the audit establishes identical assertion semantics, evidence
requirements, revision rules, lifecycle ownership, and consumer authority.

## 5. Current evidence statements

- Model ancestry that survives restore is a durability result (at most E1). It
  does not demonstrate improved learning or adaptation (E3/E4).
- Generative hypotheses, scheduling, reconciliation, and persistence establish
  implemented architecture and testable state transitions (E0/E1). They do not
  demonstrate decision benefit or causal outcome attribution (E3/E4).
- Re-embodiment integration tests establish selected mechanical preservation
  and withdrawal of execution authority. They do not establish useful transfer.
- No scientific run is authorized by this document. Any E3/E4 claim must satisfy
  the repository's experiment, review, and publication gates independently.

## 6. Acceptance condition

This design remains proposed until an owner-approved audit fills every required
field in §2 for the candidate systems in §4, with links to implementation and
tests. Missing or conflicting ownership is a finding to resolve; it is not
permission to merge systems or infer capability.
