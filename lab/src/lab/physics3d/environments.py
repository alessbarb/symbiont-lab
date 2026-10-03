"""Reproducible laboratory fixtures; no world truth crosses into the organism.

The collision engine owns instantiated geometry. Recipes only build it and are
persisted alongside physical state, never in a genome or cognitive checkpoint.
"""

from __future__ import annotations

import math
from copy import deepcopy

from environment.rng import derive_world_rng

ENVIRONMENT_NAMES = (
    "flat-v1",
    "contact-garden-v1",
    "vision-nursery-v1",
    "vision-nursery-d1-v1",
    "vision-nursery-d1-v2",
)

# Protected nursery metabolic support (Visual Acquisition v1 D1-v2). A
# property of the protected environment, not a resource to find: a fixed,
# deterministic, action-independent energy input through the body's ordinary
# intake path, bounded below the full reserve. Sized from EW-D0: basal drain
# ~0.80 energy/tick in vision-nursery-d1-v1; 0.6/tick (75%) keeps real cost
# and homeostatic variation while preventing basal metabolism from ending the
# Experience before its horizon. AcquisitionSafetyPolicy remains the final
# barrier.
_METABOLIC_SUPPORT = {
    "vision-nursery-d1-v2": {
        "kind": "bounded_maintenance",
        "rate_per_tick": 0.6,
        "ceiling_fraction": 0.9,
    },
}

# Versioned immutable recipes: positions in metres, Z up; box sizes are full extents.
_RECIPES = {
    "flat-v1": [],
    "contact-garden-v1": [
        {
            "id": "low-surface",
            "position": [1.8, -1.6, 0.03],
            "size": [1.2, 1.0, 0.06],
            "friction": 0.95,
        },
        {
            "id": "smooth-surface",
            "position": [-1.8, -1.6, 0.03],
            "size": [1.2, 1.0, 0.06],
            "friction": 0.12,
        },
        {"id": "block", "position": [1.8, 1.0, 0.25], "size": [0.5, 0.7, 0.5], "friction": 0.65},
        {"id": "barrier", "position": [-2.0, 1.0, 0.2], "size": [0.25, 1.5, 0.4], "friction": 0.65},
    ],
    # ADR-0011: luminance contrast for the visual apparatus. Luminance is a
    # physical surface property of the fixture, never an organism signal.
    "vision-nursery-v1": [
        {
            "id": "bright-panel",
            "position": [1.6, 0.0, 1.0],
            "size": [0.1, 2.4, 2.0],
            "friction": 0.65,
            "luminance": 0.95,
        },
        {
            "id": "dark-stripe",
            "position": [1.53, 0.35, 1.0],
            "size": [0.04, 0.4, 2.0],
            "friction": 0.65,
            "luminance": 0.05,
        },
        {
            "id": "dark-panel",
            "position": [-1.6, 0.0, 0.6],
            "size": [0.1, 1.6, 1.2],
            "friction": 0.65,
            "luminance": 0.08,
        },
        {
            "id": "mid-block",
            "position": [0.0, 1.5, 0.25],
            "size": [0.6, 0.3, 0.5],
            "friction": 0.65,
            "luminance": 0.5,
        },
    ],
    # Visual Acquisition v1 D1: uniform background plus one coherent luminance
    # source that sweeps laterally in front of the eye. The source is
    # kinematic and has no collision shape: it changes only what the visual
    # apparatus transduces. Phase and period derive from the run seed through
    # a world RNG namespace (never the organism's RNG); the pose is then a
    # pure function of (causal tick, derived parameters), so resume and
    # replay are exact.
    "vision-nursery-d1-v1": [
        {
            "id": "background",
            "position": [2.2, 0.0, 1.2],
            "size": [0.1, 6.0, 2.4],
            "friction": 0.65,
            "luminance": 0.45,
        },
        {
            "id": "source",
            "position": [1.4, 0.0, 1.0],
            "size": [0.05, 0.35, 0.35],
            "friction": 0.65,
            "luminance": 0.95,
            "motion": {
                "axis": [0.0, 1.0, 0.0],
                "amplitude": 0.8,
                "period_ticks_range": [72, 120],
                "namespace": "vision.d1.source-motion.v1",
            },
        },
    ],
    # Visual Acquisition v1 D1-v2: identical stimulus to d1-v1; only the
    # nursery's metabolic support differs (see _METABOLIC_SUPPORT).
    "vision-nursery-d1-v2": [
        {
            "id": "background",
            "position": [2.2, 0.0, 1.2],
            "size": [0.1, 6.0, 2.4],
            "friction": 0.65,
            "luminance": 0.45,
        },
        {
            "id": "source",
            "position": [1.4, 0.0, 1.0],
            "size": [0.05, 0.35, 0.35],
            "friction": 0.65,
            "luminance": 0.95,
            "motion": {
                "axis": [0.0, 1.0, 0.0],
                "amplitude": 0.8,
                "period_ticks_range": [72, 120],
                "namespace": "vision.d1.source-motion.v1",
            },
        },
    ],
}


def environment_recipe(name: str = "flat-v1") -> dict:
    if not isinstance(name, str) or name not in _RECIPES:
        raise ValueError(f"unknown Physics3D environment: {name}")
    recipe = {"schema_version": 1, "name": name, "fixtures": deepcopy(_RECIPES[name])}
    if name in _METABOLIC_SUPPORT:
        recipe["metabolic_support"] = deepcopy(_METABOLIC_SUPPORT[name])
    return recipe


def nursery_support_amount(recipe: dict, *, energy_reserve: float, max_energy: float) -> float:
    """Energy the protected nursery supplies this tick (0 outside such nurseries)."""
    support = recipe.get("metabolic_support")
    if not support:
        return 0.0
    room = support["ceiling_fraction"] * max_energy - energy_reserve
    return max(0.0, min(float(support["rate_per_tick"]), room))


def resolve_environment(name: str | None, saved: dict | None) -> dict:
    """Resume the exact recipe; never silently replace the world on resume."""
    if saved is None:
        return environment_recipe(name or "flat-v1")
    if not isinstance(saved, dict):
        raise ValueError("saved environment must be an object")
    expected = environment_recipe(saved.get("name"))
    if saved != expected:
        raise ValueError("saved Physics3D environment recipe is unsupported or altered")
    if name is not None and name != saved["name"]:
        raise ValueError("environment change requires a fresh body, not a pose resume")
    return deepcopy(saved)


def motion_parameters(motion: dict, seed: int) -> tuple[float, int]:
    """(phase fraction, period in ticks) derived once from the run seed."""
    rng = derive_world_rng(seed, motion["namespace"])
    low, high = motion["period_ticks_range"]
    return rng.random(), rng.randint(int(low), int(high))


def fixture_position(fixture: dict, tick: int, seed: int) -> list[float]:
    """Deterministic fixture position at a causal tick (static unless ``motion``)."""
    motion = fixture.get("motion")
    if not motion:
        return list(fixture["position"])
    phase, period = motion_parameters(motion, seed)
    offset = motion["amplitude"] * math.sin(2.0 * math.pi * (tick / period + phase))
    return [base + axis * offset for base, axis in zip(fixture["position"], motion["axis"])]


def update_environment(
    p, client_id: int, recipe: dict, bodies: tuple[int, ...], tick: int, seed: int
) -> None:
    """Move kinematic fixtures to their pose for ``tick``; static ones are untouched."""
    for fixture, body in zip(recipe["fixtures"], bodies):
        if fixture.get("motion"):
            p.resetBasePositionAndOrientation(
                body,
                fixture_position(fixture, tick, seed),
                (0, 0, 0, 1),
                physicsClientId=client_id,
            )


def build_environment(p, client_id: int, recipe: dict) -> tuple[int, ...]:
    """Instantiate static colliders, kinematic visual sources and their visuals."""
    bodies = []
    for fixture in recipe["fixtures"]:
        half = [v / 2 for v in fixture["size"]]
        shape = (
            -1  # kinematic sources are visual only; they never collide
            if fixture.get("motion")
            else p.createCollisionShape(p.GEOM_BOX, halfExtents=half, physicsClientId=client_id)
        )
        luminance = fixture.get("luminance")
        rgba = (0.35, 0.45, 0.5, 1) if luminance is None else (luminance, luminance, luminance, 1)
        visual = p.createVisualShape(
            p.GEOM_BOX, halfExtents=half, rgbaColor=rgba, physicsClientId=client_id
        )
        body = p.createMultiBody(
            baseMass=0,
            baseCollisionShapeIndex=shape,
            baseVisualShapeIndex=visual,
            basePosition=fixture["position"],
            physicsClientId=client_id,
        )
        if shape != -1:
            p.changeDynamics(
                body,
                -1,
                lateralFriction=fixture["friction"],
                restitution=0,
                physicsClientId=client_id,
            )
        bodies.append(body)
    return tuple(bodies)
