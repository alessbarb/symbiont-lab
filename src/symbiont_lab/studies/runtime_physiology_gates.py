"""Evaluator-only integration gate for Milestone I physiology boundaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .physiology import run_sustained_repair_study
from .reproduction_runtime import run_runtime_reproduction_study
from .runtime_population import run_runtime_population_study
from .social_runtime_longitudinal import run_social_runtime_longitudinal_study


@dataclass(frozen=True, slots=True)
class RuntimePhysiologyGateStudy:
    """Aggregate independent longitudinal gates without feeding labels back."""

    repair_replay_equal: bool
    repair_without_intake: float
    reproduction_replay_equal: bool
    capacity_blocked_birth: bool
    social_continuation_replay_equal: bool
    social_interactions: int
    all_gates_pass: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_runtime_physiology_gate_study() -> RuntimePhysiologyGateStudy:
    """Run the bounded repair, population and social continuation gates.

    Each child study owns its own synthetic habitat and checkpoint boundary.
    This function only composes evaluator observations; no result is passed to
    an organism as a target, reward or platform label.
    """
    repair = run_sustained_repair_study()
    population = run_runtime_population_study()
    reproduction = run_runtime_reproduction_study()
    social = run_social_runtime_longitudinal_study(ticks=24, members=4)
    all_gates_pass = all(
        (
            repair.checkpoint_replay_equal,
            repair.no_intake_repaired == 0.0,
            reproduction.replay_equal,
            population.capacity_blocked_birth,
            social.continuation_replay_equal,
        )
    )
    return RuntimePhysiologyGateStudy(
        repair_replay_equal=repair.checkpoint_replay_equal,
        repair_without_intake=repair.no_intake_repaired,
        reproduction_replay_equal=reproduction.replay_equal,
        capacity_blocked_birth=population.capacity_blocked_birth,
        social_continuation_replay_equal=social.continuation_replay_equal,
        social_interactions=social.interactions,
        all_gates_pass=all_gates_pass,
    )


__all__ = ["RuntimePhysiologyGateStudy", "run_runtime_physiology_gate_study"]
