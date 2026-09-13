from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .contracts import HostManifest


class Unit(StrEnum):
    PERCENT = "percent"
    CELSIUS = "celsius"
    WATT = "watt"
    BYTE = "byte"
    HERTZ = "hertz"
    COUNT = "count"
    RATIO = "ratio"
    SECOND = "second"


class ReadingQuality(StrEnum):
    NOMINAL = "nominal"
    DEGRADED = "degraded"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


class ReadingPrivacyClass(StrEnum):
    """Every reading must fit one of these — there is no identifying option."""

    AGGREGATE = "aggregate"
    NON_IDENTIFYING = "non_identifying"


@dataclass(slots=True, frozen=True)
class SensorReading:
    """One typed sample from a host capability (roadmap v0.30).

    This is the contract cognition and future platform providers agree on;
    it does not itself read anything from a real host, and it carries no
    identity — only ``capability_id``/``source`` tokens (same shape and same
    forbidden-identity rule as :class:`~symbiont.host.contracts.Capability`).
    """

    capability_id: str
    source: str
    value: float | None
    unit: Unit
    monotonic_timestamp_ns: int
    quality: ReadingQuality
    privacy_class: ReadingPrivacyClass

    def __post_init__(self) -> None:
        if not self.capability_id or any(char.isspace() for char in self.capability_id):
            raise ValueError("capability_id must be a non-empty token")
        if not self.source:
            raise ValueError("source must not be empty")
        if self.monotonic_timestamp_ns < 0:
            raise ValueError("monotonic_timestamp_ns must be non-negative")
        if self.quality is ReadingQuality.UNAVAILABLE and self.value is not None:
            raise ValueError("an unavailable reading must not carry a value")
        if self.quality is not ReadingQuality.UNAVAILABLE and self.value is None:
            raise ValueError("a reading must carry a value unless it is unavailable")

    def as_dict(self) -> dict[str, object]:
        return {
            "capability_id": self.capability_id,
            "source": self.source,
            "value": self.value,
            "unit": self.unit.value,
            "monotonic_timestamp_ns": self.monotonic_timestamp_ns,
            "quality": self.quality.value,
            "privacy_class": self.privacy_class.value,
        }


def reading_matches_manifest(reading: SensorReading, manifest: HostManifest) -> bool:
    """A reading is only trustworthy if its capability was actually discovered.

    Ties v0.30's reading contract to v0.29's discovery manifest: a reading
    claiming a capability_id/source pair the manifest never accepted (or
    marked unavailable) must be rejected by any consumer before it reaches
    cognition.
    """
    return any(
        capability.capability_id == reading.capability_id
        and capability.source == reading.source
        for capability in manifest.available
    )
