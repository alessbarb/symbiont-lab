# Perception and sensory development

Perception begins before the organism has any reason to understand what a signal “means”. The architecture therefore treats transduction, identity, acclimation, drift and learned significance as separate problems.

## From receptor to percept

External providers produce bounded `SensorReading` values. `PerceptionDomain` coordinates lifecycle sampling, adaptive selection, sensory transduction, acclimation, drift analysis, signal identity, signal knowledge and attention allocation. Its output is a set of organism-facing percepts plus supporting evidence such as signal references and drift observations.

The central organism-owned transducer is `SensorySystem`. Its sensors have identities, source bindings, modalities, transduction rules, maturity and cost. In adaptive mode, sensor names are stable internal identities. This prevents source-level labels from silently becoming semantic knowledge.

## Sensory development

The sensory phenotype is mutable within hard limits. Sensors may be duplicated or rewired into multisource sensors, and each structural change is recorded as a bounded `SensoryMutation`. The system therefore allows learned perceptual organisation without allowing unbounded growth.

The distinction between germinal capacity and acquired phenotype is explicit: `SensorySystem.germinal_copy()` copies capacity and modalities but not the acquired sensor phenotype.

## Acclimation and drift

A signal cannot be interpreted sensibly without some notion of ordinary variation. Host acclimation and drift baselines estimate changing distributions over time. Regime shifts are deliberately separated from stable baseline update so that a sudden change does not instantly redefine itself as normal.

This is not semantic classification. A drift detector can establish that a signal changed relative to its history without knowing whether the change means heat, injury, load or something else.

## Attention and sampling

When discoverable surfaces are larger than the organism can inspect continuously, sampling becomes selective. Adaptive sensing produces a sampling plan; attention then constrains which perceptual evidence receives further processing. Attention is therefore a resource allocation mechanism, not a labeler of truth.

## Interoception

Interoceptive channels expose limited organism-relevant physical state through the same epistemic discipline. Physics3D uses an opaque interoceptive mapping rather than handing the organism the laboratory's physiological names. This allows homeostatic state to become perceptually relevant without collapsing the world/observer distinction.

### Principal implementation anchors

- `src/symbiont/core/domains/perception.py`
- `src/symbiont/sensory/system.py`
- `src/symbiont/host/acclimation.py`
- `src/symbiont/host/drift.py`
- `src/symbiont/host/adaptive.py`
- `src/symbiont/core/cognition/attention.py`
