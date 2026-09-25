"""Evaluator-only integration gates for Milestone K social development."""

from __future__ import annotations

from dataclasses import dataclass

from .social_boundary_gates import run_social_boundary_gate_study
from .social_emergence import run_social_emergence_study
from .social_runtime_adversarial import run_social_runtime_adversarial_study
from .social_runtime_competition import run_social_runtime_competition_study
from .social_runtime_denial_revision import run_social_runtime_denial_revision_study
from .social_runtime_emergence import run_social_runtime_emergence_study
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
    adversarial_boundaries: bool
    finite_competition: bool
    emergent_interactions: bool
    runtime_emergence: bool
    runtime_emergence_replay: bool
    runtime_population_generalization: bool
    all_gates_pass: bool


def run_social_development_gate_study() -> SocialDevelopmentGateStudy:
    """Compose independent social contracts without feeding labels to runtime."""
    boundary = run_social_boundary_gate_study()
    longitudinal = run_social_runtime_longitudinal_study()
    generations = run_social_runtime_generations_study()
    resource = run_social_runtime_resource_adaptation_study()
    denial = run_social_runtime_denial_revision_study()
    specialization = run_social_runtime_specialization_study()
    adversarial = run_social_runtime_adversarial_study()
    competition = run_social_runtime_competition_study()
    emergence = run_social_emergence_study()
    runtime_emergence = run_social_runtime_emergence_study()
    runtime_emergence_replay = run_social_runtime_emergence_study() == runtime_emergence
    population_variants = tuple(
        run_social_runtime_emergence_study(members=members) for members in (3, 5)
    )

    values = {
        "boundary_contract": boundary.all_gates_pass,
        "longitudinal_replay": longitudinal.checkpoint_replay_equal
        and longitudinal.continuation_replay_equal,
        "lineage_replay": generations.checkpoint_replay_equal
        and generations.lineage_closed
        and generations.final_child_live,
        "resource_revision": resource.checkpoint_replay_equal
        and resource.denied_initial_request
        and resource.initial_resource != resource.adapted_resource,
        "denial_revision": denial.checkpoint_replay_equal
        and denial.continuation_replay_equal
        and denial.revision_tick is not None,
        "niche_differentiation": specialization.checkpoint_replay_equal
        and specialization.continuation_replay_equal
        and specialization.distinct_resource_count >= 2,
        "adversarial_boundaries": adversarial.rejected_exchange_blocked
        and adversarial.resumed_exchange_granted > 0.0
        and adversarial.isolated_opportunities > 0,
        "finite_competition": competition.no_global_label
        and competition.peer_attributed_losses > 0
        and competition.finite_resource_remaining >= 0.0,
        "emergent_interactions": emergence.interactions > 0
        and emergence.unique_pairs > 1
        and emergence.pair_entropy > 0.0,
        "runtime_emergence": (
            runtime_emergence.interactions > 0
            and runtime_emergence.unique_pairs > 1
            and runtime_emergence.pair_entropy > 0.0
            and runtime_emergence.isolated_members == 0
            and runtime_emergence.reciprocal_observations > 0
        ),
        "runtime_emergence_replay": runtime_emergence_replay,
        "runtime_population_generalization": all(
            result.interactions > 0 and result.unique_pairs > 1 and result.isolated_members == 0
            for result in population_variants
        ),
    }
    return SocialDevelopmentGateStudy(**values, all_gates_pass=all(values.values()))


__all__ = ["SocialDevelopmentGateStudy", "run_social_development_gate_study"]
