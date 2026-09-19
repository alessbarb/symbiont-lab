# Pygame Habitat v1

Status: implemented candidate

## Goal

Provide a naturalistic, passive 2D habitat view of Symbiont World while keeping
Observatory as the scientific instrument and World as the only simulation owner.

The viewer must answer **what is happening in the habitat?** without becoming a
second scientific dashboard or feeding any state back into World.

## Non-negotiable boundary

```text
World runtime
   ↓
Observatory read-only HTTP
   ├── /world/state
   └── /world/events
            ↓
      Pygame habitat
```

The viewer:

- imports no `symbiont_lab.world` or `symbiont_world` module;
- accepts only loopback HTTP;
- has no action, step, pause-world or mutation endpoint;
- freezes only local rendering when the user presses Space;
- treats missing or stale observer data as an observation problem, not a World
  state transition.

## Package structure

```text
src/symbiont_lab/viewer/
├── client.py          loopback-only Observatory transport
├── projection.py      observer JSON → renderer-safe physical state
├── camera.py          coordinate transforms, viewport and LOD
├── scene.py           interpolation, spatial index, morphology and effects
├── renderer.py        Pygame drawing only
└── world_pygame.py    event loop / local interaction
```

Pygame itself is imported lazily by the entrypoint. Projection, camera, scene and
client remain testable on headless machines without the optional dependency.

## Representation contract

### Terrain

The computational World remains hexagonal. The normal habitat view does not show
hex borders. Cells overlap visually and receive soft blending so physical fields
read as continuous geography.

Appearance is derived from observer-visible physical quantities:

- elevation;
- moisture;
- temperature;
- fertility;
- disturbance;
- traces;
- aggregate material abundance;
- aggregate hazard exposure.

Pressing `G` reveals the computational hex grid strictly as a debugging overlay.

### Material abundance

The renderer deliberately does not preserve or display human semantic resource
labels. Opaque resource pools are normalized against their capacities and combined
into a local abundance magnitude. The visible motes are therefore a representation
of **material presence**, not a declaration that something is food.

### Organisms

Body size reacts to observer-visible metabolic reserve; condition reacts to
integrity; sensor count affects visible appendage structure.

Identity is explicitly excluded from morphology generation. Two organisms with
the same externally observable structural inputs render with the same shape.
Private cognition, beliefs, concepts, attention and SelfModel are not accepted by
the habitat projection.

### Motion

World coordinates remain discrete and authoritative. The scene keeps previous and
target observer positions and uses smoothstep interpolation between them.

```text
World position(t) → observer snapshot → visual interpolation → screen
```

There is no reverse path.

### Events

`/world/events` is converted into non-textual transient effects:

- damage/hazard/collision → shock;
- acquisition/consumption → absorption;
- death → collapse;
- birth/reproduction → emergence;
- repair/recovery → recovery;
- movement → motion trace.

Unknown event kinds are ignored rather than invented.

### Persistent traces

Neighboring cells with sufficiently strong World `traces` are connected
visually. Repeated traffic can therefore create visible paths because the World
state changed, not because Pygame inferred a route.

## Camera and scale

The initial camera fits the entire observed World. `R` restores that framing.

LOD tiers:

- **near**: morphology, sensor appendages, motion tails, environment detail;
- **mid**: simplified organisms and environment;
- **far**: population points and terrain only.

A chunked spatial index (default 8×8 axial cells) restricts cell/organism traversal
to the camera viewport. Rendering cost therefore depends primarily on what is
visible, not total World population.

## Controls

- `WASD` / arrows — pan;
- mouse wheel or `+`/`-` — zoom;
- `F` / `Tab` — follow next organism;
- click organism — follow it;
- `R` — fit whole World;
- `G` — debug grid;
- `H` — HUD;
- `Space` — freeze/unfreeze local view;
- `Esc` — quit.

All controls are local presentation state.

## Scientific interpretation

Pygame is a phenomenological window, not an explanatory apparatus.

```text
Pygame      → behavior / physical manifestation
Observatory → telemetry / cognition / causal investigation
```

A surprising behavior should first be visible in the habitat. Its cognitive or
experimental explanation belongs in Observatory.

## Validation

Unit coverage verifies:

- physical projection and clamping;
- no semantic resource dependency;
- loopback-only transport;
- axial/world coordinate roundtrips;
- zoom/LOD bounds;
- interpolation without endpoint mutation;
- identity-independent morphology;
- event manifestation and expiration;
- chunked spatial visibility;
- absence of imports from World in every viewer module.

Graphical integration still requires a machine with a display and the optional
`pygame` dependency.
