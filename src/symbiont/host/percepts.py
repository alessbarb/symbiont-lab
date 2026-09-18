from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit


@dataclass(slots=True, frozen=True)
class Percept:
    """A platform-neutral organism perception, synthesized from a real
    sensor reading (roadmap v0.34).

    Percepts intentionally drop ``capability_id``/``source`` — cognition
    should never need to know which provider or discovery-internal name
    produced a signal to reason about it (Milestone B exit gate: "cognition
    imports no platform provider"). ``name`` is a stable semantic label
    chosen by the synthesis mapping, independent of any platform's specific
    capability naming, so a future second provider can synthesize the same
    percept name from a differently-named capability without cognition ever
    noticing.
    """

    name: str
    value: float | None
    unit: Unit
    quality: ReadingQuality
    privacy_class: ReadingPrivacyClass
    # Organism-owned sensory metadata. Legacy callers may omit it; the
    # historical name/value/unit/quality contract remains unchanged.
    sensor_id: str | None = None
    modality_id: str | None = None
    source_ids: tuple[str, ...] = ()
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name or any(char.isspace() for char in self.name):
            raise ValueError("name must be a non-empty token")
        if self.sensor_id is not None and (not isinstance(self.sensor_id, str) or not self.sensor_id or any(char.isspace() for char in self.sensor_id)):
            raise ValueError("sensor_id must be a non-empty token when present")
        if self.modality_id is not None and (not isinstance(self.modality_id, str) or not self.modality_id or any(char.isspace() for char in self.modality_id)):
            raise ValueError("modality_id must be a non-empty token when present")
        if any(not isinstance(item, str) or not item for item in self.source_ids):
            raise ValueError("source_ids must contain non-empty strings")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("source_ids must be unique")
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
