"""OS-agnostic boundary between Symbiont and a consenting local host."""

from .bootstrap import discover_local_host
from .contracts import (
    AccessMode,
    Capability,
    CapabilityKind,
    CapabilityScope,
    DiscoveryFailure,
    DiscoveryPolicy,
    DiscoveryProvider,
    HostManifest,
)
from .discovery import HostDiscovery

__all__ = [
    "AccessMode",
    "Capability",
    "CapabilityKind",
    "CapabilityScope",
    "DiscoveryFailure",
    "DiscoveryPolicy",
    "DiscoveryProvider",
    "HostDiscovery",
    "HostManifest",
    "discover_local_host",
]
