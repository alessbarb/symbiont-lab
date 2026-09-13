"""OS-agnostic boundary between Symbiont and a consenting local host."""

from .acclimation import CapabilityBaseline, HostAcclimation
from .bootstrap import (
    acclimate_local_host,
    discover_local_host,
    monitor_local_host,
    perceive_local_host,
    sample_local_host,
)
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
from .lifecycle import HostLifecycle, LifecycleSnapshot
from .percepts import DEFAULT_PERCEPT_NAMES, Percept, synthesize_percepts
from .readings import (
    HostSampler,
    ReadingFailure,
    ReadingPrivacyClass,
    ReadingProvider,
    ReadingQuality,
    SensorReading,
    Unit,
    reading_matches_manifest,
)

__all__ = [
    "AccessMode",
    "Capability",
    "CapabilityBaseline",
    "CapabilityKind",
    "CapabilityScope",
    "DEFAULT_PERCEPT_NAMES",
    "DiscoveryFailure",
    "DiscoveryPolicy",
    "DiscoveryProvider",
    "HostAcclimation",
    "HostDiscovery",
    "HostLifecycle",
    "HostManifest",
    "HostSampler",
    "LifecycleSnapshot",
    "Percept",
    "ReadingFailure",
    "ReadingPrivacyClass",
    "ReadingProvider",
    "ReadingQuality",
    "SensorReading",
    "Unit",
    "acclimate_local_host",
    "discover_local_host",
    "monitor_local_host",
    "perceive_local_host",
    "reading_matches_manifest",
    "sample_local_host",
    "synthesize_percepts",
]
