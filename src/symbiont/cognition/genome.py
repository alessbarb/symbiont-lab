"""Compatibility import surface for the canonical Genome v2.

No genetic state or mutation logic lives in cognition anymore. Historical v1
payloads are converted explicitly through genetics.migration before the single
v2 codec validates them.
"""
from __future__ import annotations

from typing import Mapping

from symbiont.genetics.genome import (
    AdaptiveGeneRange,
    DevelopmentGenes,
    EvolvabilityGenes,
    Genome,
    GenomeCodec as _GenomeV2Codec,
    GenomeError,
    MotorGenes,
    MutationPolicyGenes,
    PlasticityGenes,
    RangeSpec,
    RegulationGenes,
    SensorimotorGenes,
    StructuralGenes,
    StructureGenes,
    _genome_to_plain_dict,
    flatten_genes,
    legacy_validation_version,
    parse_kernel_compatibility,
    satisfies_kernel_compatibility,
)
from symbiont.genetics.migration import migrate_v1_payload


class GenomeCodec(_GenomeV2Codec):
    """Single v2 codec with an explicit read-only migration entry for v1."""

    def load(self, payload: Mapping[str, object]) -> Genome:
        if payload.get("schema_version") == 1:
            payload = migrate_v1_payload(payload)
        return super().load(payload)


__all__ = [
    "AdaptiveGeneRange",
    "DevelopmentGenes",
    "EvolvabilityGenes",
    "Genome",
    "GenomeCodec",
    "GenomeError",
    "MotorGenes",
    "MutationPolicyGenes",
    "PlasticityGenes",
    "RangeSpec",
    "RegulationGenes",
    "SensorimotorGenes",
    "StructuralGenes",
    "StructureGenes",
    "_genome_to_plain_dict",
    "flatten_genes",
    "legacy_validation_version",
    "parse_kernel_compatibility",
    "satisfies_kernel_compatibility",
]
