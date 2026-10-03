from __future__ import annotations

from symbiont.sensory.fitness import sensory_fitness


def test_health_and_novelty_cannot_create_utility_without_downstream_gain() -> None:
    assert (
        sensory_fitness(
            predictive_contribution=0.0,
            downstream_contribution=0.0,
            novelty=1.0,
            reliability=1.0,
            redundancy=0.0,
            cost=0.0,
        )
        == 0.0
    )


def test_demonstrated_gain_is_modulated_by_quality_and_cost() -> None:
    useful = sensory_fitness(
        predictive_contribution=0.8,
        downstream_contribution=0.6,
        novelty=0.8,
        reliability=0.9,
        redundancy=0.1,
        cost=0.1,
    )
    redundant = sensory_fitness(
        predictive_contribution=0.8,
        downstream_contribution=0.6,
        novelty=0.1,
        reliability=0.9,
        redundancy=1.0,
        cost=0.5,
    )
    assert useful > 0.0
    assert useful > redundant
