---
id: design.experimentation.competence-establishment-evidence-v1
title: "Competence Establishment Evidence v1 — Preregistration"
document_type: design
domain: experimentation
status: proposed
---

# Competence Establishment Evidence v1 — Preregistration

**Status:** proposed, awaiting owner approval. Regime: **two stages**, an
exploratory selection on its own seeds and a **confirmatory** comparison on
fresh seeds. Nothing has been run.

**Requirement served.** The owner requires that an organism re-embodied in a new
Body manages it sooner than a newborn (canonical organism profile register, §6).
That needs competences that are real and stay usable. The re-embodiment
functional transfer experiment (r7) could not run partly because they do not.

## 1. Finding that motivates the study

From the exploratory diagnostic on the transfer experiment's development seeds
(2026-10-03):

- A motor competence counts as **established** once its controller has
  `support ≥ 2` samples, `controllability > 0.002`, `reproducibility ≥ 2/3`
  and `directional_consistency ≥ 0.60` (`src/symbiont/actuation/competence.py`).
- With two samples a consistency of 0.60 is often reached by chance. As samples
  accumulate, such competences fall back below the gate: the controller stays in
  the pool but stops being established, and every execution binding that relied
  on it becomes `STALE / controller_unavailable`.
- On seed 109 all six stale bindings had controllers with 4–9 samples,
  controllability 0.02–0.05 and consistency about 0.5. Development organisms
  held a valid binding in only 2–57 % of their first 1000 ticks, under both the
  historical and the canonical profile.

The demotion itself is correct: later evidence refutes the competence. The
question is where the entry gate should sit. Too lenient, the organism acts on
competences that are not real and loses them; too strict, it waits too long to
act at all.

## 2. Question

Under the canonical organism in the synthetic causal Body, which establishment
gate gives an organism the earliest **stable** execution binding, and does it
beat the current gate on fresh seeds?

## 3. Intervention

Two gate parameters of `CompetenceEvidence.maturity` become experimental
parameters. Every other condition of the gate (`controllability > 0.002`,
`reproducibility ≥ 2/3`) and the ROBUST rule are unchanged.

| Parameter | Current | Levels |
| --- | --- | --- |
| Minimum support `S` | 2 | 2, 3, 4, 5, 6, 8, 10, 12, 16 |
| Minimum directional consistency `C` | 0.60 | 0.60, 0.70, 0.80 |

27 arms. The current gate `(2, 0.60)` is one of them and is the control.

## 4. Fixed conditions

- Organism: canonical organism profile `v1` (ADR-0062), newborn, private-model
  runtime, base genome, as built by the transfer study's `_newborn`.
- Body: `CausalBody`, four actuators, identity mapping, the run's seed.
- Horizon `H = 2000` ticks per run; no observer.
- Nothing evaluator-side (the mapping, the scores) reaches the organism.

## 5. Measures

Per run:

- **`T_stable` (primary).** The first tick `t` such that the organism holds at
  least one `VALID` execution binding at every tick of `[t, t + 200)`. If none
  exists by `H − 200`, `T_stable = H` (censored, the worst value).
- `T_first`: first tick with any `VALID` binding (secondary).
- Holding fraction: share of ticks from `T_first` to `H` with a `VALID` binding
  (secondary).
- False establishment rate: share of competences ever established that are not
  established at `H` (secondary).

`T_stable` is the balance measure: a lenient gate binds early but loses the
binding, a strict gate keeps it but binds late. Both delay `T_stable`.

## 6. Stage 1 — selection (exploratory)

- Seeds: `1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049` (eight; disjoint from
  every seed of the transfer experiment and from 127).
- All 27 arms on every seed (216 runs).
- **Selection rule.** The arm with the smallest median `T_stable`. Ties go to the
  smaller `S`, then the smaller `C` (the more lenient gate learns sooner).
- The selection result, every arm's medians and secondary measures are written
  to `selection.json` before any confirmation seed runs. It is exploratory: it
  supports no claim by itself.

## 7. Stage 2 — confirmation (confirmatory)

- Seeds: `2003, 2011, 2017, 2027, 2029, 2039, 2053, 2063, 2069, 2081, 2083, 2087`
  (twelve, disjoint from stage 1 and from the transfer experiment).
- Two arms: the selected gate and the current gate `(2, 0.60)`, paired by seed
  (24 runs). If stage 1 selects the current gate, stage 2 is not run and the
  result is **no change**.
- **SUPPORTED** when all three hold:
  1. the selected gate has a smaller `T_stable` on at least 9 of 12 seeds;
  2. the median paired reduction `(T_current − T_selected) / T_current` is at
     least 0.20;
  3. the median holding fraction under the selected gate is not lower than under
     the current gate.
- **NOT SUPPORTED** otherwise. Negative and null results are recorded as they
  are; no level, seed, horizon or threshold changes after a run.

## 8. Configuration consequence (ADR-0062)

- **SUPPORTED:** adopt. The two parameters become options of the canonical
  organism profile with the selected values in a new version `v2`; `v0` and `v1`
  keep `(2, 0.60)`, so closed experiments stay reproducible. Then the
  re-embodiment transfer experiment repeats its development stage on `v2`
  without any protocol change.
- **NOT SUPPORTED:** no change; recorded in the register with the reason.

## 9. Apparatus to build after approval

- `S` and `C` as parameters of `CompetenceEvidence.maturity`, defaulting to the
  current values and carried by the profile, so every existing behaviour is
  byte-identical when they are not set (checked by a digest test).
- A study module with `run_one(seed, S, C)`, the two stages, and contract tests
  for the measures, the censoring rule and the selection rule.
- Both stages as governed runs through `agentctl run start`.

## 10. Cost

Stage 1 is 216 runs of 2000 ticks. At the transfer experiment's measured
cost, that is roughly three hours, as one governed run. Stage 2 is 24 runs.

## 11. Limits

The result holds for the synthetic causal Body with four actuators and this
horizon. A Physics3D replication would be its own preregistration. The study
tunes the establishment gate only; the binding degradation rule (Binding
Degradation v1) is a separate mechanism and is not an arm here.
