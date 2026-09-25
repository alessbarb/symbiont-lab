---
id: design.world.symbiont-world-v4
title: "Symbiont World V4"
document_type: design
domain: world
status: active
canonical: true
implementation_status: planned
migrated_on: 2026-09-25
last_reviewed: null
language: en
---
# Symbiont World v4 — Living World & Scientific Observatory

**Status:** design and technical specification for v4.
**Scope:** `symbiont_world` + `symbiont_lab.world` + World Scientific Observatory.
**Guiding principle:** the world evolves from a tabular grid to a continuous and dynamic ecological territory with visually alive and interactive organisms, without losing scientific rigor, tick atomicity, or the strict read-only discipline of the observer.

---

# 1. Goal: From "technical grid" to "ecosystem microscope"

Symbiont World v3 consolidated the atomicity (`failed_tick(s) == s`), the atomic persistence with SHA-256 verification (`future(continuous) == future(restore_from_disk)`), the causal journal, and the flicker-free rendering.

In v4, the ambition increases by an order of magnitude:

1. **The world acquires relief and living geography**: the territory is not a uniform array of cells; it possesses logical relief (elevation), permeability (corridors and barriers), gradients of moisture (`moisture`) and temperature, fertility, local disturbances, and traces left by organisms (footprints that decay).
2. **Explicit spatial movement**: organisms can move endogenously between passable cells according to permeability and occupation, leaving ecological trails.
3. **Organisms with morphology derived from phenotype**: the visual appearance of each individual is not an artificial skin, but a direct expression of its age, generation, developed sensors, physiological vigor, and cognitive connections.
4. **Movement interpolation and Ghost Mode**: the displacement between ticks is smoothly animated; we can activate the ghost mode (*ghost mode*) to track the complete historical trajectory of an individual.
5. **Spatial events on the terrain**: the confirmed facts of the journal (`RESOURCE_ACQUIRED`, `PHYSIOLOGICAL_DAMAGE`, `REPAIR`, `DEATH`, `MOVE`) generate temporary visual effects directly in the coordinates where they occurred.
6. **Comparative epistemological exploration**:
   - *World Reality*: ground truth of the scientific apparatus.
   - *Organism Perception*: what the individual actually captured through its transducers (with fog of perception).
   - *Organism Self & Mind*: internal hypotheses and cognitive graph (sensors → concepts → predictors).
7. **Population View and Virtualized Scale**: dedicated screen with phenotypic clustering, lineage graph, and Canvas-based rendering engine capable of fluidly scaling to large worlds with semantic pan/zoom.

---

# 2. Dynamic Geography: CellPhenotype

Each cell in the evaluator apparatus has complete topographical and dynamic properties. These properties are the **ground truth of the scientific apparatus**, never semantics delivered to the organism.

```text
CellPhenotype
├── q, r
├── region_id
├── elevation              # [0.0, 1.0] relief: valleys (0.1), plateaus (0.5), peaks (0.9)
├── permeability           # [0.0, 1.0] passability: open corridors (1.0) vs rocky barriers (0.2)
├── moisture               # [0.0, 1.0] moisture gradient: arid (0.1) vs wetland (0.9)
├── temperature            # [0.0, 1.0] thermal gradient: boreal cold (0.1) vs warm (0.9)
├── fertility              # [0.0, 1.0] modulates the resource renewal speed
├── disturbance            # [0.0, 1.0] recent environmental disturbance (temporally decays)
├── traces                 # [0.0, 1.0] accumulated intensity of organism passage (temporally decays)
├── resource_reservoirs    # current quantities and capacities
├── hazard_exposures       # real exposure weighted by local density
└── field_values           # global gradients and oscillations
```

### Resulting ecological emergence

- **Valleys and corridors**: cells with high permeability and moisture where transit and gathering are more efficient.
- **Barriers and peaks**: cells with high elevation and low permeability that act as natural ecological borders.
- **Refuge zones**: areas with a low `hazard` level and moderate fertility.
- **Footprints and routes**: cells through which organisms transit accumulate a trail (`traces`) that decays over time, allowing visualization of migratory routes and overexploited areas.

---

# 3. Resolution of Movement and Spatial Actions

Movement uses the deterministic infrastructure of `symbiont_world.movement.resolve_movement`:

1. Organisms can manifest a movement intention (direction 0..5 or rest).
2. The permeability of the destination cell is evaluated: cells with extremely low permeability act as impassable barriers.
3. Simultaneous intentions on the same cell are resolved with a deterministic tie-break using a namespaced RNG.
4. When an organism successfully moves:
   - A causal `MOVE` event is emitted and confirmed with the previous and new position.
   - The previous cell increments its `traces` (trail) level.
   - The body in `WorldState.bodies` updates `occupied_cell`.

---

# 4. Rendering Engine: Virtualized and Multilayer Canvas

To allow both test worlds (8×8) and medium (64×64) and large (128×128+) worlds, the observer implements a multilayer architecture:

```text
┌──────────────────────────────────────────────────────────┐
│                 OBSERVATORY RENDER ENGINE                │
├──────────────────────────────────────────────────────────┤
│ Layer 0: Terrain Canvas (biomes, relief, fog)            │
│ Layer 1: Trails & Heatmap Canvas (footprints, occupancy) │
│ Layer 2: Entity & Movement Layer (interpolated glyphs)   │
│ Layer 3: Spatial Events Layer (event particles)          │
│ Layer 4: Interactive Selection & Tooltip Overlay         │
└──────────────────────────────────────────────────────────┘
```

- **Pan & Zoom Support**: fluid navigation by mouse drag and zoom wheel.
- **Virtualization**: in large worlds, only the cells contained in the active viewport are rasterized.
- **Visualization Modes**:
  - *Reality*: view of the physical world with relief and biomes.
  - *Perception*: view from the senses of the selected organism (unperceived areas show exploration fog).
  - *Heatmap*: accumulated historical heatmap of occupancy.

---

# 5. Living Organisms and Phenotypic Morphology

The organism's glyph is built from its actual biological state:

- **Base body**: radius proportional to age/maturational development.
- **Integrity ring**: outer circumference with continuous colorimetry (emerald → amber → crimson) and stroke pattern according to vital state (`active`, `stressed`, `dormant`, `agonizing`, `dead`).
- **Metabolic core**: central core whose brightness and diameter indicate the level of energy reserve.
- **Sensory structures**: radial appendages/antennae whose number and length correspond to the discovered or specialized sensors.
- **Activity pulse**: brief expansive waves upon resource ingestion, damage, or repair.
- **Persistent corpse**: upon dying, an attenuated skeletal marker remains that fades after several ticks.

---

# 6. Temporal Dimension, Ghost Mode and Spatial Events

1. **Navigable Timeline**: horizontal scrubber to go back in the memory of registered ticks.
2. **Ghost Mode**: when clicking on an organism, its historical trail is displayed (`t-k → ... → t-1 → t`) with an opacity gradient, allowing its exploration decisions to be understood.
3. **Floating Events on the Map**:
   - `RESOURCE_ACQUIRED`: expansive cyan ring with quantity indication.
   - `PHYSIOLOGICAL_DAMAGE`: angular red flash at the position of impact.
   - `REPAIR`: soft green pulse.
   - `MOVE`: displacement vector with translucent arrow.
   - When clicking on a spatial event, its causal detail is opened in the inspector.

---

# 7. Four Epistemological Perspectives + Mind + Lineage

The side inspector delves into the epistemological structure:

- **[ Reality ]**: Relief, permeability, moisture, temperature, fertility, real local hazards, and cell resources.
- **[ Phenotype ]**: Morphology, physiological state, reserves, pressure, age, generation, and last action.
- **[ Perception ]**: Filtered signals that actually arrived at the receptors, with an option to activate the subjective view of the world.
- **[ Self ]**: Internal beliefs and self-perception without evaluator-side cheating.
- **[ Mind ]**: Active cognition graph showing the chain `Sensation → Concept → Prediction`.
- **[ Lineage & History ]**: Chronology of events in which the organism has participated.

---

# 8. Population Screen

An alternative view to the geographic map that offers aggregate ecological analysis:

- **Phenotypic Clustering (2D Scatter)**: distribution of individuals according to physiological dimensions (integrity vs reserve vs cognitive plasticity).
- **Lineage Tree**: genealogical graph of founders and descendants.
- **Macroecological Metrics**: diversity indices, global stress, and average longevity.

---

# 9. Implementation Plan

- **Phase P0 — Logical Relief, Dynamic Terrain and Spatial Movement**:
  - Definition of `CellPhenotype` and `DynamicGeography` in `symbiont_lab.world.terrain`.
  - Integration of movement intentions and spatial resolution in `PopulationGenesisRuntime`.
  - Deposit and decay of footprints (`traces`) and spatial `MOVE` events.
  - Unit tests for movement, permeability, and spatial conservation.
- **Phase P1 — Canvas Rendering Engine with Pan & Zoom**:
  - Replacement of the rigid grid with reactive, high-performance Canvas.
  - Implementation of camera control (zoom, pan, virtualized viewport).
  - Layers of relief (hill/valley shading), moisture, biomes, and footprints.
- **Phase P2 — Living Glyphs, Phenotypic Morphology and Interpolation**:
  - Glyphs with sensory antennae, integrity ring, and activity pulse.
  - Continuous interpolation of positions between ticks for fluid animation.
  - Persistent death markers and displacement trails.
- **Phase P3 — Temporal Navigation, Ghost Mode and Events on the Map**:
  - Temporal history scrubber with playback.
  - Ghost mode to visualize the past trajectory of an individual.
  - Spatial visualization of journal events directly on the terrain.
- **Phase P4 — Subjective Perspective (Perception Overlay) and Population View**:
  - Toggle of perception fog (world seen through the organism).
  - Population analysis screen (2D clusters of phenotype, state distribution).
  - Cognitive graph in the inspector (`Mind`).
- **Full Verification and Push**:
  - Execution of the full test suite (`pytest`).
  - Verification of determinism and strict reading.
  - `git push origin main`.
