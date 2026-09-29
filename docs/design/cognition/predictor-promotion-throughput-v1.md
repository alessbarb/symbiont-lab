# Predictor Promotion Throughput v1: preregistration draft

Status: **draft for owner review. Not approved, not implemented, not run. Not scheduled** (owner decision 2026-09-29: it is not the D1-v2 follow-up; if D1-v2 is not assessable, work moves to the remediation roadmap).

Origin: EW-D1A audit (`docs/design/vision/visual-acquisition-v1.md` §6.5). On the vision body, about 260–1200 visual shadow hypotheses were promotable by the organism's own evidence. Meanwhile the serial nomination path, with at most one predictor candidate in structural contention at a time, produced only 13–16 predictors across *all* targets by tick 1650. This is a generic cognitive question, not a Vision one, and it must not be answered inside D1-v2.

## 1. Question

> Does the serial predictor-promotion mechanism impose an artificial bottleneck when many independent hypotheses are promotable at the same time?

It is **not** "how do we get Vision more predictors". The serialization may serve a real function (stability, competition, complexity control) and is not assumed to be wrong.

## 2. Trade-off under study

Promotion throughput versus:
- predictive quality of promoted predictors on held-out data;
- stability: churn, retirements, revisions;
- model growth: nodes and edges against `max_nodes`;
- resource cost: metabolic charge and ms/tick;
- effect on existing gates (E6 and similar) and on Gates H and I.

## 3. Candidate designs (to be chosen by the owner before any run)

- **S (control).** The current serial nomination, one pending candidate.
- **K-parallel.** Up to k independent nominees in contention (for example k ∈ {2, 4, 8}), with the same admission criteria.
- **Evidence-ranked batch.** Same admission, but nomination ordered by the organism's own shadow evidence; this changes order, not rate.

Constraints for every arm: it must be a generic mechanism, the same for every modality and target, with no Vision-specific rule. No evaluator quantity may feed back into promotion. Gates H and I must hold.

## 4. Bodies and seeds (proposal)

- Two bodies, so the answer is not modality-specific: `anthropomorphic-v6` in `embodiment-nursery-v1`, and `anthropomorphic-v6-vision` in `vision-nursery-d1-v2`.
- Seeds: new and never used; to be fixed at approval.
- Development and held-out seeds are kept separate, as in D1.

## 5. Criteria

To be fixed with the owner before implementation. They should combine a throughput gain with **non-inferior** predictive quality and stability, and no regression of existing gates. No single overall score.
