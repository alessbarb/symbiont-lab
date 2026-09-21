"""Evaluator-only shared-habitat intake study for Milestone I."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.ecology import SharedHabitat
from symbiont.core.runtime import OrganismRuntime


@dataclass(frozen=True, slots=True)
class SharedHabitatIntakeStudy:
    first_granted: float
    second_granted: float
    remaining_resources: float
    capacity_limited: bool
    checkpoint_replay_equal: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_shared_habitat_intake_study() -> SharedHabitatIntakeStudy:
    """Verify finite intake allocation between two admitted residents."""
    habitat = SharedHabitat(habitat_id="intake-study", capacity=2, resources=1.0)
    assert habitat.admit("resident-a")
    assert habitat.admit("resident-b")
    runtimes = tuple(
        OrganismRuntime(organism_id=organism_id, habitat=habitat)
        for organism_id in ("resident-a", "resident-b")
    )
    for runtime in runtimes:
        runtime.metabolism.charge("maintenance", 1.0)

    first = runtimes[0].request_resource_intake(0.75)
    checkpoint = runtimes[1].checkpoint()
    habitat_checkpoint = habitat.checkpoint()
    second = runtimes[1].request_resource_intake(0.75)

    replay_habitat = SharedHabitat.from_checkpoint(habitat_checkpoint)
    replay_runtime = OrganismRuntime.from_checkpoint(checkpoint, habitat=replay_habitat)
    replay_second = replay_runtime.request_resource_intake(0.75)
    return SharedHabitatIntakeStudy(
        first_granted=first,
        second_granted=second,
        remaining_resources=habitat.snapshot().available_resources,
        capacity_limited=second < 0.75,
        checkpoint_replay_equal=second == replay_second,
    )


__all__ = ["SharedHabitatIntakeStudy", "run_shared_habitat_intake_study"]
