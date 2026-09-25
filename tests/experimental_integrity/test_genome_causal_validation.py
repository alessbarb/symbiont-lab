from __future__ import annotations

from symbiont_lab.studies.genetics.genome_causal_validation import (
    run_genome_causal_validation,
)


def test_genome_causal_validation_is_single_locus_and_reproducible() -> None:
    first = run_genome_causal_validation(seed=991, steps=48)
    second = run_genome_causal_validation(seed=991, steps=48)

    assert first.as_dict() == second.as_dict()
    assert first.exploration_pair.differing_loci == ("sensorimotor.spontaneous_activity_baseline",)
    assert first.learning_pair.differing_loci == ("plasticity.learning_rate.baseline",)
    assert first.exploration_pair.phenotype_diverged
    assert first.learning_pair.phenotype_diverged
    assert first.exploration_pair.trajectory_diverged
    assert first.learning_pair.trajectory_diverged
    assert first.passed


def test_exploration_pair_changes_sampling_under_same_seed() -> None:
    result = run_genome_causal_validation(seed=127, steps=64)
    pair = result.exploration_pair
    assert pair.low.initial_exploration_rate < pair.high.initial_exploration_rate
    assert pair.low.activation_trace != pair.high.activation_trace


def test_learning_pair_changes_sensorimotor_learning_trajectory() -> None:
    result = run_genome_causal_validation(seed=149, steps=64)
    pair = result.learning_pair
    assert pair.low.initial_learning_rate < pair.high.initial_learning_rate
    assert (
        pair.low.prediction_error_trace != pair.high.prediction_error_trace
        or pair.low.final_relation_weight != pair.high.final_relation_weight
    )
