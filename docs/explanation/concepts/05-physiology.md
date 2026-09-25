---
id: explanation.web.05-fisiologia
title: "05 Physiology"
document_type: explanation
domain: concepts
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Physiology

<a id="que-es"></a>

## What it is

A Symbiont has an explicit internal economy: it spends finite computational resources on observing, thinking, remembering and maintaining itself, and that resource pressure determines whether the organism is active, stressed, dormant or dead. It is not a metaphor — it is real accounting that decides what the organism does when resources are scarce.

<a id="mecanismo"></a>

## Mechanism

`MetabolicLedger` manages four finite reserves: observation (reading sensors), cognition (activating and learning the graph), persistence (assimilating and consolidating memory) and maintenance (continuous basal expenditure). Physiological pressure is calculated as the minimum ratio between reserve and capacity of the four: above 0.5 is `NORMAL`, between 0.2 and 0.5 `ELEVATED`, below 0.2 `SEVERE`, and negative `UNRECOVERABLE`.

`HomeostaticController` translates that pressure into behavior: elevated pressure reduces the scale of activity; severe pressure reduces it more and additionally **disables cognitive plasticity** — the organism stops learning when under heavy stress, not just moving slower. Unrecoverable pressure or very low integrity activates a safe mode with minimal activity and blocked plasticity. Integrity repair consumes maintenance resources even when there is nothing to repair — repairing on an already intact body still costs, so that the organism has to learn the contextual pertinence of requesting repair, not receiving it for free by default.

Vital states form a strict transition machine: `ACTIVE → STRESSED → DORMANT/AGONIZING → DEAD`. Death is terminal and irreversible: if the runtime attempts to execute a tick after death, it raises an explicit error instead of simulating continuity. At the moment of death, the runtime atomically and only once releases the allocation in the shared ecological habitat, the social membership quota and the death record in the lineage authority — without leaving orphaned allocations or releasing twice.

Low-value retained state follows an explicit degradation cycle: active, aging, residue, and finally excreted — permanently purged from memory, incrementing only an aggregate counter. Nothing of what is excreted moves to an unbounded archive; it is truly lost.

<a id="implementado"></a>

## What is implemented

- Metabolic accounting of four resources with pressure derived from the minimum ratio — **[implemented]**.
- Homeostasis that reduces activity and pauses plasticity under pressure — **[implemented]**.
- Bounded repair that costs resource even without benefit on an intact body — **[implemented]**.
- Terminal and irreversible death with atomic release exactly once of ecological habitat, social habitat and lineage — **[implemented]**.
- Degradation and irreversible excretion of low-value state — **[implemented]**.

<a id="evidencia"></a>

## Evidence

It is proven that an unrecoverable pressure causes irreversible death, and that the runtime refuses to execute any tick subsequent to death. It is proven that physiological pressure reduces the activity scale and pauses plasticity simultaneously, not one without the other. It is proven that attempting to repair an already intact body consumes the effort resource without producing any real repair — the cost is neither free nor conditional on the result. And it is proven that the retained state effectively ages and ends up excreted, not accumulated indefinitely.

<a id="abierto"></a>

## What remains open (from this mechanism)

- The integrated longitudinal study of physiology (repair, bounded reproduction and social continuity in a single reproducible run) is evaluator-only: it exists as an external deterministic harness, not as a property that the organism observes or pursues by itself.
- The exact pressure thresholds (0.5 / 0.2) and the activity reduction factors (90% / 75% / 10%) are engineering parameters, not derived from a formal theory of optimal homeostasis.

<a id="respaldo-formal"></a>

## Formal backing

This chapter describes accounting and control engineering mechanisms, not a formal mathematical development of its own in the compendium. The self-model of cost and health of the organism — with which physiology shares the logic of EWMA and quantization — is in
[`docs/math/08-automodelo-y-sensores-adaptativos.md`](../math/08-automodelo-y-sensores-adaptativos.md).
