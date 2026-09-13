from __future__ import annotations

from dataclasses import dataclass

from .contracts import HostManifest
from .providers.stdlib_readings import StandardLibraryReadingProvider
from .readings import HostSampler, SensorReading


@dataclass(slots=True, frozen=True)
class SecondLookResult:
    """The outcome of a temporary higher-resolution sampling session."""

    capability_id: str
    readings: tuple[SensorReading, ...]
    cancelled: bool


class SecondLookSession:
    """A temporary, bounded, cancellable burst of higher-resolution sampling
    for one already-discovered capability (roadmap v0.39).

    Three properties by construction, not by caller discipline:

    - **Authorized** — the constructor rejects any ``capability_id`` the
      given manifest does not already report as available; a second look
      can only look more closely at something discovery already offered,
      never request a new kind of measurement.
    - **Read-only** — every tick delegates to :class:`HostSampler`, which
      never writes anything; there is no code path here that could.
    - **Temporary and cancellable** — bounded by ``max_ticks``, and
      :meth:`cancel` can end it early at any point; ``is_active`` reflects
      both.
    """

    def __init__(
        self,
        *,
        manifest: HostManifest,
        capability_id: str,
        max_ticks: int = 5,
        sampler: HostSampler | None = None,
    ) -> None:
        if max_ticks < 1:
            raise ValueError("max_ticks must be at least 1")
        if not manifest.supports(capability_id):
            raise ValueError(f"capability {capability_id!r} is not available in this host's manifest")
        self._manifest = manifest
        self._capability_id = capability_id
        self._max_ticks = max_ticks
        self._sampler = sampler if sampler is not None else HostSampler(providers=(StandardLibraryReadingProvider(),))
        self._ticks_run = 0
        self._cancelled = False
        self._readings: list[SensorReading] = []

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
        """Sample once, keeping only the reading for this session's own
        capability. Returns ``None`` once the session is no longer active."""
        if not self.is_active:
            return None
        readings, _ = self._sampler.sample(self._manifest)
        self._ticks_run += 1
        match = next((reading for reading in readings if reading.capability_id == self._capability_id), None)
        if match is not None:
            self._readings.append(match)
        return match

    def run_to_completion(self) -> SecondLookResult:
        """Tick until inactive (``max_ticks`` reached or cancelled)."""
        while self.is_active:
            self.tick()
        return SecondLookResult(
            capability_id=self._capability_id, readings=self.readings, cancelled=self._cancelled
        )
