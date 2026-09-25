---
id: design.general.endogenous-metaplastic-epigenetics-v1
title: "Endogenous Metaplastic Epigenetics V1"
document_type: design
domain: genome
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Design / preregistration — endogenous metaplastic regulation and acquired epigenetics v1

Status: **proposed and preregistered before implementation**

## 1. Problem

The canonical embodied runtime now expresses supported inherited loci into real phenotype:

    genome + inherited epigenome
            ↓
    learning_rate / exploration_rate
            ↓
    operative cognitive dynamics

However, no legitimate endogenous process changes those expressions during life, so `GermlineState.capture_acquired_variation()` has no canonical source.

The missing path is:

    experience
      ↓
    internal regulation
      ↓
    persistent expression shift
      ↓
    germline capture

## 2. Hard boundary

The regulator MUST NOT receive or derive from World resource IDs, hazard IDs, semantic labels, survival score, offspring count, fitness, reward, evaluator success, Body part names, BodySchema ground truth or Lab condition labels.

Allowed inputs are internal state already available to Symbiont: prediction error, prediction-error trend, internally inferred disruption, agency confidence and elapsed cognitive ticks.

This is metaplastic regulation, not externally supervised adaptation.

## 3. Birth expression

We must distinguish three layers:

    genetic base + inherited epigenetic marks
                    ↓
              BIRTH EXPRESSION
                    ↓
          lifetime regulatory state
                    ↓
             CURRENT EXPRESSION

A child must not treat an inherited epigenetic mark as a newly acquired lifetime change. `GermlineState.birth_expression` must represent effective expression after inherited marks have been applied at birth, not raw genome values.

## 4. Supported regulable phenotype in v1

Only loci with real operative consumers may be regulated: `learning_rate` and `exploration_rate`.

Do not invent phenotype consumers for `initial_concepts`, `soft_node_budget`, `soft_edge_budget` or `forgetting_rate` until those mechanisms exist in the canonical minimal Symbiont.

Inheritance-policy loci (`acquired_transmission_rate`, `epigenetic_decay`, `max_epigenetic_marks`) are not lifetime cognitive phenotype.

## 5. Regulatory state

Add an internal `PhenotypicRegulationState` holding birth expression, current expression, prediction-error EMA and per-locus persistence counters. It belongs to Symbiont and contains no World truth.

## 6. Generic regulatory rule

Let `e_t` be current mean prediction error and `m_t` a slow EMA. Compute bounded surprise as `clip((e_t - m_t) / (m_t + epsilon), -1, +1)`.

`learning_rate` receives a small surprise-proportional adjustment plus slow relaxation toward birth expression. `exploration_rate` is regulated only from prediction surprise and internally inferred disruption, also with slow relaxation.

No World meaning or utility is consulted.

## 7. Bounds

Every update is clamped by the existing `LocusSpec`. No regulator can expand its constitutional limits.

## 8. Persistence gate before germline capture

A transient expression fluctuation is not heritable. For each regulable locus, `abs(current - birth) >= min_delta` must hold continuously for at least `PERSISTENCE_TICKS = 64` before `capture_acquired_variation()` may observe that locus. Falling below threshold resets the counter.

## 9. Capture direction

The regulator never writes an `EpigeneticMark` directly. Canonical path: `PhenotypicRegulator -> current_expression -> persistence gate -> GermlineState.capture_acquired_variation()`.

## 10. Immediate phenotype vs germline

Acquiring a germline mark must not recursively add the same delta again to the living individual's current expression. The mark records persistent acquired regulatory state for possible transmission; it is not an additional lifetime control signal.

## 11. Falsification experiments

### M1 — semantic invariance
Same numeric internal prediction trajectory under differently named World/evaluator conditions must produce identical regulatory trajectory and marks. Acceptance: exact equality.

### M2 — transient shock
Short high-error perturbation shorter than persistence threshold: temporary expression change, NO acquired epigenetic mark.

### M3 — sustained volatility
Persistent unpredictable prediction-error regime: bounded persistent regulation and eventual mark on a legitimate regulable locus. This is a mechanism test, not a claim that increased plasticity is adaptive.

### M4 — relaxation
After sustained volatility ends, expression moves toward birth expression. If the shift falls below capture threshold before persistence duration, no mark.

### M5 — inherited mark is not re-acquired at birth
Child receives a legitimate inherited mark. `birth_expression` equals inherited effective expression; stable neutral lifetime must not generate a new acquired mark merely because inherited expression differs from raw genome.

### M6 — no evaluator-fitness dependency
Static/AST gate: regulator code may not import `symbiont_lab`, `symbiont_world`, reward, fitness or survival evaluation APIs.

## 12. Interpretation limit

Even if M1-M6 pass, this demonstrates only endogenous bounded metaplastic regulation leaving a transmissible epigenetic trace without semantic World supervision. It does not demonstrate adaptive value, natural selection, Lamarckian evolutionary benefit, consciousness or intentional self-modification.

## 13. Implementation order

1. canonical birth-expression helper;
2. internal regulator state;
3. learning/exploration expression updates;
4. persistence gate;
5. germline capture;
6. M1-M6 tests;
7. only then E7 multigenerational interpretation.
