"""Symbiont World — spatial, causal, semantically opaque habitat kernel.

W0 scope only: package boundary, constitution, contracts, topology, state,
events, RNG and checkpoint. No fields, resources, hazards or organisms yet.
See docs/design/archive/symbiont-world-v1.md for the normative spec.
"""

from __future__ import annotations

__version__ = "0.90.0"

from environment.checkpoint import WorldCheckpoint, restore, take_checkpoint
from environment.constitution import WorldConstitution
from environment.contracts import ContactEvidence, ReceivedEmission, WorldAction, WorldObservation
from environment.events import EventJournal, WorldEvent
from environment.genesis import GroundTruth, WorldEnvironment
from environment.laws import HazardLaw, PeriodicFieldLaw, ResourceLaw
from environment.movement import resolve_movement
from environment.observation import local_observation, opaque_signal_id
from environment.rng import derive_world_rng
from environment.state import TickAborted, WorldState
from environment.topology import BodyPlacement, HexCoord, HexTopology, OccupancyGrid

__all__ = [
    "__version__",
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
    "BodyPlacement",
    "HexCoord",
    "HexTopology",
    "OccupancyGrid",
]
