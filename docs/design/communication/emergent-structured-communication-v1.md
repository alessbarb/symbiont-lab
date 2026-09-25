---
canonical_id: "design.general.emergent-structured-communication-v1"
current_path: "docs/design/emergent-structured-communication-v1.md"
target_path: "docs/design/communication/emergent-structured-communication-v1.md"
document_type: "design"
diataxis_kind: null
domain: "communication"
source_language: "es"
target_language: "en"
status: "unclassified"
canonical: false
supersedes: []
depends_on: []
review_required: true
evidence: []
_extracted_title: "Emergent Structured Communication v1"
extends: []
implementation_status: "unknown"
implements: []
migrated_on: "2026-09-25"
language: "en"
last_reviewed: null
---

# Emergent Structured Communication v1

> Give Symbionts capabilities and constraints, not linguistic answers.

This phase replaces the prescriptive design of Proto-language v1 before its scientific execution. It retains only the general substrate of messages, local grounding, costs, limits, and replay; it does not retain slots, roles, grammar, target pairs, or compositionality objectives.

## Operational principle

**WE PROVIDE:** channel, symbols, memory, cost, limits, experience.

**WE DO NOT PROVIDE:** meaning, grammar, roles, composition, syntax, optimal messages.

The channel allows `SILENCE`, a symbol, or a bounded variable-length sequence (maximum 4 in the baseline). Symbols are opaque IDs and the receiver only creates associations after exposure and local experience. The policy lives in `symbiont.modeling`; the laboratory only sets contacts, resources, conditions, and evaluator-side metrics.

## Contracts and boundaries

`SymbolSequence`, `SequenceMessage`, `SequenceDecisionRecord`, and `SequenceGroundingLedger` are serializable and do not contain world labels, roles, or translations. The association is exact to the received message: there is no privileged path that factors positions or rewards reuse. The sequence ledger is separate from the private SLM ledger and does not transfer weights, corpus, or adapters. Offspring begin without associations.

Decisions preserve candidate digest, local state, selected receiver, cost, and tick. Contact opportunities are experimental control; the harness does not select the content. Observatory exposes only passive state.

## Preregistered study

`learning.emergent-structured-communication` compares `NO SIGNAL`, `RANDOM SIGNAL`, and `AUTONOMOUS UNSTRUCTURED CHANNEL` on seeds `101, 127, 149`, with opaque vocabulary, variable length, and bounded cost. Structure analysis (holistic, partially structured, or productive) is performed later on traces and never enters the policy. A holdout or factorial solution is not forced: if the code is holistic or does not work, that result is preserved.

The autonomous condition does not receive meaning mapping, target sequence, roles, slots, latent labels, or ground truth. ID permutation is an arbitrariness control, not a privileged training route.

## Status

The capability is implemented and the base study was executed locally on the three preregistered seeds. The closure is functional and bounded: autonomous communication was useful, non-trivial, and replay-safe. Compositional productivity was not observed nor is it claimed; that property is not an architectural requirement and remains outside the closure.
