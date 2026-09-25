---
id: design.general.futuro-cultural
title: "Cultural Future"
document_type: design
domain: communication
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Cultural Foundation v1

<!-- markdownlint-disable MD025 -->

> Consolidated from: cultural-foundation-v1.md, private-slm-and-cultural-foundation.md, cumulative-culture-v1.md

## Scope

This phase adds the smallest bounded substrate for social knowledge without
sharing private models, adapters, weights, corpora, telemetry, or host actions.
`SocialClaim` is a report in native token space. It is not an observation and
cannot enter the Private SLM corpus as a target in this phase.

## Epistemic boundary

`SocialClaim`, `SocialSupported`, and `SocialContradicted` are separate from
the private `ExperienceRecord` states. Local confirmation is an assessment
with a new local evidence id; it does not rewrite the received claim or turn it
into `OBSERVED`. Contradictions remain alongside the original claim.

## Causal genealogy

`ClaimGraph` is a bounded DAG. Every retransmission or bounded token mutation
creates a new claim id and points to its parent. Root evidence ids are carried
through all descendants. Independent evidence is counted only by distinct root
evidence ids, never by holders, hops, senders, or copies. Cycles, missing
parents, duplicate ids, malformed claims, and over-depth ancestry fail closed.

The receiving ledger imports the delivered ancestry for replay and lineage
inspection. This is metadata about claims, not the sender's private memory.

## Local social memory and transport

`SocialEvidenceLedger` is organism-owned and separate from `ExperienceLedger`.
It stores received/held claims, assessments, freshness, bounded forgetting,
checkpoint state, and explicit communication costs. `SocialChannel` is a
laboratory-controlled in-memory transport with an allow-list and delivery
ceiling. It has no sockets, peer discovery, host access, or autonomous network
behavior.

The organism runtime exposes only bounded claim operations. A clonal offspring
starts with an empty social ledger, just as it starts without acquired private
models and corpus. Observatory integration is projection-only and must never
mutate this state.

## Deferred behaviour

The mechanism supports retain, test, support, contradict, retransmit, mutate,
and forget. It does not hardcode cooperation, truth detection, consensus,
roles, reputation, or a sharing policy. Cultural utility and rumor behaviour
are study questions, not runtime assumptions.

## Closure gates

The preregistered study `learning.cultural-foundation` covers faithful
transmission (C1), anti-copy inflation (C2), independent corroboration (C3),
contradiction (C4), utility (C5), rumor control (C6), and persistence after
the discoverer disappears (C7). Cultural Foundation v1 is closed only if all
seven gates pass in the declared scope; implementation and unit tests alone
are insufficient.

---

# Private SLM & Cultural Foundation

## Status

**Private SLM v1: implemented and scientifically closed in its preregistered scope.**

Biological Closure v1 remains the prerequisite boundary. The private-model phase has now demonstrated organism-owned predictive learning, opaque-token invariance, explicit model lineage, bounded incremental adaptation from a prior private model and promotion through evidence-gated shadow evaluation without pretrained human knowledge or cultural transfer.

Negative results from the original regime-shift controls remain part of the evidence record and are not retroactively reclassified as positive. The closing adaptation study is a separate preregistered experiment that tests a capability found to be absent from the original cold-start-only substrate.

This document defines the post-biological lane in three deliberately separated capabilities:

1. **individual model building** — one Symbiont compresses and generalizes from its own life; **implemented and validated in Private SLM v1**;
2. **social knowledge transfer** — bounded knowledge crosses organism boundaries with provenance; **next frontier, not yet implemented**;
3. **culture** — transmitted knowledge persists beyond the discoverer and can accumulate across generations; **future phase**.

The remainder of this document preserves the design rationale and invariants that bound Private SLM v1 and the future cultural phases.

---

# 1. Research question

**Can a Symbiont transform its own evidence-backed lifetime experience into a private learned model that improves prediction, compression or hypothesis generation beyond the existing cognitive graph, without receiving pretrained human knowledge, evaluator truth or authority to modify factual memory directly?**

The interesting result is not that a neural network can be trained. That is already known.

The interesting result is whether the organism can build a useful model from the information it has actually acquired during its own life.

---

# 2. Foundational rule

The SLM is not the organism's brain and is not an oracle.

It is a **cognitive organ/tool** owned by one organism.

```text
experience
   ↓
evidence ledger
   ↓
knowledge / hypotheses
   ↓
corpus curation
   ↓
private SLM candidate
   ↓
shadow evaluation
   ↓
validated model
   ↓
predictions / hypotheses
   ↓
normal organism evidence cycle
```

The model may propose.

Reality and organism-owned evidence decide.

---

# 3. Permanent epistemic invariants

The post-biological lane must preserve all previous invariants and add these:

1. Model output is never an observation.
2. Model output is never ground truth.
3. Generated content cannot enter factual memory without normal evidence validation.
4. Evaluator labels, metrics and synthetic ground truth never enter training data.
5. A model may not execute code, commands, network operations or host actions.
6. A model may not create permissions or broaden organism capabilities.
7. Training cannot use arbitrary host files, user content or hidden telemetry.
8. Model size, training time, memory, storage and inference rate remain externally bounded.
9. A model belongs to exactly one organism in the private-SLM phase.
10. Model-generated samples cannot silently train successor models as if they were observed experience.
11. Every training example retains provenance to admissible organism evidence.
12. Promotion is evidence-gated and reversible; deletion or retirement never deletes the underlying evidence.
13. Incremental adaptation must use an explicitly authorized parent artifact belonging to the same organism.
14. Parent continuity means actual inherited model state, not lineage metadata alone.
15. A successor remains `SHADOW` until independently promoted; the active parent remains authoritative until then.
16. Direct model/corpus/weight transfer between organisms is not part of Private SLM v1.

---

# 4. No pretrained language model in the scientific baseline

The baseline experiment must not start from a pretrained human LLM.

A pretrained model would import huge amounts of external semantics and make it impossible to distinguish organism-acquired abstraction from human prior knowledge.

The scientific baseline therefore uses a small randomly initialized sequence model trained exclusively from Symbiont-native representations.

Pretrained models may later exist as an explicitly separate engineering condition, but must never be reported as evidence of emergent individual cognition.

---

# 5. Not necessarily natural language

The first model does not need human language.

Its vocabulary should derive from opaque organism-native tokens and bounded event classes.

Example conceptual stream:

```text
<SENSE:17>
<STATE:pressure.2>
<ACTION:repair>
<OUTCOME:integrity.up>
<RELATION:42>
<HYPOTHESIS:supported>
<TIME:+1>
```

No token means "CPU", "hunger", "friend" or any other human interpretation unless the organism itself has legitimately created an internal abstraction.

Human-readable translation belongs to Observatory, not cognition.

---

# 6. Experience Ledger

Introduce an immutable training-facing evidence projection, conceptually:

```text
ExperienceLedger
```

It is not raw telemetry storage.

Each entry is a bounded abstract episode derived from state the organism is already allowed to retain.

Suggested record:

```python
@dataclass(frozen=True, slots=True)
class ExperienceRecord:
    record_id: str
    organism_id: str
    tick_class: int
    context_tokens: tuple[str, ...]
    action_token: str | None
    outcome_tokens: tuple[str, ...]
    epistemic_status: str
    evidence_refs: tuple[str, ...]
    confidence_class: int
    source_kind: str
```

Constraints:

- no raw host path;
- no exact private host values unless already legitimate organism state;
- no evaluator-only fields;
- no arbitrary strings from external content;
- bounded token count;
- bounded retained records;
- immutable evidence references;
- deterministic canonical serialization.

---

# 7. Epistemic source classes

Before culture, the corpus supports only organism-local classes:

```text
OBSERVED
ASSOCIATED
HYPOTHESIZED
PREDICTED
SUPPORTED
CONTRADICTED
RETIRED
```

Future culture may add:

```text
SOCIAL_OBSERVED
SOCIAL_CLAIM
CULTURAL_INHERITANCE
```

but these are explicitly out of scope for the private-SLM milestone.

A `PREDICTED` or `HYPOTHESIZED` item must never be serialized as if it were `OBSERVED`.

---

# 8. Corpus Builder

Introduce a bounded curator:

```text
ExperienceLedger
      ↓
CorpusBuilder
      ↓
TrainingCorpus
```

The builder is deterministic for a given evidence snapshot and configuration.

Responsibilities:

- filter admissible epistemic states;
- preserve provenance;
- deduplicate near-identical episodes;
- cap repeated frequent patterns;
- retain negative/contradictory examples;
- separate train/validation/test by time or episode groups;
- prevent target leakage;
- hash the resulting dataset manifest.

It must not optimize using evaluator test results.

---

# 9. Corpus units

The initial unit should be an **episode window**, not an isolated token.

Conceptually:

```text
context(t-k ... t)
      +
action(t)
      →
outcome(t+1 ... t+h)
```

Possible initial objectives:

1. next-event prediction;
2. next-state-class prediction;
3. masked-event reconstruction;
4. action-conditioned outcome prediction.

The first scientific target should remain prediction because it has clean baselines and already connects naturally to Milestone J.

---

# 10. Vocabulary

Use a closed tokenizer over structured native tokens rather than free text.

Initial families:

```text
SPECIAL
SENSE
INTERNAL_SENSE
CONCEPT
STATE_CLASS
ACTION
OUTCOME
RELATION
EPISTEMIC_STATE
TEMPORAL_OFFSET
SEPARATOR
```

IDs are opaque and organism-local where appropriate.

---

# 11. Closed Private SLM v1 evidence boundary

Private SLM v1 is considered closed only for the following demonstrated capabilities:

- prediction from organism-private opaque experience can beat trivial held-out baselines;
- model-family promotion is selective rather than automatic;
- arbitrary opaque-symbol renaming disrupts a stale model but the predictive structure is recoverable by retraining;
- individual specificity exists in the preregistered mean criterion, though the effect is weak and heterogeneous;
- real parent-state continuity is required for incremental adaptation;
- a bounded adapted successor can outperform the stale parent under the preregistered symmetric drift protocol while preserving valid lineage and budgets;
- negative D-v1 and D-v2 results remain negative and delimit what cold-start retraining does not establish.

Private SLM v1 does **not** claim:

- universal adaptation to every regime shift;
- tokenizer migration;
- cultural transmission;
- cross-organism model reuse;
- inherited learned weights;
- natural-language competence;
- pretrained-model emergence;
- general intelligence.

---

# 12. Next frontier: social knowledge transfer before cumulative culture

The next phase should not begin by exchanging model weights or corpora. It should begin with bounded, typed, provenance-carrying claims derived from organism-owned evidence.

Conceptually:

```text
private evidence
      ↓
validated individual claim
      ↓
bounded social transmission
      ↓
receiver stores claim as received evidence
      ↓
receiver independently validates / contradicts / forgets
      ↓
claim genealogy persists across transmissions
```

The minimum cultural substrate must distinguish:

- personally observed evidence;
- personally inferred knowledge;
- received social claims;
- independent confirmations;
- repeated copies descending from the same source;
- contradictions;
- freshness/age;
- mutation of a transmitted claim;
- retirement/forgetting.

A hundred descendants of one original claim count as **one evidential lineage**, not one hundred independent observations.

The first cultural phase should therefore build claim provenance and genealogy before shared language, shared model weights or shared corpora.

---

# Cumulative Culture v1

## Scope

Cumulative Culture v1 adds bounded cultural composition over the `SocialClaim` DAG from Cultural Foundation v1. A `CulturalComposite` is an immutable, content-addressed, and serializable version of a cultural construction; it is not an observation, it does not create a root, and it cannot automatically become private experience or a Private SLM target.

The implemented surface lives in `symbiont.modeling.culture`. The transport remains `SocialChannel`, in memory and explicitly authorized by the laboratory. There are no sockets, peers, global storage, weights, adapters, corpus, or raw telemetry.

## Contract and invariants

A composite preserves:

- `component_claim_ids`, bounded to 32;
- `parent_composite_ids`, as a DAG bounded to 8;
- `contributing_organism_ids`, bounded and derived from `source_organism_id`;
- `root_evidence_ids`, the union of the roots of its claims and parents;
- `generation`, calculated as the successor of its parents;
- bounded operation (`combine`, `extend`, `refine`, `replace`, `contradict`, `retire`);
- creation tick and retirement state.

Identity is derived from the canonical payload. Duplicates, collisions, missing parents, cycles, unknown components, invalid generations, and capacity excesses fail closed. Composing never adds a new evidence: the composite is a cultural artifact, not an epistemological root.

`replace` preserves the erroneous composite as an ancestor and creates a new version that explicitly excludes the substituted component. `retire` creates a retired terminal version; the genealogy remains available and the current construct may be empty. Clonal offspring materialize an empty social ledger: cultural acquisition occurs only via transmitted claims/composites.

## Transmission and costs

A composite can be transported across an authorized peer. The receiver acquires only the referenced bounded claims and their causal ancestors, and validates that the composite matches byte for byte with the emitting ledger. It cannot read the complete private state of the emitter. The ledger charges for reception, storage, and composition; the channel charges for deliveries and maintains its ceilings.

The Observatory passively exposes counts, contributors, generations, roots, and lineage. It never edits, confirms, deletes, composes, or retransmits culture.

## Scientific design

`learning.cumulative-culture` was preregistered before executing with seeds `101, 127, 149` and 128 ticks. The protocol compares:

1. no transmission;
2. atomic claims transmitted without composition;
3. bounded composition;
4. evaluator-side ablations without breaking internal invariants.

The cumulative condition uses three distinct experience surfaces: a claim X, a claim Y, and a claim Z. No founder ledger receives the final product before the exchange. The observed sequence is `X -> X+Y -> X+Y+Z`; afterwards the founders disappear, a ledger born later receives the composite and adds W. Utility is measured as the operational capacity of the three-component construct against the atomic transmission control without composition. The laboratory does not deliver labels of roles, truth, or success to the organism.

## Limits of interpretation

The study closes the composition mechanism and its causal properties in the authorized scope. The selection of which claims to compose and when to transmit is controlled by the study harness; it is not presented as emergent autonomous cooperation. Language, symbols, prestige, conformity, cultural selection, and SLM training with social claims are not implemented.

Persistence, complexity, utility, and epistemological support remain distinct variables. A more complex or more persistent version may contain error; the protocol includes contradiction, replacement, retirement, and replay to make that possibility visible.
