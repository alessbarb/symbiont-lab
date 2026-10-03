"""Which sense sources an organism requires, resolved without building any.

Pure: no provider is constructed, no platform is inspected, nothing outside the
organism is imported. The constructor and the restore path both resolve their
sense options here, and a composer outside the organism uses the same result to
decide which concrete sources to attach.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ...host.checkpoint import CheckpointError
from ..organism_profile import CANONICAL, HISTORICAL_V0, PROFILES, OrganismProfile

# Constructor options that decide which sense sources are attached.
SENSE_OPTIONS = (
    "discover_senses",
    "bootstrap_semantic_senses",
    "interoception_enabled",
    "interoception_mode",
)


@dataclass(frozen=True, slots=True)
class SenseRequirements:
    """What the organism requires of its sense sources. Names no implementation."""

    # host senses are to be discovered and offered
    discover_senses: bool
    # the fixed semantic host senses are to be offered
    bootstrap_semantic_senses: bool
    # "enabled" | "sham" | "absent"
    interoception_mode: str


def resolve_sense_requirements(
    *,
    profile: OrganismProfile | None = None,
    discover_senses: bool | None = None,
    bootstrap_semantic_senses: bool | None = None,
    interoception_enabled: bool | None = None,
    interoception_mode: str | None = None,
) -> SenseRequirements:
    """Options left unset come from the organism profile (ADR-0062)."""
    profile = profile if profile is not None else CANONICAL
    if discover_senses is None:
        discover_senses = profile.discover_senses
    if bootstrap_semantic_senses is None:
        bootstrap_semantic_senses = profile.bootstrap_semantic_senses
    if interoception_mode is None:
        interoception_mode = (
            profile.interoception_mode
            if interoception_enabled is None
            else ("enabled" if interoception_enabled else "absent")
        )
    return SenseRequirements(
        discover_senses=discover_senses,
        bootstrap_semantic_senses=bootstrap_semantic_senses,
        interoception_mode=interoception_mode,
    )


def restored_sense_options(
    payload: Mapping[str, Any], overrides: Mapping[str, Any]
) -> dict[str, Any]:
    """The sense options and profile a restore runs with.

    An option stated by the caller wins, even when stated as ``None``. Otherwise
    the value recorded in the checkpoint's effective configuration is used. A
    restored organism keeps the profile it was born with; checkpoints written
    before profiles existed are historical.
    """
    effective = payload.get("effective_config", {})
    options = {name: overrides[name] for name in SENSE_OPTIONS if name in overrides}
    for name in SENSE_OPTIONS:
        if name not in options and name in effective:
            options[name] = effective[name]
    if "profile" in overrides:
        options["profile"] = overrides["profile"]
    else:
        born_with = effective.get("profile_version", HISTORICAL_V0.version)
        if born_with not in PROFILES:
            raise CheckpointError(f"unknown organism profile version: {born_with!r}")
        options["profile"] = PROFILES[born_with]
    return options


def resolve_restore_sense_requirements(
    payload: Mapping[str, Any], **overrides: Any
) -> SenseRequirements:
    """Sense requirements of an organism restored from ``payload``."""
    return resolve_sense_requirements(**restored_sense_options(payload, overrides))


__all__ = [
    "SENSE_OPTIONS",
    "SenseRequirements",
    "resolve_restore_sense_requirements",
    "resolve_sense_requirements",
    "restored_sense_options",
]
