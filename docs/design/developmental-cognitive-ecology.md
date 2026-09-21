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

The arbiter orders active producer identities with an organism-specific stable
hash and advances from the last committed producer. The cursor remains valid
when a producer becomes temporarily inactive, so intermittent membership does
not reset fairness.

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
