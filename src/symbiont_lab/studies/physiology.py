"""Deterministic, evaluator-only studies for Milestone I viability semantics."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from symbiont.core.metabolism import MetabolicLedger
from symbiont.core.physiology import PhysiologyController, VitalState


@dataclass(frozen=True, slots=True)
class PhysiologyStudy:
    ticks: int
    states: tuple[str, ...]
    transitions: int
    death_tick: int | None
    final_reserve: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_physiology_study(
    *,
    ticks: int = 32,
    maintenance_cost: float = 0.08,
    intake: Iterable[float] = (),
) -> PhysiologyStudy:
    """Run a bounded no-free-replenishment viability trajectory.

    ``intake`` is an explicit environmental supply per tick. The study never
    feeds evaluator truth back into the organism and is independent of host
    providers, making results reproducible and suitable for archive/replay.
    """
    if ticks < 1 or maintenance_cost < 0:
        raise ValueError("invalid physiology study parameters")
    schedule = tuple(float(value) for value in intake)
    if any(value < 0 for value in schedule):
        raise ValueError("intake values must be non-negative")
    kinds = ("observation", "cognition", "persistence", "maintenance")
    ledger = MetabolicLedger(replenishment={kind: 0.0 for kind in kinds})
    controller = PhysiologyController()
    states: list[str] = []
    for tick in range(ticks):
        if tick < len(schedule):
            ledger.intake("maintenance", schedule[tick])
        ledger.advance(retained_units=maintenance_cost)
        snapshot = controller.advance(ledger.snapshot(), tick=tick)
        states.append(snapshot.state.value)
        if snapshot.state is VitalState.DEAD:
            break
    snapshot = ledger.snapshot()
    physiology = controller.snapshot()
    return PhysiologyStudy(len(states), tuple(states), physiology.transitions,
                           physiology.death_tick, snapshot.reserve["maintenance"])


__all__ = ["PhysiologyStudy", "run_physiology_study"]
