"""Evaluator-only reproduction/death contract study for Milestone I."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.birth_authority import HabitatBirthAuthority
from symbiont.core.heredity import HeritableGenome
from symbiont.core.reproduction import paired_reproduce


@dataclass(frozen=True, slots=True)
class ReproductionStudy:
    parent_count: int
    offspring_count: int
    death_releases: int
    duplicate_death_ignored: bool
    remaining_budget: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_reproduction_study(*, capacity: int = 3, resource_budget: float = 3.0) -> ReproductionStudy:
    if capacity < 2 or resource_budget <= 0.0:
        raise ValueError("invalid reproduction study parameters")
    authority = HabitatBirthAuthority(habitat_id="study", capacity=capacity,
                                      resource_budget=resource_budget)
    genome_a = HeritableGenome("a", (("learning_rate", 0.1),))
    genome_b = HeritableGenome("b", (("learning_rate", 0.2),))
    parent_a = authority.birth(genome_id=genome_a.identity)
    parent_b = authority.birth(genome_id=genome_b.identity)
    assert parent_a is not None and parent_b is not None
    child = paired_reproduce(parent_a=parent_a.organism_id, parent_b=parent_b.organism_id,
                             genome_a=genome_a, genome_b=genome_b, generation=0,
                             authority=authority)
    assert child is not None
    first_death = authority.death(child.organism_id)
    second_death = authority.death(child.organism_id)
    return ReproductionStudy(2, 1, int(first_death is not None), second_death is None,
                             authority.resource_budget)


__all__ = ["ReproductionStudy", "run_reproduction_study"]
