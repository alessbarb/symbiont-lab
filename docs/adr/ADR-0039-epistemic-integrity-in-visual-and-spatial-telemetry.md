# ADR-0039: Epistemic Integrity in Visual and Spatial Telemetry

## Status

Accepted

## Context

Scientific visualization dashboards (such as the Observatory and Workbench) often plot organism signal states and contact forces at 3D world coordinates alongside the physical body mesh. This creates a severe epistemological illusion: human observers looking at the dashboard may infer that the organism possesses an allocentric spatial coordinate system, object permanence, or a global map of its surroundings, when in reality the organism only receives opaque, ungrounded scalar receptor streams.

## Decision

1. **Observer placement versus acquired structure.** Spatial placements, 3D coordinate callouts, and dashed lines rendered in Observatory interfaces are strictly apparatus-side correlations for researcher interpretation. They do not represent cognitive representations possessed by the organism.
2. **Explicit visualization demarcation.** The visualizer must clearly differentiate:
   - *Physical Surroundings:* Ground-truth engine collision shapes and contact points (known only to the simulator);
   - *Transduced Percepts:* Egocentric, opaque receptor readings captured by the organism;
   - *Internal Cognitive Graph:* Sensor-to-concept and concept-to-predictor topologies (which possess zero spatial coordinates).
3. **Prohibition of synthetic cognitive edges.** The visualization layer must never synthesize spatial proximity edges or connect organism concepts using geometric nearest-neighbor heuristics. If no causal signal reference exists in the organism's evidence logs, no link may be displayed.
4. **Phase separation.** Pre-action receptor anchors and post-action contact feedback are rendered as distinct temporal phases; the visualizer must not animate synthetic causal propagation between them.

## Consequences

- Preserves scientific honesty and prevents researchers from misinterpreting passive visual conveniences as artificial cognitive competence.
- Ensures strict alignment between published scientific claims and underlying algorithmic reality.

## Introduced in

Milestone OW (Experienced World / Observatory Integration).

## Evidence

`docs/design/observatory/experienced-world-v1.md`, `src/symbiont_lab/observation/world_scene.py`, `tests/unit/observatory/test_world_integration.py`.
