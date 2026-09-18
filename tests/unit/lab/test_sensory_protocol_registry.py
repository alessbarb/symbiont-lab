from pathlib import Path

from symbiont_lab.experiments.loader import load_experiment_file
from symbiont_lab.experiments.registry import PROTOCOLS


_PROTOCOLS = (
    "perception.identity-equivalence",
    "perception.adaptive-delta-discovery",
    "perception.temporal-scale-specialisation",
    "perception.modality-specialisation",
    "perception.sensory-duplication-divergence",
    "perception.sensory-ablation",
    "perception.multisource-specialisation",
    "perception.same-world-phenotype-divergence",
    "perception.autonomous-sensory-selection",
    "perception.sensory-regime-reversal",
    "perception.sensory-null-selection",
    "perception.experience-conditioned-phenotype",
)


def test_all_sensory_protocols_are_registered():
    for protocol in _PROTOCOLS:
        assert protocol in PROTOCOLS


def test_all_sensory_experiment_documents_load_and_bind_protocols():
    root = Path(__file__).resolve().parents[3] / "experiments" / "perception"
    documents = sorted(root.glob("*/experiment.toml"))
    assert len(documents) == len(_PROTOCOLS)
    loaded = {load_experiment_file(path).protocol for path in documents}
    assert loaded == set(_PROTOCOLS)
