"""Evaluator-only resource-regime shift study for Milestone K."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.runtime import OrganismRuntime
from symbiont.core.social import SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialRuntimeRegimeShiftStudy:
    phase_ticks: int
    pre_shift_successes: tuple[str, ...]
    post_shift_successes: tuple[str, ...]
    first_post_shift_resource: str
    new_resource_observed: bool
    checkpoint_replay_equal: bool
    continuation_replay_equal: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_runtime_regime_shift_study(*, phase_ticks: int = 8) -> SocialRuntimeRegimeShiftStudy:
    """Measure revision after a bounded change in anonymous resource supply.

    The evaluator changes only finite inventory between phases.  It does not
    select a target, assign a role, or tell the runtime which resource should
    be preferred.  Runtime ticks advance local freshness and evidence time.
    """
    if phase_ticks < 4:
        raise ValueError("phase_ticks must be at least 4")
    habitat = SocialHabitat(EcologicalResourcePool({"food": 0.0, "water": float(phase_ticks / 2)}))
    habitat.admit("adaptive")
    habitat.admit("peer")
    runtime = OrganismRuntime(
        organism_id="adaptive", social_habitat=habitat, social_exchange_quantum=0.5
    )
    pre_shift: list[str] = []
    for _ in range(phase_ticks):
        outcome = runtime.autonomous_social_step()
        if outcome is not None and outcome.granted > 0.0:
            pre_shift.append(outcome.resource)
        runtime.tick()

    runtime_checkpoint = runtime.checkpoint()
    habitat_checkpoint = habitat.checkpoint()
    restored = OrganismRuntime.from_checkpoint(runtime_checkpoint, social_habitat=habitat)
    checkpoint_replay_equal = restored.social_resource_ledger.evidence == runtime.social_resource_ledger.evidence

    habitat.engine.pool.replenish("food", float(phase_ticks / 2))
    post_shift: list[str] = []
    for _ in range(phase_ticks):
        outcome = restored.autonomous_social_step()
        if outcome is not None and outcome.granted > 0.0:
            post_shift.append(outcome.resource)
        restored.tick()

    replay_habitat = SocialHabitat.from_checkpoint(habitat_checkpoint)
    replay_runtime = OrganismRuntime.from_checkpoint(runtime_checkpoint, social_habitat=replay_habitat)
    replay_habitat.engine.pool.replenish("food", float(phase_ticks / 2))
    replay_post_shift: list[str] = []
    for _ in range(phase_ticks):
        outcome = replay_runtime.autonomous_social_step()
        if outcome is not None and outcome.granted > 0.0:
            replay_post_shift.append(outcome.resource)
        replay_runtime.tick()

    return SocialRuntimeRegimeShiftStudy(
        phase_ticks=phase_ticks,
        pre_shift_successes=tuple(pre_shift),
        post_shift_successes=tuple(post_shift),
        first_post_shift_resource=post_shift[0] if post_shift else "none",
        new_resource_observed="food" in post_shift,
        checkpoint_replay_equal=checkpoint_replay_equal,
        continuation_replay_equal=post_shift == replay_post_shift,
    )


__all__ = ["SocialRuntimeRegimeShiftStudy", "run_social_runtime_regime_shift_study"]
