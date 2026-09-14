from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable, Protocol

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
        readings: list[SensorReading] = []
        failures: list[ReadingFailure] = []
        selected = None if capability_ids is None else frozenset(capability_ids)
        available = tuple(
            capability
            for capability in manifest.available
            if selected is None or capability.capability_id in selected
        )

        for provider in sorted(self._providers, key=lambda item: item.provider_id):
            if not available:
                continue
            try:
                sampled = provider.sample(available)
            except Exception as exc:  # Providers are an isolation boundary.
                failures.append(
                    ReadingFailure(
                        provider_id=provider.provider_id,
                        reason=f"{type(exc).__name__}: provider failed",
                    )
                )
                continue

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

        return tuple(readings), tuple(failures)
