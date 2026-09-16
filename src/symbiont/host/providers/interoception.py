from __future__ import annotations

import resource
import time

from ..contracts import Capability, CapabilityKind
from ..readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit


class InteroceptionProvider:
    """Provides bounded, aggregate read-only interoceptive sensory surfaces.

    Reflects the organism's own internal physiological and computational state:
    - internal.tick_latency: execution time of the previous processing cycle
    - internal.memory_rss: resident memory footprint of the organism process
    - internal.epistemic_surprise: prediction error / bayesian surprise
    - internal.metabolic_reserve: fraction of physiological energy reserve remaining
    """

    provider_id = "interoception"

    def __init__(self) -> None:
        self._tick_latency: float = 0.0
        self._epistemic_surprise: float = 0.0
        self._metabolic_reserve: float = 1.0

    def update_metrics(
        self,
        *,
        tick_latency: float,
        epistemic_surprise: float,
        metabolic_reserve: float,
    ) -> None:
        self._tick_latency = max(0.0, float(tick_latency))
        self._epistemic_surprise = max(0.0, min(1.0, float(epistemic_surprise)))
        self._metabolic_reserve = max(0.0, min(1.0, float(metabolic_reserve)))

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
            Capability(
                capability_id="internal.epistemic_surprise",
                kind=CapabilityKind.SIGNAL,
                source=self.provider_id,
                detail=(("unit", "ratio"),),
            ),
            Capability(
                capability_id="internal.metabolic_reserve",
                kind=CapabilityKind.SIGNAL,
                source=self.provider_id,
                detail=(("unit", "ratio"),),
            ),
        )

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]:
        now_ns = time.monotonic_ns()
        available_ids = {cap.capability_id for cap in capabilities if cap.source == self.provider_id}
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
                rss_bytes = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
            except (OSError, ValueError):
                rss_bytes = None
            readings.append(
                SensorReading(
                    capability_id="internal.memory_rss",
                    source=self.provider_id,
                    value=rss_bytes,
                    unit=Unit.BYTE,
                    monotonic_timestamp_ns=now_ns,
                    quality=ReadingQuality.NOMINAL if rss_bytes is not None else ReadingQuality.UNAVAILABLE,
                    privacy_class=ReadingPrivacyClass.AGGREGATE,
                )
            )

        if "internal.epistemic_surprise" in available_ids:
            readings.append(
                SensorReading(
                    capability_id="internal.epistemic_surprise",
                    source=self.provider_id,
                    value=self._epistemic_surprise,
                    unit=Unit.RATIO,
                    monotonic_timestamp_ns=now_ns,
                    quality=ReadingQuality.NOMINAL,
                    privacy_class=ReadingPrivacyClass.AGGREGATE,
                )
            )

        if "internal.metabolic_reserve" in available_ids:
            readings.append(
                SensorReading(
                    capability_id="internal.metabolic_reserve",
                    source=self.provider_id,
                    value=self._metabolic_reserve,
                    unit=Unit.RATIO,
                    monotonic_timestamp_ns=now_ns,
                    quality=ReadingQuality.NOMINAL,
                    privacy_class=ReadingPrivacyClass.AGGREGATE,
                )
            )

        return tuple(readings)
