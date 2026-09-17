import pytest
from pathlib import Path

from symbiont_lab.experiments.loader import load_experiment_file
from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.longitudinal_population_ecology import (
    run_longitudinal_population_ecology_study,
    study_digest,
)


def test_longitudinal_study_is_bounded_and_replayable() -> None:
    result = run_longitudinal_population_ecology_study(
        seeds=(101,), stages=(8,), hosts=2, include_multigeneration=True
    )
    stage = result.stage_results[0]
    assert result.organism_capabilities_changed is False
    assert result.integrated_multigeneration_communication is False
    assert stage.finite_state and stage.counters_bounded and stage.replay_equal
    assert result.multigeneration["lineage_closed"] is True


def test_longitudinal_digest_and_registry_are_deterministic() -> None:
    first = run_longitudinal_population_ecology_study(
        seeds=(127,), stages=(4,), hosts=1, include_multigeneration=False
    )
    second = run_longitudinal_population_ecology_study(
        seeds=(127,), stages=(4,), hosts=1, include_multigeneration=False
    )
    assert study_digest(first) == study_digest(second)
    assert get_protocol("learning.longitudinal-population-ecology") is run_longitudinal_population_ecology_study


def test_longitudinal_preregistration_loads_with_bounded_campaign_controls() -> None:
    spec = load_experiment_file(
        Path("experiments/learning/longitudinal-population-ecology/experiment.toml")
    )
    assert spec.protocol == "learning.longitudinal-population-ecology"
    assert spec.extra_params["campaign"]["stages"] == [1000, 10000]


@pytest.mark.parametrize("kwargs", [
    {"stages": (0,)}, {"stages": (100_001,)}, {"hosts": 0}, {"hosts": 33},
    {"stages": (1, 1)},
])
def test_longitudinal_limits_fail_closed(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        run_longitudinal_population_ecology_study(
            seeds=(101,), include_multigeneration=False, **kwargs
        )
