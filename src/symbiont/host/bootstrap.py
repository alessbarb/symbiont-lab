from __future__ import annotations

from .contracts import DiscoveryPolicy, HostManifest
from .discovery import HostDiscovery
from .providers.stdlib import StandardLibraryProvider


def discover_local_host(policy: DiscoveryPolicy | None = None) -> HostManifest:
    """Bootstrap the safe built-in senses available in the current host."""

    return HostDiscovery(
        providers=(StandardLibraryProvider(),),
        policy=policy,
    ).discover()
