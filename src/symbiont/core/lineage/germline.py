"""Compatibility surface for the canonical Genome v2 genetics package.

All genetic state and operators live in symbiont.genetics. This module exists
only so historical imports resolve to the same objects.
"""
from __future__ import annotations

from importlib import resources
import json

from ...genetics.genome import Genome, GenomeCodec
from ...genetics.germline import (
    EpigeneticMark,
    GermlineState,
    InheritancePackage,
    create_offspring_package,
)
from ...genetics.mutation import mutate_genome
from ...genetics.recombination import recombine_genomes
from ...genetics.schema import DEFAULT_GENOME_SCHEMA, GeneSpec, GeneType


SymbiontGenome = Genome
LocusSpec = GeneSpec
LocusType = GeneType
STANDARD_COGNITIVE_LOCI = DEFAULT_GENOME_SCHEMA.specs


def create_standard_genome(genome_id: str) -> Genome:
    payload = json.loads(
        resources.files("symbiont.genetics")
        .joinpath("defaults/base-genome-v2.json")
        .read_text(encoding="utf-8")
    )
    payload["genome_id"] = (
        str(genome_id)
        if str(genome_id).startswith("genome_")
        else f"genome_{genome_id}"
    )
    payload["parent_ids"] = []
    return GenomeCodec().load(payload)


def create_germline_state(
    genome: Genome,
    *,
    acquired_capture_enabled: bool = False,
) -> GermlineState:
    return GermlineState.from_genome(
        genome,
        acquired_capture_enabled=acquired_capture_enabled,
    )


__all__ = [
    "EpigeneticMark",
    "GermlineState",
    "InheritancePackage",
    "LocusSpec",
    "LocusType",
    "STANDARD_COGNITIVE_LOCI",
    "SymbiontGenome",
    "create_germline_state",
    "create_offspring_package",
    "create_standard_genome",
    "mutate_genome",
    "recombine_genomes",
]
