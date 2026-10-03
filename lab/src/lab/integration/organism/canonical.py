from __future__ import annotations

import platform
from pathlib import Path
from typing import Any

from symbiont.core.orchestration.canonical_birth import restore_resident_with_canonical_cognition
from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.core.orchestration.sense_requirements import (
    SENSE_OPTIONS,
    SenseRequirements,
    resolve_restore_sense_requirements,
    resolve_sense_requirements,
)
from symbiont.host.checkpoint import load_checkpoint_file
from symbiont.host.providers.linux_surfaces import LinuxSurfaceProvider
from symbiont.host.providers.portable_surfaces import PortableSurfaceProvider
from symbiont.host.providers.process_telemetry import HostProcessTelemetry
from symbiont.host.providers.stdlib import StandardLibraryProvider
from symbiont.host.providers.stdlib_readings import StandardLibraryReadingProvider
from symbiont.host.sources import HostSenseSources

# Platforms on which host senses can be offered.
HOST_SENSE_SYSTEMS = frozenset({"Linux", "Darwin", "Windows"})


def canonical_host_sense_sources(
    requirements: SenseRequirements, *, system: str | None = None
) -> HostSenseSources:
    """The concrete sources that satisfy ``requirements`` on this platform."""
    system = platform.system() if system is None else system
    discovery: list[Any] = []
    readings: list[Any] = []
    if requirements.bootstrap_semantic_senses:
        discovery.append(StandardLibraryProvider())
        readings.append(StandardLibraryReadingProvider())

    # Linux exposes procfs/sysfs; macOS and Windows the portable aggregate surfaces.
    # Interoception is the organism's own; the Lab only supplies host telemetry.
    telemetry = None
    available = system in HOST_SENSE_SYSTEMS
    if requirements.discover_senses and available:
        host = (
            LinuxSurfaceProvider() if system == "Linux" else PortableSurfaceProvider(system=system)
        )
        discovery.append(host)
        readings.append(host)
        telemetry = HostProcessTelemetry()
    return HostSenseSources(
        discovery_providers=tuple(discovery),
        reading_providers=tuple(readings),
        process_telemetry=telemetry,
        availability="available" if available else "unavailable",
    )


def _stated(options: dict[str, Any]) -> dict[str, Any]:
    return {name: options[name] for name in ("profile", *SENSE_OPTIONS) if name in options}


def create_canonical_organism(
    runtime_type: type[OrganismRuntime] = OrganismRuntime, **options: Any
) -> OrganismRuntime:
    """A new organism with the canonical concrete sense sources attached.

    Accepts the options of the runtime. Which sources it needs is resolved by
    the organism; this only decides what satisfies them on this platform.
    """
    requirements = resolve_sense_requirements(**_stated(options))
    return runtime_type(host_sense_sources=canonical_host_sense_sources(requirements), **options)


def canonical_restore_sources(payload: dict[str, Any], **overrides: Any) -> HostSenseSources:
    """The canonical sources for restoring ``payload`` under ``overrides``."""
    requirements = resolve_restore_sense_requirements(payload, **_stated(overrides))
    return canonical_host_sense_sources(requirements)


def restore_canonical_organism(
    payload: dict[str, Any],
    runtime_type: type[OrganismRuntime] = OrganismRuntime,
    **overrides: Any,
) -> OrganismRuntime:
    """An organism restored from ``payload`` with the canonical sources attached.

    The checkpoint's recorded controls and the stated overrides are interpreted
    by the organism, not here.
    """
    return runtime_type.from_checkpoint(
        payload, host_sense_sources=canonical_restore_sources(payload, **overrides), **overrides
    )


def restore_canonical_resident(
    payload: dict[str, Any],
    runtime_type: type[OrganismRuntime] = OrganismRuntime,
    **overrides: Any,
) -> OrganismRuntime:
    """A resident restored with canonical cognition and the canonical sources."""
    return restore_resident_with_canonical_cognition(
        payload,
        runtime_class=runtime_type,
        host_sense_sources=canonical_restore_sources(payload, **overrides),
        **overrides,
    )


def load_or_create_canonical_organism(
    path: str | Path,
    runtime_type: type[OrganismRuntime] = OrganismRuntime,
    **options: Any,
) -> OrganismRuntime:
    """Restore from ``path`` if a checkpoint is there, otherwise create."""
    payload = load_checkpoint_file(path)
    if payload is None:
        return create_canonical_organism(runtime_type, **options)
    return restore_canonical_organism(payload, runtime_type, **options)
