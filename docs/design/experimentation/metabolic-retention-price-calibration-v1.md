---
id: design.experimentation.metabolic-retention-price-calibration-v1
title: "Metabolic Retention Price Calibration v1 — Preregistration"
document_type: design
domain: experimentation
status: proposed
---

# Metabolic Retention Price Calibration v1 — Preregistration

**Status:** proposed, awaiting owner approval. Regime: an exploratory selection
on its own seeds, then a **confirmatory** comparison against the current prices
on fresh seeds. Nothing has been run.

**Origin.** Canonical organism profile register §7 (owner decision 2026-10-02):
the retention prices are not backed by any result, and at full sensory capacity
retention alone would cost about five times the organism's basal spend. The
inconsistency is held as a strict expected failure
(`tests/experimental_integrity/test_metabolic_cost_coherence.py`) until this
study decides.

## 1. Current prices

Every tick the organism pays maintenance for the structure it retains
(`MemoryDomain.retained_units`, `src/symbiont/core/domains/memory.py`):

| Retained unit | Price per tick |
| --- | --- |
| Drift baseline (one per tracked percept) | 0.001 |
| Cognitive graph node | 0.0005 |

The same price is paid while the organism is dormant. The other charges
(observation, attention, assimilation, sensory mutations, constitutive
maintenance, repair, growth) are not under test. Measured basal spend of a small
canonical organism is about 0.055 per tick; a body holds 4 units of energy by
default.

## 2. Question

Which retention prices, and which dormancy discount, let the canonical organism
keep what it learns without starving under bounded energy support, and do they
beat the current prices on fresh seeds?

## 3. Intervention

Three parameters become experimental parameters (all other charges unchanged):

| Parameter | Current | Levels |
| --- | --- | --- |
| Price per drift baseline `p_b` | 0.001 | 0.001, 0.0005, 0.00025, 0.000125 |
| Price per cognitive node `p_n` | 0.0005 | 0.0005, 0.00025, 0.000125 |
| Dormancy retention factor `d` (share of retention paid while dormant) | 1.0 | 1.0, 0.5, 0.25 |

36 arms. The current prices `(0.001, 0.0005, 1.0)` are one of them and are the
control.

## 4. Fixed conditions

- Organism: the canonical organism profile current when the study runs (`v1`,
  or `v2` if Competence Establishment Evidence v1 has been adopted by then),
  newborn, private-model runtime, base genome; the profile version is recorded
  in every result.
- Body: `CausalBody`, four actuators, identity mapping, the run's seed, with the
  body's default finite energy reserve (not the unlimited reserve the agency
  studies use).
- **Energy support.** A fixed, action-independent input per tick through the
  body's ordinary intake path, as in the protected Physics3D nursery. Its rate is
  fixed by rule before any arm runs: 75 % of the median basal drain per tick,
  over ticks 1–500, of a newborn under the current prices on the pilot seeds
  `3083, 3089, 3109`. The rule and the measured value are written to
  `support.json`.
- Horizon `H = 2000` ticks; no observer.

## 5. Measures

Per run:

- **Survival** (primary): the tick of death, or `H` if alive at the horizon.
- `T_stable`: as in Competence Establishment Evidence v1 (first tick from which a
  valid binding is held for 200 consecutive ticks; censored at `H`).
- Retained structure at the end: drift baselines plus cognitive nodes.
- Share of total spend paid as retention.

## 6. Coherence constraint

An arm is **eligible** only if retention at full sensory capacity (256 drift
baselines, no nodes, not dormant) costs at most half of the support rate. This is
the consistency the strict expected failure states, made a precondition instead
of an outcome.

## 7. Stage 1 — selection (exploratory)

- Seeds: `3001, 3011, 3019, 3023, 3037, 3041, 3049, 3061`.
- All 36 arms on every seed (288 runs).
- **Selection rule.**
  - Among eligible arms where the organism is alive at `H` on at least 6 of 8
    seeds, choose the smallest median `T_stable`.
  - Ties go to the higher `p_b`, then the higher `p_n`, then the higher `d`: the
    most metabolic pressure that still works.
  - If no arm qualifies, the result is **no change**, and the prices stay
    declared unsupported.
- Written to `selection.json` before any confirmation seed runs. Exploratory: it
  supports no claim by itself.

## 8. Stage 2 — confirmation (confirmatory)

- Seeds: `4001, 4003, 4007, 4013, 4019, 4021, 4027, 4049, 4051, 4057, 4073, 4079`.
- Two arms: the selected prices and the current prices, paired by seed (24 runs).
  If stage 1 selects the current prices, stage 2 is not run.
- **SUPPORTED** when all three hold:
  1. the selected prices survive at least as long as the current ones on at
     least 9 of 12 seeds;
  2. median survival is strictly longer, or equal at `H` with a median `T_stable`
     reduction of at least 10 %;
  3. median retained structure at the end is at most twice the current one (the
     prices still bound growth).
- **NOT SUPPORTED** otherwise. No level, seed, horizon or threshold changes after
  a run.

## 9. Configuration consequence (ADR-0062)

- **SUPPORTED:** adopt. The three parameters become profile options with the
  selected values in the next profile version. Earlier versions keep the current
  prices, so closed experiments stay reproducible. The strict expected failure is
  removed, because the coherence constraint then holds.
- **NOT SUPPORTED:** no change. The register records the result and the strict
  expected failure stays.

## 10. Apparatus to build after approval

- `p_b`, `p_n` and `d` as profile options read by `MemoryDomain.retained_units`
  and the physiology step. They default to the current values, and existing
  behaviour is checked identical against `main`.
- A study module: the support rule, `run_one(seed, p_b, p_n, d)`, both stages,
  and contract tests for the eligibility rule, censoring, selection and decision.
- The pilot, selection and confirmation as governed runs through
  `agentctl run start`.

## 11. Cost and order

Stage 1 is 288 runs of 2000 ticks, roughly three to three and a half hours as
one governed run, inside the 360-minute limit. The study runs after Competence
Establishment Evidence v1 concludes, because that study may change the canonical
organism.

## 12. Limits

The result holds for the synthetic causal Body with this support rule and
horizon. Physics3D has its own energy scale (basal drain about 0.8 per tick in
the nursery); transferring prices there would need its own check. Only retention
prices and the dormancy discount are calibrated; every other charge stays as it
is.
