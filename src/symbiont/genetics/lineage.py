"""Genotype-independent genealogy for Genome v2."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GenomeLineageRecord:
    """One inheritance event.

    genotype_hash identifies inherited gene content. genome_instance_id
    identifies this materialized genome instance. Parentage is genealogy,
    not genotype content.
    """

    reproduction_event_id: str
    genome_instance_id: str
    genotype_hash: str
    parent_organism_ids: tuple[str, ...] = ()
    parent_genome_instance_ids: tuple[str, ...] = ()
    generation: int = 0

    def __post_init__(self) -> None:
        if not self.reproduction_event_id:
            raise ValueError("reproduction_event_id must not be empty")
        if not self.genome_instance_id:
            raise ValueError("genome_instance_id must not be empty")
        if len(self.genotype_hash) != 64:
            raise ValueError("genotype_hash must be a SHA-256 hex digest")
        try:
            int(self.genotype_hash, 16)
        except ValueError as exc:
            raise ValueError("genotype_hash must be hexadecimal") from exc
        if self.generation < 0:
            raise ValueError("generation must be non-negative")
        if len(set(self.parent_organism_ids)) != len(self.parent_organism_ids):
            raise ValueError("parent organism ids must be unique")
        if len(set(self.parent_genome_instance_ids)) != len(self.parent_genome_instance_ids):
            raise ValueError("parent genome instance ids must be unique")


__all__ = ["GenomeLineageRecord"]
