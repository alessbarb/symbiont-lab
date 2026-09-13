from __future__ import annotations

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
