---
id: explanation.web.02-cuerpo-y-percepcion
title: "02 Body And Perception"
document_type: explanation
domain: concepts
status: unclassified
canonical: false
implementation_status: unknown
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Body and perception

<a id="que-es"></a>

## What it is

A Symbiont does not receive a list of sensors with human names ("CPU usage", "temperature"). It discovers numerical, bounded and vetted observation surfaces within the host, assigns them opaque identities, and learns their reliability and statistical usefulness before deciding which ones to keep as active senses. The body of the organism is, in that sense, learned, not configured.

<a id="mecanismo"></a>

## Mechanism

Safe perception rests on explicit privacy contracts before touching any statistics. `Capability` prohibits any metadata containing system identity keys (`hostname`, `username`, `ip`, `mac`, etc.) — the check occurs at construction, not as a documentary convention. `ReadingPrivacyClass` only admits the values `AGGREGATE` and `NON_IDENTIFYING`: there is no variant that allows identifiable telemetry.

On that basis, `RunningStats` builds baselines with the online Welford algorithm — constant memory, without saving the history of raw samples. `CapabilityBaseline` exposes only `count`, `mean`, `variance` and `stdev`: no "threat" or "anomaly" indicator comes out of this layer, so that perception does not usurp cognitive judgment.

`DriftAwareBaseline` distinguishes three phenomena that a naive adaptive filter confuses: an isolated spike is temporarily quarantined and only confirmed as a regime shift if the deviation persists several consecutive ticks in the same direction; a slow creep is detected by comparing a fast EWMA against a standard deviation frozen at the moment of acclimation, so that the rolling variance does not inflate at the same rate as the drift itself and make it invisible.

Finally, `AdaptiveSenseModel` decides which signals to keep: a utility function combines availability, variability and mean movement, and `PairAccumulator` prunes redundant sensors when their Pearson correlation exceeds a high threshold — saving observation budget without losing distinct information.

<a id="implementado"></a>

## What is implemented

- Privacy contracts that block identity metadata at construction — **[implemented]**.
- Online statistical acclimation (Welford) without retention of raw samples — **[implemented]**.
- Distinction between isolated spike, regime shift and slow creep — **[implemented]**.
- Pruning of sensory redundancy by Pearson collinearity — **[implemented]**.
- Selection of which candidates enter the active sensory repertoire of the organism is a continuous process of the whole life cycle, not a one-time boot decision — covered in detail in predictive development (chapter 8).

<a id="evidencia"></a>

## Evidence

Three concrete behaviors are covered by deterministic tests: the confirmation of a regime shift requires a sustained streak of deviations (not a single atypical sample); a constant slow creep is confirmed as `CREEP` without ever triggering a `REGIME_SHIFT`, even after 200 ticks of continuous drift; and the acclimation baseline does not expose any classification surface — only descriptive statistics. The pruning of sensory redundancy is also tested: a sense highly correlated with a complementary signal already present is omitted from the active repertoire.

<a id="abierto"></a>

## What remains open (from this mechanism)

- The confirmation thresholds (minimum streak, drift Z, correlation threshold) are engineering heuristics, not proven optimal properties — the mathematical compendium explicitly classifies them as heuristics, not as structural invariants.
- Platform coverage beyond Linux remains with the historical cross-verification caveat documented in the roadmap; it is not treated as a blocker for Linux development.

<a id="respaldo-formal"></a>

## Formal backing

The complete analytical development — univariate and bivariate Welford numerical stability, the derivation of the frozen noise floor for creep detection, and the dynamic utility function of sensory selection — is in
[`docs/math/02-percepcion-aclimatacion-y-relaciones.md`](../math/02-percepcion-aclimatacion-y-relaciones.md)
and
[`docs/math/03-deteccion-de-deriva-y-regimenes.md`](../math/03-deteccion-de-deriva-y-regimenes.md).
