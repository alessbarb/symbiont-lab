"""What a host channel yields: the surfaces it offers and the samples it takes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

MetadataValue = str | int | float | bool | None


class CapabilityKind(StrEnum):
    RUNTIME = "runtime"
    COMPUTE = "compute"
    STORAGE = "storage"
    CLOCK = "clock"
    SIGNAL = "signal"


class Unit(StrEnum):
    PERCENT = "percent"
    BYTE = "byte"
    COUNT = "count"
    RATIO = "ratio"
    SECOND = "second"


class ReadingQuality(StrEnum):
    NOMINAL = "nominal"
    UNAVAILABLE = "unavailable"


class ReadingPrivacyClass(StrEnum):
    AGGREGATE = "aggregate"


@dataclass(slots=True, frozen=True)
class Capability:
    """One surface a host channel offers, without host identity."""

    capability_id: str
    kind: CapabilityKind
    source: str
    available: bool = True
    detail: tuple[tuple[str, MetadataValue], ...] = ()


@dataclass(slots=True, frozen=True)
class SensorReading:
    """One sample of one surface."""

    capability_id: str
    source: str
    value: float | None
    unit: Unit
    monotonic_timestamp_ns: int
    quality: ReadingQuality
    privacy_class: ReadingPrivacyClass
