from __future__ import annotations

from pathlib import Path

from lab.experiments.loader import load_experiment_file
from lab.experiments.registry import get_protocol


def test_cognitive_ecology_protocols_are_registered():
    expected = {
        "learning.structural-producer-fairness": "run_structural_producer_fairness_study",
        "learning.continuous-temporal-challenge": "run_continuous_temporal_challenge",
        "learning.cognitive-ecology-embodiment": "run_cognitive_ecology_embodiment_study",
        "learning.continuous-temporal-controls": "run_continuous_temporal_controls",
        "learning.embodied-behavioral-ablation": "run_embodied_behavioral_ablation",
        "learning.canonical-sensorimotor-agency": "run_sensorimotor_agency_study",
        "learning.canonical-sensorimotor-counterfactual": "run_counterfactual_replay_study",
        "learning.canonical-sensorimotor-adaptation": "run_sensorimotor_adaptation_study",
        "learning.generative-cognition-counterfactual-utility": "run_generative_counterfactual_utility_study",
        "learning.generative-cognition-recombination-construction": "run_generative_recombination_construction_study",
        "learning.generative-cognition-predictive-utility": "run_generative_predictive_utility_study",
        "learning.generative-cognition-model-correction": "run_generative_model_correction_study",
        "learning.generative-cognition-depth-calibration": "run_generative_depth_calibration_study",
        "learning.generative-cognition-replay-utility": "run_generative_replay_utility_study",
        "learning.generative-cognition-consolidation-gates": "run_generative_consolidation_gates_study",
        "learning.generative-cognition-planning-utility": "run_generative_planning_utility_study",
    }
    for protocol, function_name in expected.items():
        assert get_protocol(protocol).__name__ == function_name


def test_cognitive_ecology_preregistrations_bind_expected_protocols():
    root = Path("lab/experiments/learning")
    cases = {
        "structural-producer-fairness": "learning.structural-producer-fairness",
        "continuous-temporal-challenge": "learning.continuous-temporal-challenge",
        "cognitive-ecology-embodiment": "learning.cognitive-ecology-embodiment",
        "continuous-temporal-controls": "learning.continuous-temporal-controls",
        "embodied-behavioral-ablation": "learning.embodied-behavioral-ablation",
        "canonical-sensorimotor-adaptation": "learning.canonical-sensorimotor-adaptation",
        "generative-cognition-recombination-construction": "learning.generative-cognition-recombination-construction",
        "generative-cognition-predictive-utility": "learning.generative-cognition-predictive-utility",
        "generative-cognition-model-correction": "learning.generative-cognition-model-correction",
        "generative-cognition-depth-calibration": "learning.generative-cognition-depth-calibration",
        "generative-cognition-replay-utility": "learning.generative-cognition-replay-utility",
        "generative-cognition-consolidation-gates": "learning.generative-cognition-consolidation-gates",
        "generative-cognition-planning-utility": "learning.generative-cognition-planning-utility",
    }
    for directory, protocol in cases.items():
        spec = load_experiment_file(root / directory / "experiment.toml")
        assert spec.protocol == protocol
        assert tuple(spec.seeds) == (101, 127, 149)


def test_behavioral_ablation_preregisters_executable_horizon():
    spec = load_experiment_file(
        Path("lab/experiments/learning/embodied-behavioral-ablation/experiment.toml")
    )

    assert spec.extra_params["ablation"]["horizon_ticks"] == 256
