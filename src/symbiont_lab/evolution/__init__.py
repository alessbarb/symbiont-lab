"""Genome mutation, evaluation-result selection, and lineage archiving
for laboratory evolution (roadmap v0.59).

This package belongs entirely to ``symbiont_lab``: it is the scientific
apparatus for explicit laboratory evolution and does not grant a resident
organism reproductive or deployment capability. Future organism-level
reproduction is a separate roadmap concern and must remain mediated by the
organism lifecycle and an authorized habitat rather than by importing this
laboratory apparatus into cognition.
"""

from .lineage import GenomeLineageRecord, LineageArchive, LineageRecord
from .mutation import (
    derive_child_genome,
    mutate_continuous_fields,
    mutate_genome,
    mutate_soft_budget,
)
from .recombination import recombine_genomes
from .reproduction import create_offspring_package

__all__ = [
    "GenomeLineageRecord",
    "LineageArchive",
    "LineageRecord",
    "create_offspring_package",
    "derive_child_genome",
    "mutate_continuous_fields",
    "mutate_genome",
    "mutate_soft_budget",
    "recombine_genomes",
]
