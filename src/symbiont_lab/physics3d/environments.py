"""Reproducible laboratory fixtures; no world truth crosses into the organism.

The collision engine owns instantiated geometry. Recipes only build it and are
persisted alongside physical state, never in a genome or cognitive checkpoint.
"""

from __future__ import annotations

import math
from copy import deepcopy

ENVIRONMENT_NAMES = (
    "flat-v1",
    "contact-garden-v1",
    "vision-nursery-v1",
    "vision-nursery-d1-v1",
)

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
    # Vision Acquisition v1 D1: uniform background plus one coherent luminance
    # source that sweeps laterally in front of the eye. The source is
    # kinematic and has no collision shape: it changes only what the visual
    # apparatus transduces, and its pose is a pure function of the causal
    # tick (never the clock), so resume and replay are exact.
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
            "motion": {"axis": [0.0, 1.0, 0.0], "amplitude": 0.8, "period_ticks": 96},
        },
    ],
}


def environment_recipe(name: str = "flat-v1") -> dict:
    if not isinstance(name, str) or name not in _RECIPES:
        raise ValueError(f"unknown Physics3D environment: {name}")
    return {"schema_version": 1, "name": name, "fixtures": deepcopy(_RECIPES[name])}


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


def fixture_position(fixture: dict, tick: int) -> list[float]:
    """Deterministic fixture position at a causal tick (static unless ``motion``)."""
    motion = fixture.get("motion")
    if not motion:
        return list(fixture["position"])
    offset = motion["amplitude"] * math.sin(2.0 * math.pi * tick / motion["period_ticks"])
    return [base + axis * offset for base, axis in zip(fixture["position"], motion["axis"])]


def update_environment(p, client_id: int, recipe: dict, bodies: tuple[int, ...], tick: int) -> None:
    """Move kinematic fixtures to their pose for ``tick``; static ones are untouched."""
    for fixture, body in zip(recipe["fixtures"], bodies):
        if fixture.get("motion"):
            p.resetBasePositionAndOrientation(
                body, fixture_position(fixture, tick), (0, 0, 0, 1), physicsClientId=client_id
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
