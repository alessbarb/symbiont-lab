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
from .readings import (
    ReadingPrivacyClass,
    ReadingQuality,
    SensorReading,
    Unit,
    reading_matches_manifest,
)

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
    "ReadingPrivacyClass",
    "ReadingQuality",
    "SensorReading",
    "Unit",
    "discover_local_host",
    "reading_matches_manifest",
]
