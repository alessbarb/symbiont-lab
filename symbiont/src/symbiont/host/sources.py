"""Sense sources handed to the organism from outside.

The organism does not need to know where a source comes from. Whoever composes
it supplies the discovery and reading providers and says whether host senses are
available; the organism attaches them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .discovery import DiscoveryProvider
from .readings import ReadingProvider


@dataclass(frozen=True, slots=True)
class HostSenseSources:
    discovery_providers: tuple[DiscoveryProvider, ...] = ()
    reading_providers: tuple[ReadingProvider, ...] = ()
    # The provider through which the organism's interoceptive channels are offered, if any.
    interoception_provider: Any | None = None
    # "available" | "unavailable": whether host senses could be offered at all.
    availability: str = "unavailable"

    def __post_init__(self) -> None:
        if self.availability not in {"available", "unavailable"}:
            raise ValueError("availability must be 'available' or 'unavailable'")
