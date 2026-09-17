from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, Iterable

from .contracts import HostManifest
from .discovery import HostDiscovery
from .readings import CapabilitySamplingOutcome, HostSampler, ReadingFailure, ReadingProvider, SensorReading

SamplingSelector = Callable[[HostManifest], Iterable[str] | None]


@dataclass(slots=True, frozen=True)
class LifecycleSnapshot:
    """One tick's discovery + sampling result."""

    tick: int
    manifest: HostManifest
    readings: tuple[SensorReading, ...]
    reading_failures: tuple[ReadingFailure, ...]
    backed_off_providers: tuple[str, ...]
    sampled_capability_ids: tuple[str, ...] = ()
    sampling_outcomes: tuple[CapabilitySamplingOutcome, ...] = ()


class HostLifecycle:
    """Bounded, backoff-aware repeated discovery and selective sampling.

    Discovery still observes which *safe* capabilities exist every tick. Sampling can
    independently narrow that manifest through a caller-supplied selector, which is
    how a developing organism can reduce observation cost without losing the ability
    to notice that a dormant/new capability exists and occasionally probe it again.
    """

    def __init__(
        self,
        *,
        discovery: HostDiscovery,
        reading_providers: Iterable[ReadingProvider],
        history_limit: int = 32,
        base_backoff_ticks: int = 1,
        max_backoff_ticks: int = 32,
        clock: Callable[[], float] = time.perf_counter,
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
        self._clock = clock

    @property
    def history(self) -> tuple[LifecycleSnapshot, ...]:
        return tuple(self._history)

    def fork_for_child(self) -> "HostLifecycle":
        """Copy provider configuration without acquired lifecycle state."""
        return HostLifecycle(
            discovery=self._discovery,
            reading_providers=self._reading_providers,
            history_limit=self._history.maxlen or 32,
            base_backoff_ticks=self._base_backoff_ticks,
            max_backoff_ticks=self._max_backoff_ticks,
            clock=self._clock,
        )

    def tick(self, *, sampling_selector: SamplingSelector | None = None) -> LifecycleSnapshot:
        self._tick_count += 1
        manifest = self._discovery.discover()

        requested: frozenset[str] | None = None
        if sampling_selector is not None:
            selected = sampling_selector(manifest)
            if selected is not None:
                available_ids = {capability.capability_id for capability in manifest.available}
                requested = frozenset(capability_id for capability_id in selected if capability_id in available_ids)

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
            readings, failures, sampling_outcomes = HostSampler(eligible).sample_with_outcomes(
                manifest,
                capability_ids=requested,
                clock=self._clock,
            )
        else:
            readings, failures, sampling_outcomes = (), (), ()

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
            sampled_capability_ids=tuple(sorted(reading.capability_id for reading in readings)),
            sampling_outcomes=sampling_outcomes,
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
