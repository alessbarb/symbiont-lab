from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, TypeAlias

MetadataValue: TypeAlias = str | int | float | bool | None


class CapabilityKind(StrEnum):
    RUNTIME = "runtime"
    COMPUTE = "compute"
    MEMORY = "memory"
    STORAGE = "storage"
    PROCESS_ACTIVITY = "process_activity"
    NETWORK_ACTIVITY = "network_activity"
    FILESYSTEM_ACTIVITY = "filesystem_activity"
    THERMAL = "thermal"
    POWER = "power"
    SERVICE_ACTIVITY = "service_activity"
    CLOCK = "clock"
    SIGNAL = "signal"


class AccessMode(StrEnum):
    READ_ONLY = "read_only"
    WRITE = "write"
    EXECUTE = "execute"


class CapabilityScope(StrEnum):
    LOCAL = "local"
    REMOTE = "remote"


@dataclass(slots=True, frozen=True)
class Capability:
    """One sense a host can offer without exposing host identity."""

    capability_id: str
    kind: CapabilityKind
    source: str
    access: AccessMode = AccessMode.READ_ONLY
    scope: CapabilityScope = CapabilityScope.LOCAL
    available: bool = True
    detail: tuple[tuple[str, MetadataValue], ...] = ()

    def __post_init__(self) -> None:
        if not self.capability_id or any(char.isspace() for char in self.capability_id):
            raise ValueError("capability_id must be a non-empty token")
        if not self.source:
            raise ValueError("source must not be empty")
        keys = [key for key, _ in self.detail]
        if len(keys) != len(set(keys)):
            raise ValueError("capability detail keys must be unique")
        forbidden = {"hostname", "username", "user", "home", "cwd", "ip", "mac"}
        if forbidden.intersection(key.lower() for key in keys):
            raise ValueError("capability detail must not contain host identity")


@dataclass(slots=True, frozen=True)
class DiscoveryFailure:
    provider_id: str
    reason: str


@dataclass(slots=True, frozen=True)
class HostManifest:
    """Deterministic account of the safe senses available to Symbiont."""

    schema_version: int
    capabilities: tuple[Capability, ...]
    failures: tuple[DiscoveryFailure, ...]

    @property
    def available(self) -> tuple[Capability, ...]:
        return tuple(capability for capability in self.capabilities if capability.available)

    def supports(self, capability_id: str) -> bool:
        return any(
            capability.capability_id == capability_id and capability.available
            for capability in self.capabilities
        )


class DiscoveryProvider(Protocol):
    """Platform-specific probes implement this boundary; cognition never does."""

    @property
    def provider_id(self) -> str: ...

    def discover(self) -> tuple[Capability, ...]: ...


@dataclass(slots=True, frozen=True)
class DiscoveryPolicy:
    """Hard boundary for autonomous discovery."""

    allowed_access: frozenset[AccessMode] = field(
        default_factory=lambda: frozenset({AccessMode.READ_ONLY})
    )
    allowed_scopes: frozenset[CapabilityScope] = field(
        default_factory=lambda: frozenset({CapabilityScope.LOCAL})
    )

    def accepts(self, capability: Capability) -> bool:
        return (
            capability.access in self.allowed_access
            and capability.scope in self.allowed_scopes
        )
