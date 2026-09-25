"""Evaluator-only gate matrix for the currently active developmental milestones."""

from __future__ import annotations

from dataclasses import dataclass

from .predictive_development_gates import run_predictive_development_gate_study
from .runtime_physiology_gates import run_runtime_physiology_gate_study
from .social_development_gates import run_social_development_gate_study


@dataclass(frozen=True, slots=True)
class DevelopmentalMilestoneGateStudy:
    physiology_i: bool
    predictive_j: bool
    social_k: bool
    all_gates_pass: bool


def run_developmental_milestone_gate_study() -> DevelopmentalMilestoneGateStudy:
    """Verify I/J/K independently, without sharing evaluator state with runtime."""
    physiology = run_runtime_physiology_gate_study()
    predictive = run_predictive_development_gate_study()
    social = run_social_development_gate_study()
    values = {
        "physiology_i": physiology.all_gates_pass,
        "predictive_j": predictive.all_gates_pass,
        "social_k": social.all_gates_pass,
    }
    return DevelopmentalMilestoneGateStudy(**values, all_gates_pass=all(values.values()))


__all__ = ["DevelopmentalMilestoneGateStudy", "run_developmental_milestone_gate_study"]
