"""A stand-in for host telemetry, so organism tests need no real host channel."""

from __future__ import annotations

import time

from symbiont.host.contracts import Capability, CapabilityKind
from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit

HOST_IDS = {"internal.tick_latency": Unit.SECOND, "internal.memory_rss": Unit.BYTE}


class FakeTelemetry:
    """Host telemetry with stated values, standing in for a real machine."""

    provider_id = "fake_host"

    def __init__(self, tick_latency: float | None = None, memory_rss: float | None = 2e8) -> None:
        self._tick_latency, self._fixed = 0.0, tick_latency
        self._memory_rss = memory_rss

    def observe_tick(self, latency: float) -> None:
        self._tick_latency = latency

    def discover(self) -> tuple[Capability, ...]:
        return tuple(
            Capability(
                capability_id=capability_id, kind=CapabilityKind.SIGNAL, source=self.provider_id
            )
            for capability_id in HOST_IDS
        )

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]:
        return tuple(
            SensorReading(
                capability_id=capability.capability_id,
                source=self.provider_id,
                value=self._value(capability.capability_id),
                unit=HOST_IDS[capability.capability_id],
                monotonic_timestamp_ns=time.monotonic_ns(),
                quality=(
                    ReadingQuality.UNAVAILABLE
                    if self._value(capability.capability_id) is None
                    else ReadingQuality.NOMINAL
                ),
                privacy_class=ReadingPrivacyClass.AGGREGATE,
            )
            for capability in capabilities
            if capability.capability_id in HOST_IDS
        )

    def _value(self, capability_id: str) -> float | None:
        if capability_id == "internal.memory_rss":
            return self._memory_rss
        return self._tick_latency if self._fixed is None else self._fixed


# an absurd machine: hour-long ticks, a petabyte of memory
EXTREME = {"tick_latency": 3600.0, "memory_rss": 1e15}
