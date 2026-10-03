from __future__ import annotations

import math
import time
from dataclasses import replace
from typing import Protocol

from ..host.contracts import Capability, CapabilityKind
from ..host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit


class HostTelemetry(Protocol):
    """Host measurements carried alongside interoception; supplied from outside."""

    def observe_tick(self, latency: float) -> None: ...

    def discover(self) -> tuple[Capability, ...]: ...

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]: ...


class InteroceptionProvider:
    """The organism's sense of its own physiological and cognitive state.

    - internal.epistemic_surprise: prediction error / bayesian surprise
    - internal.metabolic_reserve: fraction of physiological energy reserve remaining
    - internal.integrity: bounded structural integrity
    - internal.metabolic_pressure: coarse pressure state projected to a ratio
    - internal.repair_pressure: current integrity deficit
    - internal.waste_pressure: bounded retained-degradation pressure

    These are intrinsic: they are computed from the organism's own state and
    need no host. Measurements of the host process (``host_telemetry``) are a
    separate, optional source. They are published under this provider's
    persisted id but stay apparatus evidence and never reach organism learning.
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

    def __init__(self, host_telemetry: HostTelemetry | None = None) -> None:
        self._host_telemetry = host_telemetry
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
        if self._host_telemetry is not None:
            self._host_telemetry.observe_tick(tick_latency)
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
        host = self._host_telemetry.discover() if self._host_telemetry is not None else ()
        return (
            *(replace(capability, source=self.provider_id) for capability in host),
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
        own = tuple(cap for cap in capabilities if cap.source == self.provider_id)
        readings: list[SensorReading] = (
            [
                replace(reading, source=self.provider_id)
                for reading in self._host_telemetry.sample(own)
            ]
            if self._host_telemetry is not None
            else []
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
        """Project only admitted organism-facing internal readings.

        Host telemetry remains apparatus-only evidence and
        pass through unchanged. Only capabilities admitted by organism_facing()
        are normalized for adaptive sensing and cognition.
        """
        if reading.source != self.provider_id or not self.organism_facing(reading.capability_id):
            return reading
        if reading.value is None:
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

        if reading.capability_id in {
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
        if (
            reading.source != self.provider_id
            or not self.organism_facing(reading.capability_id)
            or reading.value is None
        ):
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
