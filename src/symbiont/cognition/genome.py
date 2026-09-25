"""Public import surface for the canonical Genome v2 model.

Historical payloads are deliberately not accepted through this module. Callers
that read persisted legacy artifacts must use ``symbiont.genetics.migration``
at the explicit compatibility boundary instead.
"""

from __future__ import annotations

from symbiont.genetics.genome import (
    AdaptiveGeneRange,
    DevelopmentGenes,
    EvolvabilityGenes,
    Genome,
    GenomeCodec,
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
