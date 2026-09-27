---
title: Body in World observation contract
status: implemented
canonical: true
---

# Body in World v1

## Audit of main b6d3635 (27 September 2026)

1. **World:** `symbiont_world/state.py`, `topology.py`, `contracts.py` and
   `symbiont_lab/world/runtime.py` implement a persistent hex ecology. Physics3D
   is a different environment: `physics3d/runtime.py` owns its PyBullet client,
   infinite plane, articulated apparatus and `PhysicalResource`. They do not
   share a coordinate system or placement. Do not merge their scenes.
2. **Transport:** `observation/physics3d.py` projects physical frames into
   body/body_pose and cognition/vitals/mind_snapshot events, paired by tick in
   ObservedFrame. Body's EventSource consumes these directly. The bounded
   ObservationBus drops old queue entries; replay of last-by-type is insufficient
   for dependent deltas. Atlas has a diff utility, but does not provide spatial
   world entities or reconnect reconciliation for Body.
3. **Space:** apparatus exports authoritative base and link poses, joints, COM,
   contact positions/normals/forces and counterpart physics IDs. Resource exports
   radius, position, remaining material and scalar field support radius. The UI
   previously assumed a 0.18 m sphere and drew a 100 m plane without an observed
   world contract. No actual obstacles are present in this runtime by default.
4. **Perception:** PhysicsReadingProvider records requested samples only;
   pre.sensory_input.values is not the same as runtime.percepts. The latter are
   organism-produced percepts. observer_semantics maps their opaque names back
   to source receptors. Current apparatus has proprioception, body kinematics,
   regional contact/load, interoception and one non-directional scalar field.
   It has no camera, object detector, vision cone or metric range sensor.
5. **Self:** BodySchema exports opaque sense/cognitive-region parts, maturity,
   confidence, recency and evidence-backed dependencies. SelfModel and acquired
   action dimensions have additional evidence. Part IDs must not be equated
   with anatomical segment names. Existing Self View uses humanoid ordinal
   mappings; new spatial overlays instead use the active apparatus descriptor.
6. **Environment knowledge:** cognitive predictors, effects, competencies,
   affordances and self/external channel evidence exist. None of the examined
   contracts proves a metric map, object permanence, object identity linked to
   world IDs, semantic categories or predicted world-space trajectories.
   Learning a field signal is not learning where its source is. Familiarity of
   a signal is not familiarity with an object.
7. **Missing:** an observer-owned spatial scene, physical IDs translated into
   stable scene IDs, per-receptor physical anchoring, separate sampled/perceived
   evidence, initial snapshot/delta reconciliation and contextual selection.
8. **Direct implementation:** project the active physical environment, current
   contact geometry and existing sensory/self evidence. Preserve unavailable
   spatial knowledge explicitly. Do not alter cognition, genome or world laws.

## Contract and boundary

World != Body != Embodiment != Symbiont. New `world_scene` data is observer-only,
produced by Physics3D and carried by the existing observation bus. It is not
part of organism checkpoints, receptor readings, genome or decision inputs.
The exporter reads collision shapes from the real engine, rather than creating
another simulator or a hand-authored frontend world. Unsupported shapes are
reported, not replaced with invented geometry. Plane display is a finite
observer window into an infinite surface, not a wall or physical boundary.

`world_id` scopes native physics entity IDs to an observation session;
`embodiment_id` and `body_id` remain separate. Revision is a transport revision,
not a cognition tick. Coordinates are metres, PyBullet Z-up, XYZW quaternion.

A full snapshot has entities keyed by stable ID, receptor anchors, physical
contacts, perception samples (pre-action phase), signal evidence and explicit
capability availability. Post-action physical contacts must not be confused
with pre-action tactile perception. Ground-truth source attribution remains
observer inference even when a signal is represented internally.

State dimensions are independent: exists, modality supported, receptor sampled,
nonzero stimulus, organism percept emitted, internal signal representation,
spatial object representation, object familiarity, spatial prediction. Missing
information is unavailable, never false confidence or inferred knowledge.

Known World and Predictions explain missing spatial grounding. They do not
paint known/predicted objects by proxy from a signal. Actual signal predictions
and motor relations remain inspectable via existing Mind/Atlas and Self View.
No hypothetical learned object store is introduced in v1.

## Incremental transport

The producer emits a full `world_scene` followed by upserts/removals,
transform-only changes and changed evidence fields. Every delta includes base
revision. ObservationBus materializes the latest full scene for reconnect and
GET /api/world-scene. Client rejects gaps and fetches a fresh snapshot; stale
responses cannot replace newer state. This also repairs queue overflow and
expired replay. IDs reset on a new observation session. Deletions dispose GPU
resources and clear selection. World events never enter dense body_pose frames.

Physics integration, cognitive ticks, rich observation cadence, SSE delivery
and requestAnimationFrame remain independent. Body keeps its existing pose
interpolator. Spatial evidence is shown at its recorded tick and phase; no
extrapolated perception. Static geometry is reused across updates.

## UI

One scene with Physical, Perception, Self Model, Known World, Predictions and
World Truth toggles; world truth is visibly labeled as observer knowledge.
Unknown world objects remain wireframe in truth mode. With truth off they are
hidden unless a future explicit spatial representation supports them. Perception
shows the recorded receptor locations and contact evidence; the scalar field's
support sphere is visible only with World Truth because its origin/radius are
not known to the organism. Self colors refer to mapped signal confidence,
not anatomical concepts acquired by Symbiont. One contextual inspector shows
positions, contacts, source IDs, samples, percepts and self evidence with ticks.
No reach sphere, vision cone, chair category or imagined trajectory is fabricated.
