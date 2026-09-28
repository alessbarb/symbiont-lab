"""Reproducible laboratory fixtures; no world truth crosses into the organism.

The collision engine owns instantiated geometry. Recipes only build it and are
persisted alongside physical state, never in a genome or cognitive checkpoint.
"""

from __future__ import annotations

from copy import deepcopy

ENVIRONMENT_NAMES = ("flat-v1", "contact-garden-v1")

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


def build_environment(p, client_id: int, recipe: dict) -> tuple[int, ...]:
    """Instantiate real static colliders and native Physics3D visuals."""
    bodies = []
    for fixture in recipe["fixtures"]:
        half = [v / 2 for v in fixture["size"]]
        shape = p.createCollisionShape(p.GEOM_BOX, halfExtents=half, physicsClientId=client_id)
        visual = p.createVisualShape(
            p.GEOM_BOX, halfExtents=half, rgbaColor=(0.35, 0.45, 0.5, 1), physicsClientId=client_id
        )
        body = p.createMultiBody(
            baseMass=0,
            baseCollisionShapeIndex=shape,
            baseVisualShapeIndex=visual,
            basePosition=fixture["position"],
            physicsClientId=client_id,
        )
        p.changeDynamics(
            body, -1, lateralFriction=fixture["friction"], restitution=0, physicsClientId=client_id
        )
        bodies.append(body)
    return tuple(bodies)
