"""Canonical composition of an organism with its concrete sense sources.

The organism does not choose a platform. This is where the Lab decides which
concrete host providers a canonical organism is given, and hands them over.
"""

from lab.integration.organism.canonical import (
    canonical_host_sense_sources,
    canonical_restore_sources,
    create_canonical_organism,
    load_or_create_canonical_organism,
    restore_canonical_organism,
    restore_canonical_resident,
)

__all__ = [
    "canonical_host_sense_sources",
    "canonical_restore_sources",
    "create_canonical_organism",
    "load_or_create_canonical_organism",
    "restore_canonical_organism",
    "restore_canonical_resident",
]
