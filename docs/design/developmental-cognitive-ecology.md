# Developmental Cognitive Ecology

Status: implemented foundation, experimental.

## Purpose

Symbiont must receive constitutional limits and adaptive capabilities, not a
pre-assigned cognitive architecture. Persistent cognitive structure therefore
grows through independent producers that accumulate local evidence, expose at
most one proposal to the global substrate, receive bounded access to scarce
structural capacity, and remain reversible after consolidation.

## Core invariants

1. **Multiplicity is not authority.** A producer with 1,000 internal hypotheses
   has at most one outstanding structural proposal.
2. **Global arbitration is semantically opaque.** Scheduling uses producer
   identity, not meanings such as predictor, motor, concept, language or self.
3. **Bounded producer access.** Active producers rotate through a deterministic
   organism-specific ring. No contention debt is accumulated.
4. **Local evidence stays local.** A producer chooses its nominee using evidence
   comparable inside its own mechanism. The global arbiter does not compare
   prediction gain with motor controllability or concept support.
5. **Structural proposals are atomic.** A minimal functional structure may
   contain multiple node/edge mutations and commits or fails as one transaction.
6. **Birth is provisional.** Internal representations need developmental time
   and empirical evidence before they may support deeper recursive structure.
7. **Growth remains reversible.** Existing retirement and structural maintenance
   remain authoritative after admission.
8. **Lab and Observatory remain passive.** They measure the ecology but never
   choose proposals or scheduling outcomes.

## Current implementation

### Producer backpressure

`CognitiveBridge._register_structural_candidate` derives or accepts an opaque
`producer_id`. Registration rejects a second outstanding proposal from the
same producer. This converts the global registry from candidate-centric voting
to producer-centric access.

### Producer round-robin

The arbiter first selects the oldest outstanding proposal age, preventing
newly arriving producers from leapfrogging older pending work indefinitely.
Among equally old producers it uses an organism-specific stable hash ring and
advances from the last committed producer. The cursor remains valid when a
producer becomes temporarily inactive, so intermittent membership does not
reset fairness.

`contention_losses` is retained only as a legacy checkpoint field and no
longer influences scheduling.

### Atomic proposals

Structural admission no longer requires exactly one new node. A proposal may
consume several node/edge slots as long as it fits the same constitutional
mutation and resource bounds.

The first germinal concept and `readout_core` can therefore be proposed as one
minimal functional transaction rather than being born as two independently
starvable fragments.

### Predictive producer

Automatic predictor promotion no longer loops over every promotable shadow
hypothesis. Predictive learning performs local ranking and nominates one
proposal while its previous proposal is unresolved.

Ranking is local to predictive learning and currently uses:

- predictive gain;
- evidence sample count;
- deterministic organism-local tie-breaking.

It is not a global cognitive utility function.

### Developmental depth gate

A SENSE may be targeted immediately because it is an established external input.
A PREDICTOR may become the target of a new predictor only after:

- surviving at least the structural tentative lifetime;
- accumulating the minimum predictive evidence;
- showing positive aggregate predictive gain;
- showing positive recent gain.

This does not prohibit higher-order prediction. It prevents instantaneous
predictor-on-predictor cascades before the lower representation has demonstrated
stability and utility.

Structural birth ticks are checkpointed as provenance.

## Explicit non-goals of this slice

This foundation does **not** yet introduce:

- a universal utility score;
- semantic quotas;
- a learned global router;
- ESN/CTW/GRU specialization by role;
- RSSM;
- intrinsic-motivation curriculum;
- generic maturity states for every representation;
- new organism rewards.

Those belong to later experimental phases only after producer fairness and
developmental depth survive embodied runs.

## Adversarial acceptance tests

The implementation is expected to preserve these properties:

- 1,000 hypotheses from one producer create one global nominee;
- a second active producer retains bounded structural access;
- producer disappearance does not reset the scheduling cursor;
- newly arriving producers cannot starve an older pending proposal;
- multi-node proposals are rejected when they exceed available capacity;
- concept/readout bootstrap can be one atomic proposal;
- newborn predictors cannot immediately become recursive prediction targets;
- maturation provenance survives checkpoint/restore.

## Next experimental gate

Run the same Physics3D regime that previously produced predictor saturation.

The change is supported only if the run demonstrates all of the following:

1. predictor shadow multiplicity no longer fills the structural registry;
2. primitive/concept producers obtain bounded opportunities;
3. `concept` and `readout` structure can bootstrap without reserved semantic
   capacity;
4. recursive predictor depth grows only after empirical maturation;
5. prediction remains useful rather than merely being structurally throttled;
6. retirement continues to release obsolete capacity.

Only after those gates pass should the temporal-mechanism ecology
(ESN/CTW/ACTW/GRU/SLM challengers) be introduced.


## Implementation status — 2026-09-21

Implemented on `main`:

- producer-centric structural arbitration;
- one outstanding global proposal per producer;
- organism-specific deterministic producer round-robin;
- producer-local proposal validation separated from global scheduling;
- atomic multi-node structural proposals;
- atomic concept + core-readout bootstrap;
- generic representation lifecycle:
  `nascent -> provisional -> mature/stable -> weakening/retiring`;
- checkpointed age, observation and activation evidence;
- mature-substrate gate for higher-order structural growth;
- predictor-specific positive-gain requirement before recursive prediction;
- generic orphan retirement for concept/state/gate/readout;
- predictor-specific reversible retirement;
- insufficiency evidence consumption once a relation is explained;
- passive fairness and maturity telemetry in Observatory and Physics3D;
- neutral temporal mechanism contract;
- stationary and decayed VOMM challengers;
- sparse ESN + online NLMS challenger;
- local temporal responsibility tracker;
- preregistered producer-fairness, discrete temporal, continuous temporal and
  embodied cognitive-ecology studies.

### Explicitly still gated by evidence

The following remain deliberately **not integrated into organism cognition**:

- assigning ESN, VOMM, GRU or Transformer a semantic cognitive role;
- a learned global router;
- RSSM;
- intrinsic-motivation / learning-progress curricula;
- exact CTW/ACTW implementation;
- automatic promotion of any temporal challenger merely because it performs
  well in a lab benchmark.

Before any of those can enter the resident architecture, the embodied
`learning.cognitive-ecology-embodiment` study must show that producer fairness,
maturation, retirement and non-monopolization survive Physics3D.

The temporal challengers must additionally pass their causal controls rather
than merely exploiting autocorrelation.


## Phase gate after causal-validation implementation

The architecture now contains the complete pre-exploration path:

1. producer-level bounded structural access;
2. atomic structural proposals;
3. generic developmental maturation;
4. insufficiency-driven growth with stale-evidence consumption;
5. reversible weakening/retirement;
6. neutral discrete and continuous temporal challengers;
7. local explanatory responsibility;
8. causal controls:
   - predictive plasticity/lesion;
   - action/outcome shuffles for discrete temporal models;
   - action shuffle/no-action controls for continuous ESN;
   - matched Physics3D twins with cognitive motor outputs retained, removed,
     or within-family shuffled.

A second motor-output graph delay is deliberately not synthesized: resident
learned motor/primitive association edges already use the canonical maximum
`delay_ticks=1`. Temporal-delay causality remains covered by the dedicated
temporal studies rather than by a noncanonical Physics3D lesion.

The matched-twin study is preregistered as
`learning.embodied-behavioral-ablation`. A seed that never develops cognitive
motor output is reported as **not causally testable**, not as a successful
ablation.

### Phase H remains blocked

Learning-progress / intrinsic-motivation scheduling MUST NOT be connected to
resident exploration yet.

Unblocking requires empirical evidence from fresh preregistered runs that:

- `learning.structural-producer-fairness` preserves the hard waiting bound;
- `learning.cognitive-ecology-embodiment` removes the historical predictor
  monopoly without suppressing all useful predictive structure;
- temporal challengers pass their causal controls, not merely autocorrelation
  benchmarks;
- at least one seed develops a naturally occurring cognitive motor output that
  makes `learning.embodied-behavioral-ablation` causally testable.

Until those conditions hold, adding intrinsic motivation would confound the
question the current architecture is designed to answer.
