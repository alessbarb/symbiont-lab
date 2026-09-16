"""Evaluator-only integrated boundary matrix for Milestone K."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .social_runtime_adversarial import run_social_runtime_adversarial_study
from .social_runtime_context_replay import run_social_runtime_context_replay_study
from .social_runtime_generations import run_social_runtime_generations_study


@dataclass(frozen=True, slots=True)
class SocialBoundaryGateStudy:
    cooperation_bounded: bool
    contention_bounded: bool
    isolation_observable: bool
    rejection_reversible: bool
    context_replay_equal: bool
    lineage_replay_equal: bool
    child_remains_live: bool
    all_gates_pass: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_boundary_gate_study() -> SocialBoundaryGateStudy:
    """Compose independent K gates without feeding evaluator labels to runtime."""
    adversarial = run_social_runtime_adversarial_study()
    context = run_social_runtime_context_replay_study()
    generations = run_social_runtime_generations_study(generations=2)
    cooperation_bounded = 0.0 < adversarial.cooperation_granted <= 0.5
    contention_bounded = (
        0.0 <= adversarial.contention_granted < adversarial.contention_requested
    )
    isolation_observable = adversarial.isolated_opportunities == 1
    rejection_reversible = (
        adversarial.rejected_exchange_blocked
        and adversarial.resumed_exchange_granted > 0.0
    )
    context_replay_equal = context.checkpoint_equal and context.post_restore_parity
    lineage_replay_equal = generations.checkpoint_replay_equal and generations.lineage_closed
    all_gates_pass = all((
        cooperation_bounded,
        contention_bounded,
        isolation_observable,
        rejection_reversible,
        context_replay_equal,
        lineage_replay_equal,
        generations.final_child_live,
    ))
    return SocialBoundaryGateStudy(
        cooperation_bounded=cooperation_bounded,
        contention_bounded=contention_bounded,
        isolation_observable=isolation_observable,
        rejection_reversible=rejection_reversible,
        context_replay_equal=context_replay_equal,
        lineage_replay_equal=lineage_replay_equal,
        child_remains_live=generations.final_child_live,
        all_gates_pass=all_gates_pass,
    )


__all__ = ["SocialBoundaryGateStudy", "run_social_boundary_gate_study"]
