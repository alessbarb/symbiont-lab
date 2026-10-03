from __future__ import annotations

import platform
from typing import Any

from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.core.organism_profile import CANONICAL
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
    *,
    discover_senses: bool,
    bootstrap_semantic_senses: bool,
    interoception_mode: str,
    system: str | None = None,
) -> HostSenseSources:
    """The concrete sources a canonical organism is given on this platform."""
    if interoception_mode not in INTEROCEPTION_MODES:
        raise ValueError("interoception_mode must be enabled, sham or absent")
    system = platform.system() if system is None else system
    discovery: list[Any] = []
    readings: list[Any] = []
    if bootstrap_semantic_senses:
        discovery.append(StandardLibraryProvider())
        readings.append(StandardLibraryReadingProvider())

    # The interoceptive surface is only offered alongside host-sense discovery.
    # Linux exposes procfs/sysfs; macOS and Windows the portable aggregate surfaces.
    interoception = None
    available = system in HOST_SENSE_SYSTEMS
    if discover_senses and available:
        host = (
            LinuxSurfaceProvider() if system == "Linux" else PortableSurfaceProvider(system=system)
        )
        discovery.append(host)
        readings.append(host)
        if interoception_mode != "absent":
            provider_type = (
                ShamInteroceptionProvider if interoception_mode == "sham" else InteroceptionProvider
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


def create_canonical_organism(
    runtime_type: type[OrganismRuntime] = OrganismRuntime, **options: Any
) -> OrganismRuntime:
    """Build an organism with the canonical concrete sense sources attached.

    Accepts the same options as the runtime. Options left unset come from the
    organism profile, exactly as in the runtime's own constructor.
    """
    profile = options.get("profile") or CANONICAL
    discover_senses = options.get("discover_senses")
    if discover_senses is None:
        discover_senses = profile.discover_senses
    bootstrap = options.get("bootstrap_semantic_senses")
    if bootstrap is None:
        bootstrap = profile.bootstrap_semantic_senses
    mode = options.get("interoception_mode")
    if mode is None:
        enabled = options.get("interoception_enabled")
        mode = (
            profile.interoception_mode if enabled is None else ("enabled" if enabled else "absent")
        )
    sources = canonical_host_sense_sources(
        discover_senses=bool(discover_senses),
        bootstrap_semantic_senses=bool(bootstrap),
        interoception_mode=mode,
    )
    return runtime_type(host_sense_sources=sources, **options)
