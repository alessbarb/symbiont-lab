# Anatomy of a perception

A perception is not a sensor reading with a nicer name. It is the result of several transformations that progressively separate physical measurement from organism-owned representation.

Consider a physical receptor value in Physics3D.

```text
physical state
→ apparatus receptor
→ SensorReading
→ organism-owned sensor
→ transduction
→ Percept
→ acclimation / drift / attention
→ cognitive evidence
```

The apparatus and reading provider know which physical channel produced the reading. The adaptive sensory system may deliberately discard that semantic name and use a stable opaque sensor identity instead. That identity has its own maturity, cost, quality history and structural ancestry.

`SensorySystem.transduce()` constructs source-indexed readings, ensures appropriate identity sensors, checks source availability and quality, advances sensor maturity and applies the configured transduction. A sensor may depend on one source or combine several.

The resulting percept enters `PerceptionDomain`, where it can contribute to baseline statistics, rhythm, drift detection, signal-knowledge updates and attention allocation. None of those stages automatically establishes external semantic meaning. They establish relationships such as stability, novelty, covariance, usefulness and reliability.

A perception becomes scientifically meaningful when downstream mechanisms use it: a drift event may trigger investigation; a repeated proprioceptive pattern may contribute to body schema; a sensorimotor consequence may provide causal evidence for a competence; a prediction error may revise cognition.

The provenance of those downstream changes should therefore point back to the relevant perceptual evidence rather than merely to the name of the processing module.
