"""Evaluator-only integration gates for Milestone K social development."""
from __future__ import annotations

from dataclasses import dataclass

from .social_boundary_gates import run_social_boundary_gate_study
from .social_runtime_denial_revision import run_social_runtime_denial_revision_study
from .social_runtime_generations import run_social_runtime_generations_study
from .social_runtime_longitudinal import run_social_runtime_longitudinal_study
from .social_runtime_resource_adaptation import run_social_runtime_resource_adaptation_study
from .social_runtime_specialization import run_social_runtime_specialization_study


@dataclass(frozen=True, slots=True)
class SocialDevelopmentGateStudy:
    boundary_contract: bool
    longitudinal_replay: bool
    lineage_replay: bool
    resource_revision: bool
    denial_revision: bool
    niche_differentiation: bool
    all_gates_pass: bool


def run_social_development_gate_study() -> SocialDevelopmentGateStudy:
    """Compose independent social contracts without feeding labels to runtime."""
    boundary = run_social_boundary_gate_study()
    longitudinal = run_social_runtime_longitudinal_study()
    generations = run_social_runtime_generations_study()
    resource = run_social_runtime_resource_adaptation_study()
    denial = run_social_runtime_denial_revision_study()
    specialization = run_social_runtime_specialization_study()

    values = {
        "boundary_contract": boundary.all_gates_pass,
        "longitudinal_replay": longitudinal.checkpoint_replay_equal and longitudinal.continuation_replay_equal,
        "lineage_replay": generations.checkpoint_replay_equal and generations.lineage_closed and generations.final_child_live,
        "resource_revision": resource.checkpoint_replay_equal and resource.denied_initial_request and resource.initial_resource != resource.adapted_resource,
        "denial_revision": denial.checkpoint_replay_equal and denial.continuation_replay_equal and denial.revision_tick is not None,
        "niche_differentiation": specialization.checkpoint_replay_equal and specialization.continuation_replay_equal and specialization.distinct_resource_count >= 2,
    }
    return SocialDevelopmentGateStudy(**values, all_gates_pass=all(values.values()))


__all__ = ["SocialDevelopmentGateStudy", "run_social_development_gate_study"]
