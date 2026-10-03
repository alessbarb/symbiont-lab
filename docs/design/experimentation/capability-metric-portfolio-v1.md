---
id: design.experimentation.capability-metric-portfolio-v1
title: "Capability Metric Portfolio v1 — Proposal"
document_type: design
domain: experimentation
status: proposed
canonical: false
implementation_status: not-started
date: 2026-10-02
depends_on:
  - research/audits/current/2026-10-02-symbiont-metric-audit.md
language: en
---

# Capability Metric Portfolio v1 — Proposal

**Status:** proposed for scientific-owner review. This portfolio is not an
approved protocol, threshold set, readiness gate, or experiment authorization.
It does not change the research programme, existing protocols, runners, or
historical artifacts.

## 1. Purpose and boundary

Provide a common reporting structure for capability-specific evidence used to
reason about Symbiont readiness. It is not a universal intelligence score.
Individual studies select only the dimensions relevant to their preregistered
claim; this document does not require every study to measure every dimension.

The current audit in
[`research/audits/current/2026-10-02-symbiont-metric-audit.md`](../../../lab/research/audits/current/2026-10-02-symbiont-metric-audit.md)
records the source studies, artifacts, implementation observations, and
limitations underlying this proposal. Their outcomes remain bounded to those
studies.

## 2. Reporting contract

For each selected metric and condition, report the raw numerator and
denominator, the derived rate when defined, per-seed/run values, missing or
censored cases, and uncertainty at the independent sampling unit supported by
the protocol. Do not treat repeated observations within one organism/run as
independent organisms. Keep positive, negative, null, and not-testable outcomes
visible.

If the denominator is zero, report the rate as unavailable (for example,
`null`) and retain the zero denominator. Do not encode no opportunity/no event
as a zero success rate or as maximal reuse. A numeric zero means the event was
observable and the numerator was zero.

Separate apparatus integrity (source revision/dirty state, protocol identity,
replay, missingness, and evaluator isolation) from capability outcomes. An
integrity failure constrains interpretation; it is not a capability penalty
that can be averaged into a score.

## 3. Capability-specific dimensions

Select dimensions by scientific claim and preserve control contrasts rather
than pooling rival explanations:

| Claim family | Report separately | Interpretation boundary |
| --- | --- | --- |
| Causal agency | Detection of genuine effects; false-positive rates for independent, confounded, yoked/external, and sham conditions where present; confidence distributions and thresholded decisions | One thresholded success rate is not threshold-independent discrimination or confidence calibration. |
| Causal revision | Belief/model revision; structural mapping change; sham specificity; non-reviser counts and revision latency/censoring | Mapping change alone is not evidence of causal-model revision. |
| Temporal attribution | Outcomes by fixed delay class and variable-delay condition | Do not hide delay-specific failures in a pooled rate. |
| Acquisition and re-embodiment | Body/task-specific acquisition, uncertainty change, reacquisition or recovery across the preregistered phases; identity/state continuity as integrity | A return advantage or final-state match alone does not establish continuity or reacclimation. |
| Transfer and OOD | Held-out utility/degradation, uncertainty response, recovery, stale-belief persistence, and transfer, as applicable | Keep distinct from acquisition and from one another; held-out use requires its existing authorization. |
| Genetic/developmental | Genotype-expression consistency, phenotype divergence, and inherited-state isolation | Report consistency and divergence separately; do not infer mechanism from correlation alone. |
| Social/communication | Signal use, opportunities/silence, costs, acquisition, source calibration, dependency, persistence, and held-out utility as applicable | Utility, code structure, productivity, compositionality, and language are distinct claims. |

Event-derived rates must include eligible-event and opportunity counts. For
communication, keep prediction gain, entropy/information measures, reuse,
held-out utility, and productivity distinct; document evaluator-only quantities
and their isolation from organism cognition.

## 4. Analysis and decision limits

The protocol must identify the independent unit before selecting summary
statistics. Show per-seed/run outcomes and a distribution or uncertainty
interval that respects that unit. Do not introduce ROC/AUC, calibration claims,
acceptance thresholds, or cross-study rankings unless their sampling,
outcome definition, and decision rule are separately justified and approved.

This portfolio supplies no thresholds and cannot be used to retrospectively
reclassify existing studies. Any operationalization in a confirmatory or
held-out protocol requires a separate versioned, preregistered amendment and
the applicable owner authorization. Frozen evidence remains unchanged.

## 5. Decision requested

The scientific owner is asked to accept, revise, or reject this non-binding
reporting direction. If accepted, each future protocol should define only its
claim-relevant metrics, denominators, controls, sampling unit, censoring,
uncertainty analysis, and decision criteria before outcomes are inspected.
Acceptance of this portfolio alone does not authorize protocol changes,
threshold selection, implementation, or experiment execution.

## 6. Evidence provenance

This proposal derives from the current metric audit dated 2026-10-02 and its
bounded inspection of programme §27, existing protocols, result artifacts,
and current runners. The audit notes dirty source manifests for historical
causal results and a zero-event communication reuse-rate semantic defect.
These limitations are retained; no rerun or historical artifact migration is
claimed here.
