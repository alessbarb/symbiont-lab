---
id: explanation.web.09-metodologia-y-limites
title: "09 Methodology And Limitations"
document_type: explanation
domain: concepts
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Methodology and limitations

<a id="que-es"></a>

This chapter is transversal: it does not follow the fixed spine of chapters 1-8. Here we document how the evidence cited in the rest of the series is generated, and what generalization limits apply across all mechanisms, instead of repeating the same warning eight times.

<a id="metodologia"></a>

## Experimental methodology

The project's synthetic experimentation follows five fixed principles:

1. **Deterministic isolation of RNG streams** — unrelated randomness must never interfere with each other; streams are derived via SHA-256 with separate namespaces.
2. **Causal prefix integrity in attention** — attention selectors process events sequentially and can never look at future scores nor global results.
3. **Shadow-only observation** — the observer's experimental hooks (retrospective budgets, counterfactual sensors) operate strictly in shadow mode: they never perturb the agent's actions, the collective memory, nor the state of the world.
4. **Replicated paired designs** — multi-seed studies preserve the world/seed pairing between compared interventions, to maximize statistical power and eliminate inter-world variance bias.
5. **Explanatory, non-operational reasoning** — internally generated hypotheses serve an interpretative, information-seeking function, they never trigger external operational actions.

<a id="preregistro"></a>

## Pre-registration and audits

Protocols are formally declared before data collection (`research/protocols/`), and replication studies are declaratively specified (`research/studies/`) before execution. Adversarial audits (`research/audits/`) verify the experimental integrity of the simulator itself and the laboratory apparatus — they do not only measure the organism, but also attempt to find methodological flaws in how it is measured.

For example, the v0.13.0 version audit explicitly documents a provenance correction discovered during the analysis itself: a replication file turned out to belong to a different commit than declared, and that discrepancy is recorded and separated from the main table instead of being silently mixed in. This is deliberate: the project treats data provenance errors as findings to be documented, not as noise to be discarded.

<a id="limites-transversales"></a>

## Transversal generalization limits

These limits apply across all mechanisms described in chapters 1-8, not to a single one:

- **Autonomous multi-organism emergence** (ecology, sociability) is measured solely in evaluator-only laboratory harnesses, under controlled synthetic regimes. There is no evidence that this behavior generalizes to production without laboratory supervision.
- **Predictor promotion** in the predictive development cycle is an explicit and bounded operation; its generalization outside the studied regimes remains open.
- **Cross-platform coverage** beyond Linux retains a historical cross-verification caveat, documented as a verification limitation, not as a development blocker.
- **No laboratory study feeds back into the organism's cognition**: evaluator metrics, including those in this very chapter, exist to measure from the outside, never to teach from the inside — it is the same epistemological boundary from chapter 1, now applied to the methodology that produces the evidence cited throughout the series.

<a id="respaldo-formal"></a>

## Formal backing

The five methodological principles are in [`docs/methodology/README.md`](../methodology/README.md). Pre-registered protocols live in `research/protocols/`, declarative studies in `research/studies/`, and adversarial audits in `research/audits/`.
