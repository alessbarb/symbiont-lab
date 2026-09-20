"""WorldObservation / WorldAction: the only two types that cross the
organism boundary (docs/design/symbiont-world-v1.md §4).

Both are immutable by construction, not just by convention: mapping fields
are coerced into MappingProxyType so a caller cannot mutate them after
construction, and no field carries cell_id, absolute coordinates, entity
types or any other ground-truth semantics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ContactEvidence:
    """Evidence of a nearby source. Intensity only — never a typed
    identity such as `entity.type = symbiont`."""

    source_id: str
    intensity: float


@dataclass(frozen=True, slots=True)
class ReceivedEmission:
    sequence: tuple[int, ...]
    intensity: float


@dataclass(frozen=True, slots=True)
class WorldObservation:
    signals: Mapping[str, float] = field(default_factory=dict)
    contact: tuple[ContactEvidence, ...] = ()
    reception: tuple[ReceivedEmission, ...] = ()
    internal: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "signals", MappingProxyType(dict(self.signals)))
        object.__setattr__(self, "internal", MappingProxyType(dict(self.internal)))
        object.__setattr__(self, "contact", tuple(self.contact))
        object.__setattr__(self, "reception", tuple(self.reception))


@dataclass(frozen=True, slots=True)
class WorldAction:
    move: str | None = None
    sample: str | None = None
    acquire: str | None = None
    interact: str | None = None
    emit: tuple[int, ...] | None = None
    rest: bool = False

    def __post_init__(self) -> None:
        if self.emit is not None:
            object.__setattr__(self, "emit", tuple(self.emit))
