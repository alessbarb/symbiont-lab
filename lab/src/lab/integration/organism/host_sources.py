"""Host channels from ``modality.host``, presented to the organism in its own types."""

from __future__ import annotations

from typing import Any

from symbiont.host.contracts import Capability, CapabilityKind
from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit


class HostSource:
    """One host channel as an organism discovery and reading provider.

    Records are converted field for field; the organism's types validate them.
    """

    def __init__(self, source: Any) -> None:
        self.source = source
        self.provider_id: str = source.provider_id

    def discover(self) -> tuple[Capability, ...]:
        return tuple(
            Capability(
                capability_id=surface.capability_id,
                kind=CapabilityKind(surface.kind),
                source=surface.source,
                available=surface.available,
                detail=surface.detail,
            )
            for surface in self.source.discover()
        )

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]:
        return tuple(
            SensorReading(
                capability_id=reading.capability_id,
                source=reading.source,
                value=reading.value,
                unit=Unit(reading.unit),
                monotonic_timestamp_ns=reading.monotonic_timestamp_ns,
                quality=ReadingQuality(reading.quality),
                privacy_class=ReadingPrivacyClass(reading.privacy_class),
            )
            for reading in self.source.sample(capabilities)
        )

    def observe_tick(self, latency: float) -> None:
        self.source.observe_tick(latency)
