"""Cognitive graph, genome and plasticity kernel (roadmap v0.55+).

This package never imports symbiont_lab -- cognition must stay
independent of the evaluation apparatus that will eventually score it
(see tests/experimental_integrity/test_ground_truth_boundary.py).
"""

from .learning import ShadowPrediction
