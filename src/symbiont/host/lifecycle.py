from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Iterable

from .contracts import HostManifest
from .discovery import HostDiscovery
from .readings import HostSampler, ReadingFailure, ReadingProvider, SensorReading


@dataclass(slots=True, frozen=True)
class LifecycleSnapshot:
    """One tick's discovery + sampling result."""

    tick: int
    manifest: HostManifest
    readings: tuple[SensorReading, ...]
    reading_failures: tuple[ReadingFailure, ...]
    backed_off_providers: tuple[str, ...]


class HostLifecycle:
    """Bounded, backoff-aware repeated discovery and sampling (roadmap v0.32).

    A single :class:`~symbiont.host.discovery.HostDiscovery` or
    :class:`~symbiont.host.readings.HostSampler` call already isolates one
    provider's failure from the others within that call (v0.29/v0.31). This
    adds what only shows up across *repeated* calls over the organism's
    lifetime:

    - hot capability changes — every tick re-discovers, so a capability that
      appears or disappears between ticks is observable via
      :meth:`capability_changes`;
    - backoff — a reading provider that keeps failing is skipped for a
      growing number of ticks instead of being retried every single tick,
      and is retried at full frequency again the moment it next succeeds;
    - bounded buffers — history never grows past ``history_limit`` snapshots.
    """

    def __init__(
        self,
        *,
        discovery: HostDiscovery,
        reading_providers: Iterable[ReadingProvider],
        history_limit: int = 32,
        base_backoff_ticks: int = 1,
        max_backoff_ticks: int = 32,
    ) -> None:
        if history_limit < 1:
            raise ValueError("history_limit must be at least 1")
        if base_backoff_ticks < 1:
            raise ValueError("base_backoff_ticks must be at least 1")
        if max_backoff_ticks < base_backoff_ticks:
            raise ValueError("max_backoff_ticks must be at least base_backoff_ticks")

        self._discovery = discovery
        self._reading_providers = tuple(reading_providers)
        provider_ids = [provider.provider_id for provider in self._reading_providers]
        if len(provider_ids) != len(set(provider_ids)):
            raise ValueError("provider_id values must be unique")

        self._base_backoff_ticks = base_backoff_ticks
        self._max_backoff_ticks = max_backoff_ticks
        self._history: Deque[LifecycleSnapshot] = deque(maxlen=history_limit)
        self._retry_at_tick: dict[str, int] = {}
        self._failure_streak: dict[str, int] = {}
        self._tick_count = 0

    @property
    def history(self) -> tuple[LifecycleSnapshot, ...]:
        return tuple(self._history)

    def tick(self) -> LifecycleSnapshot:
        self._tick_count += 1
        manifest = self._discovery.discover()

        eligible = [
            provider
            for provider in self._reading_providers
            if self._retry_at_tick.get(provider.provider_id, 0) < self._tick_count
        ]
        backed_off = tuple(
            sorted(
                provider.provider_id
                for provider in self._reading_providers
                if provider not in eligible
            )
        )

        if eligible:
            readings, failures = HostSampler(eligible).sample(manifest)
        else:
            readings, failures = (), ()

        failed_ids = {failure.provider_id for failure in failures}
        for provider in eligible:
            if provider.provider_id in failed_ids:
                streak = self._failure_streak.get(provider.provider_id, 0) + 1
                self._failure_streak[provider.provider_id] = streak
                delay = min(
                    self._base_backoff_ticks * (2 ** (streak - 1)),
                    self._max_backoff_ticks,
                )
                self._retry_at_tick[provider.provider_id] = self._tick_count + delay
            else:
                self._failure_streak.pop(provider.provider_id, None)
                self._retry_at_tick.pop(provider.provider_id, None)

        snapshot = LifecycleSnapshot(
            tick=self._tick_count,
            manifest=manifest,
            readings=readings,
            reading_failures=failures,
            backed_off_providers=backed_off,
        )
        self._history.append(snapshot)
        return snapshot

    def capability_changes(self) -> tuple[str, ...]:
        """Capability ids whose availability differs between the last two ticks."""
        if len(self._history) < 2:
            return ()
        previous, current = self._history[-2], self._history[-1]
        before = {capability.capability_id for capability in previous.manifest.available}
        after = {capability.capability_id for capability in current.manifest.available}
        return tuple(sorted(before.symmetric_difference(after)))
