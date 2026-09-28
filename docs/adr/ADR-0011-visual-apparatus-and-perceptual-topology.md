# ADR-0011: Visual Apparatus and Perceptual Topology (ADR-EW-004)

## Status

Accepted. Decision 2 is reversible.

## Context

The Experience & World specification (§7, §13–15 of the gap analysis) requires Vision to arrive as a causal apparatus: physical world → apparatus → physical sample → opaque receptor channels → cognition. Observer geometry (`world_scene`, `PhysicsWorldObserver.entities`) is not a valid substitute. Gap decision D3 was left open for this ADR.

## Decision

1. **Topology (gap decision D3).** Physical receptor adjacency is apparatus-given structure. Grouping into sources is acquired structure. The apparatus owns a `PerceptualTopology`: neighbour lists over opaque receptor ids. It carries no coordinates, rows, columns, depth, distance, colour names or eye semantics. In this milestone nothing in cognition consumes the topology. Exposing it to Symbiont needs a later, explicit contract.
2. **A new body kind, not a modified body.** Vision ships as `anthropomorphic-v6-vision`. The receptor contract of `anthropomorphic-v6` is left unchanged. Changing it would alter the contract fingerprint of every stored organism and every running study. Entering the vision body is an ordinary re-embodiment into a new epoch. This is reversible: a later ADR may fold vision into a future body version.
3. **Apparatus.** A single receptor array is mounted on the head link. It samples once per cognition tick, using the deterministic CPU renderer, and depends only on the simulation state. Each receptor delivers a bounded luminance value in `[0, 1]`. The apparatus does not deliver depth, segmentation, entity identity or RGB channel names. The presentation camera, render cadence, `world_scene` and wall-clock time never feed the apparatus.
4. **Size and sensory budget.** The array is 12×12 (144 receptors), following the specification's "start small" principle. Measurement changed the budget premise: v6 already admits about 152–173 active sensors (107 receptors plus proprioceptive derivations), not 107. Under the shared cap of 256, the vision body filled the cap, and 34 body senses were silently squeezed out by visual ones. `BodyDescriptor.sensory_capacity` therefore makes the budget per body. It stays at 256 for every existing body, which leaves v6 unchanged, and is 512 for the vision body. After 120 ticks the vision body admits 143 of 144 visual receptors, and more non-visual senses than v6 (229 vs 173). **Provisional:** sensor counts were still growing between 48 and 120 ticks. A long-horizon check is still pending: plateau below 512, the v6 source set contained in the vision set, and a sensory checkpoint under the 1 MiB `max_sensor_checkpoint_bytes`, which raises if exceeded. Measured cost is +95 ms per tick over v6 in the same nursery (306 ms vs 211 ms, headless, on the development machine). Rendering takes 0.22 ms of that; the rest is cognition scaling with the extra senses. Whether 12×12 suffices for acquisition is an empirical question for EW-D.
5. **Opaque identities.** Visual receptors extend the existing `rec.N` namespace (`rec.107`–`rec.250`) through a fixed, versioned permutation of array positions. Receptor ordinals therefore do not reveal array layout.
6. **Nursery.** `vision-nursery-v1` is a versioned environment recipe with luminance contrast. Luminance is a fixture property of the recipe only; existing recipes are unchanged. Independently moving sources and occlusion schedules belong to EW-D.
7. **Launchability.** The `vision-nursery-v1` run definition becomes launchable, and it requires the vision body kind.

## Consequences

- Gate D (visual acquisition) is not claimed. EW-C delivers only the substrate: the apparatus, opaque channels, topology, deterministic sampling and isolation tests.
- Raw receptor-field observer transport is not chosen here (gap D4). It must be benchmarked before any Vision UI.

## Introduced in

Milestone EW-C.
