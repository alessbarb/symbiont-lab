from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from .contracts import HostManifest
from .providers.stdlib_readings import StandardLibraryReadingProvider
from .readings import CapabilitySamplingOutcome, HostSampler, SensorReading


@dataclass(slots=True, frozen=True)
class SecondLookResult:
    """The outcome of a temporary higher-resolution sampling session."""

    capability_id: str
    readings: tuple[SensorReading, ...]
    cancelled: bool
    outcomes: tuple[CapabilitySamplingOutcome, ...] = ()


class SecondLookSession:
    """A temporary, bounded, cancellable burst for one authorized capability."""

    def __init__(
        self,
        *,
        manifest: HostManifest,
        capability_id: str,
        max_ticks: int = 5,
        sampler: HostSampler | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        if max_ticks < 1:
            raise ValueError("max_ticks must be at least 1")
        if not manifest.supports(capability_id):
            raise ValueError(f"capability {capability_id!r} is not available in this host's manifest")
        self._manifest = manifest
        self._capability_id = capability_id
        self._max_ticks = max_ticks
        self._sampler = sampler if sampler is not None else HostSampler(providers=(StandardLibraryReadingProvider(),))
        self._clock = clock
        self._ticks_run = 0
        self._cancelled = False
        self._readings: list[SensorReading] = []
        self._outcomes: list[CapabilitySamplingOutcome] = []

    @property
    def capability_id(self) -> str:
        return self._capability_id

    @property
    def is_active(self) -> bool:
        return not self._cancelled and self._ticks_run < self._max_ticks

    @property
    def readings(self) -> tuple[SensorReading, ...]:
        return tuple(self._readings)

    def cancel(self) -> None:
        self._cancelled = True

    def tick(self) -> SensorReading | None:
        if not self.is_active:
            return None
        readings, _, outcomes = self._sampler.sample_with_outcomes(
            self._manifest,
            capability_ids=(self._capability_id,),
            clock=self._clock,
        )
        self._ticks_run += 1
        self._outcomes.extend(outcomes)
        match = next((reading for reading in readings if reading.capability_id == self._capability_id), None)
        if match is not None:
            self._readings.append(match)
        return match

    def run_to_completion(self) -> SecondLookResult:
        while self.is_active:
            self.tick()
        return SecondLookResult(
            capability_id=self._capability_id,
            readings=self.readings,
            cancelled=self._cancelled,
            outcomes=tuple(self._outcomes),
        )
