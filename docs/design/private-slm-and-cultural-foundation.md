# Private SLM & Cultural Foundation

## Status

Proposed design. Biological Closure v1 is treated as the prerequisite boundary.

This document defines the first post-biological development lane for Symbiont: an organism-owned, private, bounded small language/model substrate trained only from the organism's own admissible experience before any cultural transmission is enabled.

The design deliberately separates three future capabilities that must not be collapsed:

1. **individual model building** — one Symbiont compresses and generalizes from its own life;
2. **social knowledge transfer** — bounded knowledge crosses organism boundaries with provenance;
3. **culture** — transmitted knowledge persists beyond the discoverer and can accumulate across generations.

The first implementation covers only (1).

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

The tokenizer itself is versioned and hashed.

Unknown future tokens map to bounded unknown classes rather than silently changing vocabulary semantics inside an existing model.

---

# 11. Initial model family

The default baseline should be deliberately small.

Recommended first family:

- decoder-only or causal transformer;
- randomly initialized;
- fixed architecture supplied by the immutable training substrate;
- approximately 0.5M–5M parameters for first experiments;
- short context window, initially 64–256 native tokens;
- no external embeddings;
- no natural-language tokenizer;
- deterministic seeded initialization in laboratory experiments.

The exact architecture is an implementation choice, not a biological claim.

A recurrent baseline should also be available so that "transformer" is not silently treated as the null hypothesis.

---

# 12. Model Factory boundary

Training must not happen as arbitrary code generation inside `OrganismRuntime`.

Introduce a governed external capability boundary conceptually:

```text
OrganismRuntime
      │ request
      ▼
ModelTrainingAuthority
      │ validates budget / corpus / architecture
      ▼
SandboxedTrainer
      │
      ▼
ModelArtifact
```

The organism may eventually request training.

The organism never supplies executable source code.

The authority owns:

- supported architectures;
- parameter ceilings;
- CPU/memory/time budget;
- allowed objective classes;
- artifact format;
- storage quota;
- cancellation;
- deterministic seed policy where required.

## 12.1 Bounded parent adaptation

`parent_model_id` is not sufficient evidence of continuity. Cold-start training
and parent adaptation are separate operations. `adapt_private_model` first loads
the content-addressed parent artifact and fails closed unless organism ownership,
architecture, objective, tokenizer hash, context window, parameter shape and
artifact integrity all match.

The trainer initializes the candidate from the parent's actual serialized weights
and applies only the newly curated, evidence-backed corpus. Model output remains
`PREDICTED` and cannot silently become a target. The successor manifest records
parent and ancestor IDs, generation, corpus/tokenizer hashes, seed, adaptation
reason, authorized ceilings and observed adaptation cost.

The runtime keeps the active parent until independently authorized promotion. The
successor is adopted as `SHADOW`, and a failed or rejected successor cannot replace
the parent. Checkpoints retain registry lineage but never embed arbitrary weights;
clonal offspring retain modeling capacity without acquiring private artifacts or
corpus. Observatory exposure is passive and limited to model IDs, lineage,
generation, state, evaluation summary and adaptation count.

The first follow-up is preregistered as `learning.private-model-adaptation`. It
compares stale, fresh and parent-initialized adapted models under the symmetric
D-v2 regime without changing D-v1/D-v2.

---

# 13. Training as metabolism

Training is not free.

A training request consumes explicit resources from the organism/habitat accounting model.

Cost dimensions should include at least:

```text
compute
memory
persistence/storage
cognition opportunity cost
```

A model that is never useful but consumes continuous training resources should become physiologically expensive.

This creates a future endogenous pressure toward smaller or more specialized models without hard-coding "smaller is better".

---

# 14. Candidate / active / retired lifecycle

Model artifacts have a lifecycle separate from organism factual knowledge:

```text
CANDIDATE
   ↓
SHADOW
   ↓
ACTIVE
   ↓
DEGRADED / RETIRED
```

A candidate cannot affect normal cognition.

A shadow model may be queried by evaluator-owned or shadow-runtime paths, but its answer is not used for action selection.

An active model may later supply bounded predictions/hypotheses.

Retirement preserves lineage metadata and evaluation summary but does not require preserving obsolete full weights indefinitely.

---

# 15. Promotion gate

No model is promoted because training loss decreased.

Promotion requires independent evidence against declared baselines.

Minimum comparisons:

```text
zero / uniform
frequency prior
persistence
existing CognitiveGraph predictor
simple recurrent model
```

Metrics may include:

- held-out log loss;
- calibration;
- next-state accuracy where meaningful;
- action-conditioned prediction gain;
- robustness under token remapping;
- performance after regime shift;
- compute cost per useful prediction.

The evaluator owns aggregate comparison metrics.

The organism may receive only the normal consequences of predictions it legitimately uses after activation.

---

# 16. Anti-self-confirmation rule

The strongest new invariant is:

> **Model output may create a hypothesis, never its own confirming evidence.**

Forbidden loop:

```text
SLM says X
   ↓
X stored as fact
   ↓
X enters corpus
   ↓
new SLM sees more X
   ↓
confidence rises
```

Allowed loop:

```text
SLM proposes X
   ↓
HYPOTHESIZED
   ↓
organism encounters independent evidence
   ↓
SUPPORTED / CONTRADICTED
   ↓
future corpus may include both proposal provenance and independent result
```

---

# 17. Model Registry

Each organism receives a bounded local registry.

Suggested metadata:

```python
@dataclass(frozen=True, slots=True)
class ModelRecord:
    model_id: str
    organism_id: str
    parent_model_id: str | None
    corpus_hash: str
    tokenizer_hash: str
    architecture_id: str
    parameter_count: int
    training_budget_class: int
    objective: str
    state: str
    created_tick_class: int
    evaluation_summary: tuple[int, ...]
```

Weights belong to the artifact store; model records belong to organism durable state only if they are still part of its active cognitive phenotype.

---

# 18. Checkpoint semantics

A checkpoint must not pretend to freeze an in-progress accelerator/training microstate.

Allowed durable state:

- corpus manifest hash;
- model artifact reference/hash;
- tokenizer version;
- active/retired status;
- bounded evaluation classes;
- training request state if safely restartable.

In-progress trainer internals may be cancelled on restart unless a future explicit resumable-training contract is designed.

A dead organism's private model is historical material, not automatically an active model for a new identity.

---

# 19. No inheritance in phase 1

Private models are acquired lifetime phenotype.

Therefore clonal and paired descendants do **not** receive:

- parent model weights;
- parent corpus;
- parent model predictions;
- parent tokenizer extensions;
- parent factual memories.

This preserves the existing separation:

```text
genetic inheritance != lifetime cognition
```

Any future post-birth model/knowledge transfer belongs to the cultural milestone.

---

# 20. Runtime integration

Initial integration should be deliberately weak.

Phase 1 runtime path:

```text
normal cognition
     │
     ├──► private model shadow query
     │          ↓
     │     evaluator comparison
     │
     └──► unchanged action path
```

Only after utility is demonstrated:

```text
private SLM
   ↓
PredictionProposal / HypothesisProposal
   ↓
existing epistemic boundary
   ↓
normal evidence / prediction machinery
```

The SLM never returns arbitrary executable actions.

---

# 21. Output schema

Avoid free-form natural language in the first active integration.

Use closed typed output such as:

```python
@dataclass(frozen=True, slots=True)
class ModelPredictionProposal:
    target_token: str
    horizon_class: int
    predicted_class: int
    confidence_class: int
    model_id: str
```

and:

```python
@dataclass(frozen=True, slots=True)
class ModelHypothesisProposal:
    subject_token: str
    relation_token: str
    object_token: str
    confidence_class: int
    model_id: str
```

Both become organism hypotheses, not facts.

---

# 22. First experiments

## Experiment A — Can it learn anything?

Same organism experience snapshot.

Compare:

```text
frequency baseline
persistence baseline
small recurrent baseline
tiny transformer
```

Gate: at least one learned model beats trivial baselines on a predeclared held-out task without target leakage.

## Experiment B — Is the gain organism-specific?

Train models from different individuals with identical birth genomes but divergent life histories.

Cross-evaluate:

```text
model A on A
model A on B
model B on B
model B on A
```

Hypothesis: private models should reflect individual experience, not merely reproduce apparatus regularities.

## Experiment C — Opaque remapping

Permute sense/action token identities while preserving underlying structure.

A useful architecture should recover performance from relational/temporal structure rather than fixed human-facing IDs.

## Experiment D — Regime shift

Train before a known evaluator-side regime change, then observe degradation and recovery after new evidence/training.

Gate: stale models must be detectable and revisable.

## Experiment E — Utility ablation

Compare otherwise matched organisms:

```text
SLM active
SLM shadow-only
no SLM
```

Only this experiment can justify integrating the model into cognition.

---

# 23. Utility criteria

The private-SLM milestone closes only if the model yields at least one reproducible gain in a predeclared domain such as:

- lower held-out predictive loss;
- better calibrated predictions;
- faster adaptation after regime change;
- better hypothesis precision at equal proposal budget;
- comparable predictive utility with lower retained explicit state;
- improved sample efficiency.

A larger model with lower training loss but no downstream held-out utility does not satisfy the gate.

---

# 24. Observatory

Observatory remains passive and should expose model state separately from organism facts.

Suggested panel:

```text
PRIVATE MODEL
state: SHADOW
architecture: tiny-transformer-v1
parameters: class 3
corpus: 1,842 admissible episodes
provenance coverage: 100%
held-out gain: positive
last validation: recent
```

It may also show model lineage:

```text
m0 → m1 → m2
      ↘ retired
```

Never display model-generated hypotheses as confirmed organism knowledge unless the normal knowledge system has independently promoted them.

---

# 25. symbiont_lab responsibilities

`symbiont_lab` owns:

- benchmark construction;
- evaluator-only train/validation/test metrics;
- model-family comparisons;
- ablations;
- cross-individual evaluation;
- token-remapping controls;
- regime-shift protocols;
- artifact reproducibility manifests;
- null/negative-result reporting.

`symbiont` owns only organism-facing evidence, requests, artifacts it legitimately acquired and bounded proposal consumption.

---

# 26. Proposed module boundaries

Conceptual layout:

```text
src/symbiont/modeling/
├── experience.py
├── corpus.py
├── tokenizer.py
├── registry.py
├── proposals.py
└── authority.py

symbiont_lab/modeling/
├── trainer.py
├── architectures.py
├── evaluation.py
├── baselines.py
└── studies.py
```

Exact package placement must respect the existing organism/laboratory import boundary.

The organism must never import evaluator modules.

---

# 27. Implementation sequence

## L0 — Boundary and corpus contract

- `ExperienceRecord` closed schema;
- provenance references;
- corpus manifest;
- train/validation/test split rules;
- no model training yet.

## L1 — Native tokenizer

- deterministic structured vocabulary;
- organism-local opaque IDs;
- versioned encoding;
- round-trip and unknown-token tests.

## L2 — Laboratory model factory

- tiny recurrent baseline;
- tiny transformer baseline;
- deterministic seeds;
- bounded artifact format;
- CPU/memory/time caps.

## L3 — Shadow private model

- model registry;
- candidate/shadow lifecycle;
- no runtime behavioral influence;
- Observatory passive projection.

## L4 — Scientific utility gate

- held-out baselines;
- individual-specificity test;
- opaque-remapping test;
- regime-shift test;
- no-SLM ablation.

## L5 — Bounded active proposals

Only after L4 passes:

- typed prediction proposals;
- typed hypothesis proposals;
- normal epistemic validation;
- metabolic inference cost;
- retirement on degradation.

## L6 — Private SLM closure

Close when individual models provide reproducible utility while all epistemic and safety boundaries remain intact.

Culture is still disabled.

---

# 28. Cultural frontier — explicitly deferred

After Private SLM closure, a separate design must decide how knowledge crosses organism boundaries.

That future design must preserve at least:

```text
origin organism
original evidence lineage
number of transmissions
independent confirmations
contradictions
last direct evidence
model-derived vs directly observed provenance
```

It must support the possibility of useful tradition **and** false tradition without losing epistemic genealogy.

No cultural artifact may silently become genetic inheritance.

---

# 29. Future culture sequence

The intended later sequence is:

```text
private experience
      ↓
private model
      ↓
private discovered abstraction
      ↓
bounded social transmission
      ↓
recipient hypothesis
      ↓
validation / rejection
      ↓
tradition
      ↓
multigenerational culture
```

Only after this exists should model adapters, distilled models or learned symbol systems be considered transmissible cultural artifacts.

---

# 30. Exit condition for this design lane

The first post-biological milestone is successful when:

> A Symbiont can construct a bounded private model from its own admissible life history, the model demonstrates reproducible out-of-sample utility beyond simpler baselines, its outputs remain hypotheses/predictions rather than facts, the model cannot bypass organism/kernel authority, and no knowledge from another organism or human pretrained corpus is required.

At that point Symbiont has moved from:

```text
I learn relationships during my life.
```

to:

```text
I can build a model of patterns in my own life and use it to propose what may happen next.
```

That is the required foundation for culture.
