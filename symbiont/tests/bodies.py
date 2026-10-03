"""Deterministic test Body: the canonical organism with fixed, opaque senses.

Tests use the canonical profile (ADR-0062). What they vary is the Body: this one
supplies a small set of synthetic signals whose readings depend only on the
sample count, so a test never reads the real machine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from symbiont.host.contracts import Capability, CapabilityKind
from symbiont.host.discovery import HostDiscovery
from symbiont.host.lifecycle import HostLifecycle
from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit

SIGNALS = ("signal.a", "signal.b", "signal.c")


class TestBodyDiscovery:
    __test__ = False

    provider_id = "test-body"

    def discover(self) -> tuple[Capability, ...]:
        return tuple(
            Capability(signal, CapabilityKind.SIGNAL, self.provider_id) for signal in SIGNALS
        )


@dataclass
class TestBody:
    """Every reading is a function of the sample count."""

    __test__ = False
    calls: int = 0
    provider_id: str = "test-body"

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]:
        self.calls += 1
        return tuple(
            SensorReading(
                capability_id=capability.capability_id,
                source=self.provider_id,
                value=round(1.0 + math.sin(self.calls / (3.0 + index)), 6),
                unit=Unit.COUNT,
                monotonic_timestamp_ns=self.calls,
                quality=ReadingQuality.NOMINAL,
                privacy_class=ReadingPrivacyClass.AGGREGATE,
            )
            for index, capability in enumerate(capabilities)
        )


def test_body_kwargs(body: TestBody | None = None) -> dict:
    """Runtime keyword arguments that embody an organism in a ``TestBody``."""
    body = body if body is not None else TestBody()
    lifecycle = HostLifecycle(
        discovery=HostDiscovery((TestBodyDiscovery(),)), reading_providers=(body,)
    )
    return dict(host_lifecycle=lifecycle, host_reading_providers=(body,))


test_body_kwargs.__test__ = False
