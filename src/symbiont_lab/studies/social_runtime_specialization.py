"""Evaluator-only bounded niche differentiation study for Milestone K."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.runtime import OrganismRuntime
from symbiont.core.social import SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialRuntimeSpecializationStudy:
    ticks: int
    member_a_resource: str
    member_b_resource: str
    distinct_resource_count: int
    checkpoint_replay_equal: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_runtime_specialization_study(*, ticks: int = 12) -> SocialRuntimeSpecializationStudy:
    """Measure differentiated resource choices after local contention.

    Both runtimes see the same opaque tokens and finite pool. The evaluator
    only schedules a bounded contention order and replenishes the synthetic
    habitat; it does not assign roles, preferences or target resources.
    """
    if ticks < 4:
        raise ValueError("ticks must be at least 4")
    habitat = SocialHabitat(
        EcologicalResourcePool({"food": 0.5, "water": float(ticks)}),
        max_members=2,
    )
    habitat.admit("member-a")
    habitat.admit("member-b")
    runtimes = [
        OrganismRuntime(organism_id="member-a", social_habitat=habitat, social_exchange_quantum=0.5),
        OrganismRuntime(organism_id="member-b", social_habitat=habitat, social_exchange_quantum=0.5),
    ]
    sequences: dict[str, list[str]] = {runtime.organism_id: [] for runtime in runtimes}
    replay_equal = True
    for tick in range(ticks):
        if tick == ticks // 2:
            checkpoints = [runtime.checkpoint() for runtime in runtimes]
            restored = [
                OrganismRuntime.from_checkpoint(payload, social_habitat=habitat)
                for payload in checkpoints
            ]
            replay_equal = all(
                left.social_resource_ledger.evidence == right.social_resource_ledger.evidence
                for left, right in zip(runtimes, restored)
            )
            runtimes = restored
        for runtime in runtimes:
            outcome = runtime.autonomous_social_step()
            if outcome is not None and outcome.granted > 0.0:
                sequences[runtime.organism_id].append(outcome.resource)
        habitat.engine.pool.replenish("food", 0.5)
        habitat.engine.pool.replenish("water", 1.0)
    choices = tuple(
        sequence[0] if sequence else "none"
        for sequence in (sequences["member-a"], sequences["member-b"])
    )
    return SocialRuntimeSpecializationStudy(
        ticks=ticks,
        member_a_resource=choices[0],
        member_b_resource=choices[1],
        distinct_resource_count=len({choice for choice in choices if choice != "none"}),
        checkpoint_replay_equal=replay_equal,
    )


__all__ = [
    "SocialRuntimeSpecializationStudy",
    "run_social_runtime_specialization_study",
]
