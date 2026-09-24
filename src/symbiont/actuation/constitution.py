"""Compatibility module for the body-owned actuator surface.

Actuation constitution is no longer genetic. New code should import
symbiont.actuation.surface directly.
"""
from .surface import (
    ActuatorChannel,
    ActuatorConstitution,
    ActuatorSurface,
    MotorSlot,
    derive_actuator_constitution,
)

__all__ = [
    "ActuatorChannel",
    "ActuatorConstitution",
    "ActuatorSurface",
    "MotorSlot",
    "derive_actuator_constitution",
]
