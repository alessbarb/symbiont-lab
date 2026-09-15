"""OS-agnostic boundary between Symbiont and a consenting local host."""

from .acclimation import CapabilityBaseline, HostAcclimation
from .adaptive import (
    AdaptiveSenseModel,
    PairAccumulator,
    RelationView,
    SamplingPlan,
    SenseState,
    SensoryRelation,
)
from .bootstrap import (
    acclimate_local_host,
    current_time_bucket,
    discover_local_host,
    learn_local_host_rhythms,
    monitor_local_host,
    perceive_local_host,
    sample_local_host,
    second_look_at_local_host,
    track_local_host_drift,
)
from .checkpoint import CHECKPOINT_SCHEMA_VERSION, CheckpointError, export_checkpoint, import_checkpoint
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
from .drift import DriftAwareBaseline, DriftKind, DriftObservation
from .lifecycle import HostLifecycle, LifecycleSnapshot
from .hypotheses import HypothesisStatus, SignalHypothesis, HypothesisTracker
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
from .rhythms import RhythmModel, TimeBucket, time_bucket_for_hour
from .second_look import SecondLookResult, SecondLookSession

__all__ = [
    "AccessMode", "AdaptiveSenseModel", "HypothesisStatus", "SignalHypothesis", "HypothesisTracker", "PairAccumulator", "RelationView", "SamplingPlan",
    "SenseState", "SensoryRelation", "CHECKPOINT_SCHEMA_VERSION", "Capability",
    "CapabilityBaseline", "CapabilityKind", "CapabilityScope", "CheckpointError",
    "DEFAULT_PERCEPT_NAMES", "DiscoveryFailure", "DiscoveryPolicy", "DiscoveryProvider",
    "DriftAwareBaseline", "DriftKind", "DriftObservation", "HostAcclimation",
    "HostDiscovery", "HostLifecycle", "HostManifest", "HostSampler", "LifecycleSnapshot",
    "Percept", "ReadingFailure", "ReadingPrivacyClass", "ReadingProvider", "ReadingQuality",
    "RhythmModel", "SecondLookResult", "SecondLookSession", "SensorReading", "TimeBucket",
    "Unit", "acclimate_local_host", "current_time_bucket", "discover_local_host",
    "export_checkpoint", "import_checkpoint", "learn_local_host_rhythms",
    "monitor_local_host", "perceive_local_host", "reading_matches_manifest",
    "sample_local_host", "second_look_at_local_host", "synthesize_percepts",
    "time_bucket_for_hour", "track_local_host_drift",
]
