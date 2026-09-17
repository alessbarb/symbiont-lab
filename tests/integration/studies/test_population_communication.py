from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.observability.population_communication import run_population_communication_study


def test_population_communication_protocol_reconstructs_only_real_edges():
    assert get_protocol("observability.population-communication").__name__ == "run_population_communication_study"
    result = run_population_communication_study(seeds=(101, 127, 149))
    assert result.bounded_history and result.factual_only and result.no_feedback
    for seed in result.per_seed:
        assert seed.replay_deterministic
        assert seed.reconstructed_path == ("A", "B", "C", "D")
        assert seed.edges == (("A", "B"), ("B", "C"), ("C", "D"))
        assert seed.event_count == 3
        assert seed.grounding_event_count == 3
        assert seed.no_inferred_edges


def test_population_communication_rejects_empty_seed_set():
    try:
        run_population_communication_study(seeds=())
    except ValueError:
        pass
    else:
        raise AssertionError("empty seed set must fail closed")
