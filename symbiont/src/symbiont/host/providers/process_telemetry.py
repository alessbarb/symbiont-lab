from __future__ import annotations

import time

try:
    import resource
except ImportError:  # Windows has no stdlib resource module.
    resource = None

from ..contracts import Capability, CapabilityKind
from ..readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit


class HostProcessTelemetry:
    """Measurements of the host process that runs the organism.

    - internal.tick_latency: execution time of the previous processing cycle
    - internal.memory_rss: resident memory footprint of the process

    These describe the machine, not the organism: they are apparatus evidence
    and never reach organism learning. The capability ids keep their persisted
    ``internal.`` prefix.
    """

    provider_id = "host_process"

    def __init__(self) -> None:
        self._tick_latency: float = 0.0

    def observe_tick(self, latency: float) -> None:
        self._tick_latency = max(0.0, float(latency))

    def discover(self) -> tuple[Capability, ...]:
        return (
            Capability(
                capability_id="internal.tick_latency",
                kind=CapabilityKind.SIGNAL,
                source=self.provider_id,
                detail=(("unit", "second"),),
            ),
            Capability(
                capability_id="internal.memory_rss",
                kind=CapabilityKind.SIGNAL,
                source=self.provider_id,
                detail=(("unit", "byte"),),
            ),
        )

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]:
        now_ns = time.monotonic_ns()
        available_ids = {cap.capability_id for cap in capabilities}
        readings: list[SensorReading] = []

        if "internal.tick_latency" in available_ids:
            readings.append(
                SensorReading(
                    capability_id="internal.tick_latency",
                    source=self.provider_id,
                    value=self._tick_latency,
                    unit=Unit.SECOND,
                    monotonic_timestamp_ns=now_ns,
                    quality=ReadingQuality.NOMINAL,
                    privacy_class=ReadingPrivacyClass.AGGREGATE,
                )
            )

        if "internal.memory_rss" in available_ids:
            try:
                rss_bytes = (
                    float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
                    if resource is not None
                    else None
                )
            except (OSError, ValueError):
                rss_bytes = None
            readings.append(
                SensorReading(
                    capability_id="internal.memory_rss",
                    source=self.provider_id,
                    value=rss_bytes,
                    unit=Unit.BYTE,
                    monotonic_timestamp_ns=now_ns,
                    quality=ReadingQuality.NOMINAL
                    if rss_bytes is not None
                    else ReadingQuality.UNAVAILABLE,
                    privacy_class=ReadingPrivacyClass.AGGREGATE,
                )
            )
        return tuple(readings)
