from __future__ import annotations

from .acclimation import HostAcclimation
from .contracts import DiscoveryPolicy, HostManifest
from .discovery import HostDiscovery
from .drift import DriftAwareBaseline, DriftObservation
from .lifecycle import HostLifecycle
from .percepts import Percept, synthesize_percepts
from .providers.stdlib import StandardLibraryProvider
from .providers.stdlib_readings import StandardLibraryReadingProvider
from .readings import HostSampler, ReadingFailure, SensorReading
from .rhythms import RhythmModel, cycle_phase_for_tick
from .second_look import SecondLookResult, SecondLookSession


def discover_local_host(policy: DiscoveryPolicy | None = None) -> HostManifest:
    """Bootstrap the safe built-in senses available in the current host."""

    return HostDiscovery(
        providers=(StandardLibraryProvider(),),
        policy=policy,
    ).discover()


def sample_local_host(
    manifest: HostManifest | None = None,
) -> tuple[tuple[SensorReading, ...], tuple[ReadingFailure, ...]]:
    """Sample the safe built-in readings available in the current host.

    Discovers the host first (if a manifest isn't already provided) so
    sampling only ever produces readings for capabilities discovery itself
    already accepted.
    """

    resolved_manifest = manifest if manifest is not None else discover_local_host()
    return HostSampler(providers=(StandardLibraryReadingProvider(),)).sample(resolved_manifest)


def perceive_local_host(manifest: HostManifest | None = None) -> tuple[Percept, ...]:
    """Sample the built-in providers and synthesize platform-neutral percepts."""

    readings, _ = sample_local_host(manifest)
    return synthesize_percepts(readings)


def learn_local_host_rhythms(
    *,
    ticks: int = 5,
    rhythm_model: RhythmModel | None = None,
    start_tick: int = 0,
) -> RhythmModel:
    """Perceive the built-in providers for N ticks along the internal cycle.

    Each tick is placed in the macro phase of ``start_tick + i`` (ADR-0042);
    the host clock is never consulted.
    """

    if ticks < 1:
        raise ValueError("ticks must be at least 1")
    if start_tick < 0:
        raise ValueError("start_tick must be non-negative")
    resolved_model = rhythm_model if rhythm_model is not None else RhythmModel()
    for offset in range(ticks):
        percepts = perceive_local_host()
        resolved_model.observe(percepts, phase=cycle_phase_for_tick(start_tick + offset))
    return resolved_model


def monitor_local_host(policy: DiscoveryPolicy | None = None) -> HostLifecycle:
    """Bootstrap a bounded, backoff-aware lifecycle over the built-in providers."""

    return HostLifecycle(
        discovery=HostDiscovery(providers=(StandardLibraryProvider(),), policy=policy),
        reading_providers=(StandardLibraryReadingProvider(),),
    )


def acclimate_local_host(
    *,
    ticks: int = 5,
    lifecycle: HostLifecycle | None = None,
    acclimation: HostAcclimation | None = None,
) -> tuple[HostAcclimation, HostLifecycle]:
    """Run bounded ticks against the built-in providers to seed a baseline.

    Threat classification is out of scope by construction: this only ever
    returns a :class:`HostAcclimation`, which can produce descriptive
    statistics and nothing else (roadmap v0.33).
    """

    if ticks < 1:
        raise ValueError("ticks must be at least 1")
    resolved_lifecycle = lifecycle if lifecycle is not None else monitor_local_host()
    resolved_acclimation = acclimation if acclimation is not None else HostAcclimation()
    for _ in range(ticks):
        snapshot = resolved_lifecycle.tick()
        resolved_acclimation.observe(snapshot.readings)
    return resolved_acclimation, resolved_lifecycle


def track_local_host_drift(
    *,
    ticks: int = 5,
    baselines: dict[str, DriftAwareBaseline] | None = None,
) -> tuple[dict[str, DriftAwareBaseline], list[dict[str, DriftObservation]]]:
    """Perceive the built-in providers for N ticks, classifying each percept
    against its own aging baseline (roadmap v0.36).

    One :class:`DriftAwareBaseline` per percept name, created on first sight.
    Returns the baselines (so a caller can keep tracking across calls) and
    the per-tick classifications, in tick order.
    """

    if ticks < 1:
        raise ValueError("ticks must be at least 1")
    resolved_baselines = baselines if baselines is not None else {}
    tick_observations: list[dict[str, DriftObservation]] = []
    for _ in range(ticks):
        percepts = perceive_local_host()
        observations: dict[str, DriftObservation] = {}
        for percept in percepts:
            if percept.value is None:
                continue
            baseline = resolved_baselines.get(percept.name)
            if baseline is None:
                baseline = DriftAwareBaseline()
                resolved_baselines[percept.name] = baseline
            observations[percept.name] = baseline.observe(percept.value)
        tick_observations.append(observations)
    return resolved_baselines, tick_observations


def second_look_at_local_host(
    capability_id: str,
    *,
    max_ticks: int = 5,
    manifest: HostManifest | None = None,
) -> SecondLookResult:
    """Run a temporary, bounded, cancellable higher-resolution sampling
    session against one already-discovered capability of this host
    (roadmap v0.39).

    Discovers the host first (if a manifest isn't already provided) so the
    same authorization check :class:`SecondLookSession` performs — the
    capability must already be in the manifest — is grounded in this host's
    actual current discovery, not a stale or hypothetical one.
    """
    resolved_manifest = manifest if manifest is not None else discover_local_host()
    session = SecondLookSession(
        manifest=resolved_manifest, capability_id=capability_id, max_ticks=max_ticks
    )
    return session.run_to_completion()
