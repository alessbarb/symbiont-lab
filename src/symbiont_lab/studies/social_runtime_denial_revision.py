"""Evaluator-only proof that repeated local denials revise resource choice."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.runtime import OrganismRuntime
from symbiont.core.social import SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialRuntimeDenialRevisionStudy:
    phase_ticks: int
    pre_shift_successes: tuple[str, ...]
    post_shift_attempts: tuple[tuple[str, float], ...]
    revision_tick: int | None
    checkpoint_replay_equal: bool
    continuation_replay_equal: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _run_post_shift(runtime: OrganismRuntime, ticks: int) -> tuple[tuple[str, float], ...]:
    attempts: list[tuple[str, float]] = []
    for _ in range(ticks):
        outcome = runtime.autonomous_social_step()
        if outcome is not None:
            attempts.append((outcome.resource, outcome.granted))
    return tuple(attempts)


def run_social_runtime_denial_revision_study(
    *, phase_ticks: int = 8,
) -> SocialRuntimeDenialRevisionStudy:
    """Change one opaque inventory and require revision after local denials.

    The evaluator only changes finite inventory.  It never tells the runtime
    which token is preferred; the runtime must discover the replacement from
    its own consecutive-denial evidence.  Replay uses an independent habitat.
    """
    if phase_ticks < 4:
        raise ValueError("phase_ticks must be at least 4")
    habitat = SocialHabitat(
        EcologicalResourcePool({"alpha": 0.0, "beta": float(phase_ticks) * 0.5}),
        max_members=2,
    )
    for member in ("adaptive", "peer"):
        habitat.admit(member)
    runtime = OrganismRuntime(
        organism_id="adaptive", social_habitat=habitat, social_exchange_quantum=0.5
    )
    pre_shift: list[str] = []
    for _ in range(phase_ticks):
        outcome = runtime.autonomous_social_step()
        if outcome is not None and outcome.granted > 0.0:
            pre_shift.append(outcome.resource)
        # The social step itself advances local evidence.  Keeping this
        # evaluator phase free of unrelated cognitive scheduling makes the
        # resource-regime boundary the only changing condition.

    runtime_checkpoint = runtime.checkpoint()
    habitat_checkpoint = habitat.checkpoint()
    restored = OrganismRuntime.from_checkpoint(runtime_checkpoint, social_habitat=habitat)
    checkpoint_replay_equal = restored.social_resource_ledger.evidence == runtime.social_resource_ledger.evidence

    habitat.engine.pool.replenish("alpha", float(phase_ticks))
    post_shift = _run_post_shift(restored, phase_ticks)
    denied = False
    revision_tick: int | None = None
    for index, (resource, granted) in enumerate(post_shift):
        if resource == "beta" and granted <= 0.0:
            denied = True
        elif denied and resource == "alpha" and granted > 0.0:
            revision_tick = index
            break

    replay_habitat = SocialHabitat.from_checkpoint(habitat_checkpoint)
    replay_runtime = OrganismRuntime.from_checkpoint(runtime_checkpoint, social_habitat=replay_habitat)
    replay_habitat.engine.pool.replenish("alpha", float(phase_ticks))
    replay_post_shift = _run_post_shift(replay_runtime, phase_ticks)
    return SocialRuntimeDenialRevisionStudy(
        phase_ticks=phase_ticks,
        pre_shift_successes=tuple(pre_shift),
        post_shift_attempts=post_shift,
        revision_tick=revision_tick,
        checkpoint_replay_equal=checkpoint_replay_equal,
        continuation_replay_equal=post_shift == replay_post_shift,
    )


__all__ = ["SocialRuntimeDenialRevisionStudy", "run_social_runtime_denial_revision_study"]
