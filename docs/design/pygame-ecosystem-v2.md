# Pygame Ecosystem v2

Status: implemented candidate

## Purpose

Evolve the passive Pygame habitat from a scientific-looking naturalist map into a
visually coherent ecosystem while preserving the same epistemic boundary:

- World owns reality and simulation time;
- Observatory exposes read-only physical observation;
- Pygame renders only observable physical consequences.

No visual system introduced here is allowed to become an input to World.

## New capabilities

### Continuous environmental transitions

Each observed cell is tracked between consecutive snapshots. Elevation, moisture,
temperature, fertility, traces, disturbance, population density, material
abundance and hazard exposure are interpolated with smoothstep.

This removes visual discontinuities without altering authoritative World state.

### Relief

Terrain shading uses local gradients in observed elevation. The renderer derives a
directional relief factor from neighboring elevations and applies it to the
underlying physical color field.

Relief therefore indicates geometry rather than a hand-authored biome type.

### Surface water

World Ecology v1 now exposes real dynamic `surface_water`. The reflective layer
renders that state directly; it no longer infers water from moisture/elevation.

The broader terrain color field still uses raw moisture, elevation and effective
fertility as physical visual encodings.

### Ambient physical motion

At near LOD, cells can display deterministic ambient particles. Particle activity
is controlled by observed:

- moisture;
- temperature deviation;
- disturbance.

Particle positions are deterministic per physical cell/lane and time. They add no
new stochastic state and cannot affect World.

### Persistent remains

An observed death event, or an alive→dead transition in the snapshot, creates one
visual remnant at the last observed physical position.

Remnants:

- are presentation-only;
- are deduplicated per organism identity;
- decay visually over a bounded lifetime;
- never imply decomposition mechanics inside World;
- disappear from Pygame without deleting or mutating any World entity.

### LOD behavior

Far:
- terrain and population points.

Mid:
- terrain, paths, simplified environment and organisms.

Near:
- relief detail;
- material motes;
- hazard haze;
- persistent traffic paths;
- ambient physical particles;
- organism morphology and sensor appendages;
- transient event effects;
- death remnants.

## Scientific constraints

The viewer still imports neither `symbiont_lab.world` nor `symbiont_world`.

The ecosystem layer may derive presentation quantities from physical observation,
but must not:

- create semantic resource categories;
- infer surface water when World does not report it;
- infer intentions;
- inspect cognition;
- add simulated weather not present in observed fields;
- fabricate births/deaths;
- alter movement;
- feed camera/selection state into the organism or World.

## Validation

Unit coverage now includes:

- temporal environmental interpolation;
- elevation-gradient relief;
- deterministic ambient seeds;
- death-remnant creation and deduplication;
- remnant expiry;
- fallback remnant creation from observed alive→dead transition;
- continued no-World-import invariant.

Graphical QA still requires a machine with a display and the optional Pygame
dependency.
