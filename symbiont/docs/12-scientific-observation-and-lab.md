# Scientific observation and the laboratory

The laboratory exists to make Symbiont observable without becoming part of its cognition. That sounds obvious, but it is one of the easiest boundaries to violate accidentally.

## What the laboratory is allowed to know

`symbiont_lab` can know experiment configuration, ground truth, body geometry, resource distance, evaluator metrics, full physical state and historical traces. The organism may know only a transformed subset of those facts through legitimate sensory or social channels.

A visualization can therefore display more than the organism knows. The UI must make that difference legible rather than projecting observer semantics back into the subject.

## Observatory

The observation package projects runtime snapshots into researcher-facing views. Current modules include the cognition atlas, event bus, physics projection, world scene and provenance journal. Observatory should remain passive: it may aggregate, label and visualize, but not issue hidden cognitive instructions.

## Physics3D

Physics3D is a laboratory implementation of embodied dynamics. It owns the physical solver, bodies, contact, resource geometry and other world/body facts. It can expose a presentation stream at a higher visual cadence than cognition without adding extra organism ticks.

## Telemetry

Telemetry serves two roles. First, it makes a run inspectable. Second, it supplies evidence for later experiments and debugging. A telemetry field must therefore be classified by authority: is it emitted by the organism, derived by the laboratory, or read directly from the physical simulator?

Without that classification a future researcher could mistake a derived evaluator field for evidence that the organism itself represented the same quantity.

## Causal journal

The laboratory provenance journal receives causal events from outward-only subscriptions. It provides the durable historical layer that the organism's bounded in-memory provenance cannot retain forever. Because the journal does not feed back, it can be richer without becoming an implicit memory extension for the subject.

### Principal implementation anchors

- `src/symbiont_lab/observation/*`
- `src/symbiont_lab/physics3d/*`
- `docs/design/telemetry/physics3d-telemetry-v4.1.md`
- `docs/design/observability/self-model-workbench-v1.md`
- `docs/design/observatory/body-in-world-v1.md`
