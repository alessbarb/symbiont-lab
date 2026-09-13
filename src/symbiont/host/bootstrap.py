from __future__ import annotations

from .acclimation import HostAcclimation
from .contracts import DiscoveryPolicy, HostManifest
from .discovery import HostDiscovery
from .lifecycle import HostLifecycle
from .providers.stdlib import StandardLibraryProvider
from .providers.stdlib_readings import StandardLibraryReadingProvider
from .readings import HostSampler, ReadingFailure, SensorReading


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
