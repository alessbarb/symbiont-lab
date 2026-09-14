from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, Iterable, Protocol

from .contracts import Capability, HostManifest


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
    """One typed sample from a host capability."""

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
    return any(
        capability.capability_id == reading.capability_id
        and capability.source == reading.source
        for capability in manifest.available
    )


@dataclass(slots=True, frozen=True)
class ReadingFailure:
    provider_id: str
    reason: str


class SamplingOutcomeKind(StrEnum):
    SUCCEEDED = "succeeded"
    UNAVAILABLE = "unavailable"
    MISSING = "missing"
    PROVIDER_FAILED = "provider_failed"


@dataclass(slots=True, frozen=True)
class CapabilitySamplingOutcome:
    """One capability's fate in one provider's sampling call, for self-model
    cost/health attribution (roadmap v0.53). ``attributed_elapsed_s`` divides
    that call's wall-clock time evenly across every capability it was asked
    to sample, not just the ones it returned — an omitted or failed
    capability must not appear free."""

    capability_id: str
    provider_id: str
    kind: SamplingOutcomeKind
    attributed_elapsed_s: float
    quality: ReadingQuality | None = None

    def __post_init__(self) -> None:
        if self.attributed_elapsed_s < 0.0:
            raise ValueError("attributed_elapsed_s must be non-negative")


class ReadingProvider(Protocol):
    """Platform-specific sampling probes implement this; cognition never does."""

    @property
    def provider_id(self) -> str: ...

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]: ...


class HostSampler:
    """Sample typed readings scoped to accepted and optionally selected senses.

    ``capability_ids`` is a hard sampling boundary, not a post-read filter: only
    selected capabilities are handed to providers. Providers still receive the same
    normalized capability tuple shape as before; the sampler does not assume a
    one-provider/one-source topology.
    """

    def __init__(self, providers: Iterable[ReadingProvider]) -> None:
        self._providers = tuple(providers)
        provider_ids = [provider.provider_id for provider in self._providers]
        if len(provider_ids) != len(set(provider_ids)):
            raise ValueError("provider_id values must be unique")

    def sample(
        self,
        manifest: HostManifest,
        *,
        capability_ids: Iterable[str] | None = None,
    ) -> tuple[tuple[SensorReading, ...], tuple[ReadingFailure, ...]]:
        readings, failures, _ = self._sample_internal(
            manifest, capability_ids=capability_ids, clock=time.perf_counter
        )
        return readings, failures

    def sample_with_outcomes(
        self,
        manifest: HostManifest,
        *,
        capability_ids: Iterable[str] | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> tuple[tuple[SensorReading, ...], tuple[ReadingFailure, ...], tuple[CapabilitySamplingOutcome, ...]]:
        """Like :meth:`sample`, but also reports what happened to every
        attempted capability and how much wall-clock time it cost (roadmap
        v0.53's self-model). ``clock`` is injectable for deterministic
        tests; production callers use the default ``time.perf_counter``."""
        return self._sample_internal(manifest, capability_ids=capability_ids, clock=clock)

    def _sample_internal(
        self,
        manifest: HostManifest,
        *,
        capability_ids: Iterable[str] | None,
        clock: Callable[[], float],
    ) -> tuple[tuple[SensorReading, ...], tuple[ReadingFailure, ...], tuple[CapabilitySamplingOutcome, ...]]:
        readings: list[SensorReading] = []
        failures: list[ReadingFailure] = []
        outcomes: list[CapabilitySamplingOutcome] = []
        selected = None if capability_ids is None else frozenset(capability_ids)
        available = tuple(
            capability
            for capability in manifest.available
            if selected is None or capability.capability_id in selected
        )
        attempted_ids = tuple(capability.capability_id for capability in available)

        for provider in sorted(self._providers, key=lambda item: item.provider_id):
            if not available:
                continue
            start = clock()
            try:
                sampled = provider.sample(available)
            except Exception as exc:  # Providers are an isolation boundary.
                elapsed = clock() - start
                failures.append(
                    ReadingFailure(
                        provider_id=provider.provider_id,
                        reason=f"{type(exc).__name__}: provider failed",
                    )
                )
                share = elapsed / len(attempted_ids) if attempted_ids else 0.0
                outcomes.extend(
                    CapabilitySamplingOutcome(
                        capability_id=capability_id,
                        provider_id=provider.provider_id,
                        kind=SamplingOutcomeKind.PROVIDER_FAILED,
                        attributed_elapsed_s=share,
                    )
                    for capability_id in attempted_ids
                )
                continue
            elapsed = clock() - start
            share = elapsed / len(attempted_ids) if attempted_ids else 0.0

            by_capability: dict[str, SensorReading] = {}
            for reading in sampled:
                if selected is not None and reading.capability_id not in selected:
                    failures.append(
                        ReadingFailure(
                            provider_id=provider.provider_id,
                            reason=f"rejected unrequested reading {reading.capability_id}",
                        )
                    )
                    continue
                if not reading_matches_manifest(reading, manifest):
                    failures.append(
                        ReadingFailure(
                            provider_id=provider.provider_id,
                            reason=f"rejected unmatched reading {reading.capability_id}",
                        )
                    )
                    continue
                readings.append(reading)
                by_capability[reading.capability_id] = reading

            for capability_id in attempted_ids:
                reading = by_capability.get(capability_id)
                if reading is None:
                    kind = SamplingOutcomeKind.MISSING
                    quality = None
                elif reading.quality is ReadingQuality.UNAVAILABLE:
                    kind = SamplingOutcomeKind.UNAVAILABLE
                    quality = reading.quality
                else:
                    kind = SamplingOutcomeKind.SUCCEEDED
                    quality = reading.quality
                outcomes.append(
                    CapabilitySamplingOutcome(
                        capability_id=capability_id,
                        provider_id=provider.provider_id,
                        kind=kind,
                        attributed_elapsed_s=share,
                        quality=quality,
                    )
                )

        return tuple(readings), tuple(failures), tuple(outcomes)
