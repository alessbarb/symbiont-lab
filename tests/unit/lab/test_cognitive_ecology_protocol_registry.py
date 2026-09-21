from __future__ import annotations

from pathlib import Path

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.experiments.spec import load_experiment_file


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
    }
    for directory, protocol in cases.items():
        spec = load_experiment_file(root / directory / "experiment.toml")
        assert spec.protocol == protocol
        assert tuple(spec.seeds) == (101, 127, 149)
