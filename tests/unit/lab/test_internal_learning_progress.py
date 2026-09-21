from __future__ import annotations

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.learning.internal_learning_progress import _pearson


def test_internal_learning_progress_protocol_registered():
    assert (
        get_protocol("learning.internal-learning-progress").__name__
        == "run_internal_learning_progress_study"
    )


def test_internal_learning_progress_pearson_tracks_same_direction():
    assert _pearson((1.0, 0.5, 0.1), (0.8, 0.4, 0.05)) > 0.99


def test_internal_learning_progress_pearson_detects_inverse_signal():
    assert _pearson((1.0, 0.5, 0.1), (-0.8, -0.4, -0.05)) < -0.99
