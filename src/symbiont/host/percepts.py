from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping

from .readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit

# Equivalent to `any(char.isspace() for char in s)` (verified identical over
# the whole BMP) but runs as one C-level scan instead of a Python-level
# per-character loop — this class of ID is checked on every Percept/
# SensorReading construction, several times per tick.
_HAS_WHITESPACE = re.compile(r"\s").search


@dataclass(slots=True, frozen=True)
class Percept:
    """A bounded percept emitted toward cognition.

    Legacy callers may still construct a Percept directly from a host reading,
    preserving the historical v0.34 contract. In adaptive sensory mode the
    percept is emitted by an organism-owned SensorState: ``name`` is the
    stable receptor identity. Source/provider lineage remains outside the
    percept itself and is projected outward from SensorState only. Human host aliases are not required
    by cognition.
    """

    name: str
    value: float | None
    unit: Unit
    quality: ReadingQuality
    privacy_class: ReadingPrivacyClass
    # NOTE(legacy): Organism-owned sensory metadata. Legacy callers may omit it; the
    # historical name/value/unit/quality contract remains unchanged.
    sensor_id: str | None = None
    modality_id: str | None = None
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name or _HAS_WHITESPACE(self.name):
            raise ValueError("name must be a non-empty token")
        if self.sensor_id is not None and (not isinstance(self.sensor_id, str) or not self.sensor_id or _HAS_WHITESPACE(self.sensor_id)):
            raise ValueError("sensor_id must be a non-empty token when present")
        if self.modality_id is not None and (not isinstance(self.modality_id, str) or not self.modality_id or _HAS_WHITESPACE(self.modality_id)):
            raise ValueError("modality_id must be a non-empty token when present")
        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)) or not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be numeric within [0, 1]")

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit.value,
            "quality": self.quality.value,
            "privacy_class": self.privacy_class.value,
        }


#: Default capability_id -> percept name mapping for the built-in providers.
#: This is the semantic layer above capability_id: differently-named
#: capabilities on a future second platform provider can synthesize into
#: the same percept name here without cognition ever having to know.
DEFAULT_PERCEPT_NAMES: Mapping[str, str] = {
    "compute.logical_cpu": "system_load",
    "storage.disk_usage": "storage_pressure",
}


def synthesize_percepts(
    readings: Iterable[SensorReading],
    *,
    percept_names: Mapping[str, str] = DEFAULT_PERCEPT_NAMES,
) -> tuple[Percept, ...]:
    """Turn readings into percepts, dropping capability_id/source identity.

    A reading whose ``capability_id`` has no entry in ``percept_names`` is
    skipped rather than guessed at — an unrecognized signal must not
    silently reach cognition under an invented name.
    """

    percepts: list[Percept] = []
    for reading in readings:
        name = percept_names.get(reading.capability_id)
        if name is None:
            continue
        percepts.append(
            Percept(
                name=name,
                value=reading.value,
                unit=reading.unit,
                quality=reading.quality,
                privacy_class=reading.privacy_class,
            )
        )
    return tuple(percepts)
