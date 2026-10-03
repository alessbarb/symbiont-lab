from __future__ import annotations

import platform
from pathlib import Path
from typing import Any

from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.core.orchestration.sense_requirements import (
    SENSE_OPTIONS,
    SenseRequirements,
    resolve_restore_sense_requirements,
    resolve_sense_requirements,
)
from symbiont.host.checkpoint import load_checkpoint_file
from symbiont.host.providers.interoception import (
    InteroceptionProvider,
    ShamInteroceptionProvider,
)
from symbiont.host.providers.linux_surfaces import LinuxSurfaceProvider
from symbiont.host.providers.portable_surfaces import PortableSurfaceProvider
from symbiont.host.providers.stdlib import StandardLibraryProvider
from symbiont.host.providers.stdlib_readings import StandardLibraryReadingProvider
from symbiont.host.sources import HostSenseSources

# Platforms on which host senses can be offered.
HOST_SENSE_SYSTEMS = frozenset({"Linux", "Darwin", "Windows"})
INTEROCEPTION_MODES = frozenset({"enabled", "sham", "absent"})


def canonical_host_sense_sources(
    requirements: SenseRequirements, *, system: str | None = None
) -> HostSenseSources:
    """The concrete sources that satisfy ``requirements`` on this platform."""
    if requirements.interoception_mode not in INTEROCEPTION_MODES:
        raise ValueError("interoception_mode must be enabled, sham or absent")
    system = platform.system() if system is None else system
    discovery: list[Any] = []
    readings: list[Any] = []
    if requirements.bootstrap_semantic_senses:
        discovery.append(StandardLibraryProvider())
        readings.append(StandardLibraryReadingProvider())

    # The interoceptive surface is only offered alongside host-sense discovery.
    # Linux exposes procfs/sysfs; macOS and Windows the portable aggregate surfaces.
    interoception = None
    available = system in HOST_SENSE_SYSTEMS
    if requirements.discover_senses and available:
        host = (
            LinuxSurfaceProvider() if system == "Linux" else PortableSurfaceProvider(system=system)
        )
        discovery.append(host)
        readings.append(host)
        if requirements.interoception_mode != "absent":
            provider_type = (
                ShamInteroceptionProvider
                if requirements.interoception_mode == "sham"
                else InteroceptionProvider
            )
            interoception = provider_type()
            discovery.append(interoception)
            readings.append(interoception)
    return HostSenseSources(
        discovery_providers=tuple(discovery),
        reading_providers=tuple(readings),
        interoception_provider=interoception,
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


def restore_canonical_organism(
    payload: dict[str, Any],
    runtime_type: type[OrganismRuntime] = OrganismRuntime,
    **overrides: Any,
) -> OrganismRuntime:
    """An organism restored from ``payload`` with the canonical sources attached.

    The checkpoint's recorded controls and the stated overrides are interpreted
    by the organism, not here.
    """
    requirements = resolve_restore_sense_requirements(payload, **_stated(overrides))
    return runtime_type.from_checkpoint(
        payload, host_sense_sources=canonical_host_sense_sources(requirements), **overrides
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
