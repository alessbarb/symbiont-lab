"""Symbiont World — spatial, causal, semantically opaque habitat kernel.

W0 scope only: package boundary, constitution, contracts, topology, state,
events, RNG and checkpoint. No fields, resources, hazards or organisms yet.
See docs/design/symbiont-world-v1.md for the normative spec.
"""
from __future__ import annotations

from .constitution import WorldConstitution
from .contracts import ContactEvidence, ReceivedEmission, WorldAction, WorldObservation
from .events import EventJournal, WorldEvent
from .checkpoint import WorldCheckpoint, restore, take_checkpoint
from .genesis import GroundTruth, WorldEnvironment
from .laws import HazardLaw, PeriodicFieldLaw, ResourceLaw
from .movement import resolve_movement
from .observation import local_observation, opaque_signal_id
from .rng import derive_world_rng
from .state import TickAborted, WorldState
from .topology import HexCoord, HexTopology, OccupancyGrid, WorldBody

__all__ = [
    "WorldConstitution",
    "ContactEvidence",
    "ReceivedEmission",
    "WorldAction",
    "WorldObservation",
    "EventJournal",
    "WorldEvent",
    "WorldCheckpoint",
    "restore",
    "take_checkpoint",
    "GroundTruth",
    "WorldEnvironment",
    "PeriodicFieldLaw",
    "ResourceLaw",
    "HazardLaw",
    "resolve_movement",
    "local_observation",
    "opaque_signal_id",
    "derive_world_rng",
    "TickAborted",
    "WorldState",
    "HexCoord",
    "HexTopology",
    "OccupancyGrid",
    "WorldBody",
]
