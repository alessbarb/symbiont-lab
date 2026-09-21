from __future__ import annotations

from pathlib import Path

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.experiments.loader import load_experiment_file


def test_cognitive_ecology_protocols_are_registered():
    expected = {
        "learning.structural-producer-fairness":
            "run_structural_producer_fairness_study",
        "learning.continuous-temporal-challenge":
            "run_continuous_temporal_challenge",
        "learning.cognitive-ecology-embodiment":
            "run_cognitive_ecology_embodiment_study",
        "learning.continuous-temporal-controls":
            "run_continuous_temporal_controls",
        "learning.embodied-behavioral-ablation":
            "run_embodied_behavioral_ablation",
        "learning.canonical-sensorimotor-agency":
            "run_sensorimotor_agency_study",
        "learning.canonical-sensorimotor-counterfactual":
            "run_counterfactual_replay_study",
    }
    for protocol, function_name in expected.items():
        assert get_protocol(protocol).__name__ == function_name


def test_cognitive_ecology_preregistrations_bind_expected_protocols():
    root = Path("experiments/learning")
    cases = {
        "structural-producer-fairness": "learning.structural-producer-fairness",
        "continuous-temporal-challenge": "learning.continuous-temporal-challenge",
        "cognitive-ecology-embodiment": "learning.cognitive-ecology-embodiment",
        "continuous-temporal-controls": "learning.continuous-temporal-controls",
        "embodied-behavioral-ablation": "learning.embodied-behavioral-ablation",
    }
    for directory, protocol in cases.items():
        spec = load_experiment_file(root / directory / "experiment.toml")
        assert spec.protocol == protocol
        assert tuple(spec.seeds) == (101, 127, 149)



def test_behavioral_ablation_preregisters_executable_horizon():
    spec = load_experiment_file(
        Path("experiments/learning/embodied-behavioral-ablation/experiment.toml")
    )

    assert spec.extra_params["ablation"]["horizon_ticks"] == 256
