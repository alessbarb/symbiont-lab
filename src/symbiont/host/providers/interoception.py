from __future__ import annotations

import math
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
    - internal.integrity: bounded structural integrity
    - internal.metabolic_pressure: coarse pressure state projected to a ratio
    - internal.repair_pressure: current integrity deficit
    - internal.waste_pressure: bounded retained-degradation pressure
    """

    provider_id = "interoception"
    # Computational host measurements remain apparatus evidence.  Only these
    # bounded physiological/cognitive channels cross into organism learning.
    ORGANISM_CAPABILITY_IDS = frozenset(
        {
            "internal.epistemic_surprise",
            "internal.metabolic_reserve",
            "internal.integrity",
            "internal.metabolic_pressure",
            "internal.repair_pressure",
            "internal.waste_pressure",
        }
    )

    @classmethod
    def organism_facing(cls, capability_id: str) -> bool:
        return capability_id in cls.ORGANISM_CAPABILITY_IDS

    def __init__(self) -> None:
        self._tick_latency: float = 0.0
        self._epistemic_surprise: float = 0.0
        self._metabolic_reserve: float = 1.0
        self._integrity: float = 1.0
        self._metabolic_pressure: float = 0.0
        self._repair_pressure: float = 0.0
        self._waste_pressure: float = 0.0

    def update_metrics(
        self,
        *,
        tick_latency: float,
        epistemic_surprise: float,
        metabolic_reserve: float,
        integrity: float = 1.0,
        metabolic_pressure: float = 0.0,
        repair_pressure: float = 0.0,
        waste_pressure: float = 0.0,
    ) -> None:
        self._tick_latency = max(0.0, float(tick_latency))
        self._epistemic_surprise = max(0.0, min(1.0, float(epistemic_surprise)))
        self._metabolic_reserve = max(0.0, min(1.0, float(metabolic_reserve)))
        self._integrity = max(0.0, min(1.0, float(integrity)))
        self._metabolic_pressure = max(0.0, min(1.0, float(metabolic_pressure)))
        self._repair_pressure = max(0.0, min(1.0, float(repair_pressure)))
        self._waste_pressure = max(0.0, min(1.0, float(waste_pressure)))

    def update_physiological_state(
        self,
        *,
        metabolic_reserve: float,
        integrity: float,
        metabolic_pressure: float,
        repair_pressure: float,
        waste_pressure: float,
    ) -> None:
        """Refresh state that must be fresh at the next decision boundary.

        Computational measurements remain one-cycle observations, while body
        state is updated immediately before sampling.  This prevents damage or
        depletion introduced between ticks from becoming an avoidable stale
        interoceptive percept.
        """
        self._metabolic_reserve = max(0.0, min(1.0, float(metabolic_reserve)))
        self._integrity = max(0.0, min(1.0, float(integrity)))
        self._metabolic_pressure = max(0.0, min(1.0, float(metabolic_pressure)))
        self._repair_pressure = max(0.0, min(1.0, float(repair_pressure)))
        self._waste_pressure = max(0.0, min(1.0, float(waste_pressure)))

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
            Capability(
                capability_id="internal.integrity",
                kind=CapabilityKind.SIGNAL,
                source=self.provider_id,
                detail=(("unit", "ratio"),),
            ),
            Capability(
                capability_id="internal.metabolic_pressure",
                kind=CapabilityKind.SIGNAL,
                source=self.provider_id,
                detail=(("unit", "ratio"),),
            ),
            Capability(
                capability_id="internal.repair_pressure",
                kind=CapabilityKind.SIGNAL,
                source=self.provider_id,
                detail=(("unit", "ratio"),),
            ),
            Capability(
                capability_id="internal.waste_pressure",
                kind=CapabilityKind.SIGNAL,
                source=self.provider_id,
                detail=(("unit", "ratio"),),
            ),
        )

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]:
        now_ns = time.monotonic_ns()
        available_ids = {
            cap.capability_id for cap in capabilities if cap.source == self.provider_id
        }
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
                    quality=ReadingQuality.NOMINAL
                    if rss_bytes is not None
                    else ReadingQuality.UNAVAILABLE,
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

        for capability_id, value in (
            ("internal.integrity", self._integrity),
            ("internal.metabolic_pressure", self._metabolic_pressure),
            ("internal.repair_pressure", self._repair_pressure),
            ("internal.waste_pressure", self._waste_pressure),
        ):
            if capability_id in available_ids:
                readings.append(
                    SensorReading(
                        capability_id=capability_id,
                        source=self.provider_id,
                        value=value,
                        unit=Unit.RATIO,
                        monotonic_timestamp_ns=now_ns,
                        quality=ReadingQuality.NOMINAL,
                        privacy_class=ReadingPrivacyClass.AGGREGATE,
                    )
                )

        return tuple(readings)

    def normalize_for_organism(self, reading: SensorReading) -> SensorReading:
        """Project a raw internal reading into a bounded organism signal.

        The raw reading remains available to the apparatus through the lifecycle
        snapshot.  Organism-facing learning must not consume platform units or
        unbounded process measurements, so this boundary converts the two
        administrative measurements into finite ratios before they enter
        adaptive sensing and cognition.
        """
        if reading.source != self.provider_id or reading.value is None:
            return reading
        if not math.isfinite(reading.value):
            return SensorReading(
                capability_id=reading.capability_id,
                source=reading.source,
                value=None,
                unit=Unit.RATIO,
                monotonic_timestamp_ns=reading.monotonic_timestamp_ns,
                quality=ReadingQuality.UNAVAILABLE,
                privacy_class=reading.privacy_class,
            )

        if reading.capability_id == "internal.tick_latency":
            value = min(1.0, max(0.0, reading.value / 1.0))
        elif reading.capability_id == "internal.memory_rss":
            # Log compression keeps large-but-bounded host variation from
            # dominating the same signal space as reserve and surprise.
            value = math.log1p(max(0.0, reading.value)) / math.log1p(512 * 1024 * 1024)
            value = min(1.0, max(0.0, value))
        elif reading.capability_id in {
            "internal.epistemic_surprise",
            "internal.metabolic_reserve",
            "internal.integrity",
            "internal.metabolic_pressure",
            "internal.repair_pressure",
            "internal.waste_pressure",
        }:
            value = min(1.0, max(0.0, reading.value))
        else:
            return reading

        return SensorReading(
            capability_id=reading.capability_id,
            source=reading.source,
            value=value,
            unit=Unit.RATIO,
            monotonic_timestamp_ns=reading.monotonic_timestamp_ns,
            quality=reading.quality,
            privacy_class=reading.privacy_class,
        )

    def local_action_pressure(self) -> float:
        """Return bounded internal modulation for local action selection.

        The aggregate includes the channels that can change the body's local
        action frontier.  In particular, integrity and repair pressure must
        reach the endogenous learner; otherwise environmental damage is
        recorded by the provider but cannot condition repair behaviour.
        """
        return max(
            0.0,
            min(
                1.0,
                0.25 * (1.0 - self._metabolic_reserve)
                + 0.20 * self._epistemic_surprise
                + 0.25 * self._repair_pressure
                + 0.20 * self._metabolic_pressure
                + 0.10 * self._waste_pressure,
            ),
        )


class ShamInteroceptionProvider(InteroceptionProvider):
    """Keep interoceptive topology and cost while withholding its values.

    The apparatus still records the real bounded readings, but the organism
    receives a neutral projection.  This is a control for sensory topology and
    processing workload; it must not be interpreted as an organism-facing
    signal or as a second policy path.
    """

    def normalize_for_organism(self, reading: SensorReading) -> SensorReading:
        if reading.source != self.provider_id or reading.value is None:
            return reading
        return SensorReading(
            capability_id=reading.capability_id,
            source=reading.source,
            value=0.5,
            unit=Unit.RATIO,
            monotonic_timestamp_ns=reading.monotonic_timestamp_ns,
            quality=ReadingQuality.NOMINAL,
            privacy_class=reading.privacy_class,
        )

    def local_action_pressure(self) -> float:
        # Preserve the call and its bounded computational path without
        # exposing actual reserve or surprise to action selection.
        return 0.5
