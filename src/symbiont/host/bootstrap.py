from __future__ import annotations

from datetime import datetime

from .acclimation import HostAcclimation
from .contracts import DiscoveryPolicy, HostManifest
from .discovery import HostDiscovery
from .lifecycle import HostLifecycle
from .percepts import Percept, synthesize_percepts
from .providers.stdlib import StandardLibraryProvider
from .providers.stdlib_readings import StandardLibraryReadingProvider
from .readings import HostSampler, ReadingFailure, SensorReading
from .rhythms import RhythmModel, TimeBucket, time_bucket_for_hour


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


def current_time_bucket() -> TimeBucket:
    """The current coarse time-of-day bucket, computed from local wall time.

    The hour itself is read only to compute this bucket and is never
    returned or stored — see :func:`~symbiont.host.rhythms.time_bucket_for_hour`.
    """

    return time_bucket_for_hour(datetime.now().hour)


def learn_local_host_rhythms(
    *,
    ticks: int = 5,
    rhythm_model: RhythmModel | None = None,
    time_bucket: TimeBucket | None = None,
) -> RhythmModel:
    """Perceive the built-in providers for N ticks, learning one time-bucket's rhythm."""

    if ticks < 1:
        raise ValueError("ticks must be at least 1")
    resolved_model = rhythm_model if rhythm_model is not None else RhythmModel()
    resolved_bucket = time_bucket if time_bucket is not None else current_time_bucket()
    for _ in range(ticks):
        percepts = perceive_local_host()
        resolved_model.observe(percepts, time_bucket=resolved_bucket)
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
