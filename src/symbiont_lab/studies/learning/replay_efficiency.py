from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass

from symbiont_lab.studies.learning.replay_pressure_curve import (
    PRESSURES,
    ReplayDose,
    _budget_for_pressure,
    run_replay_pressure_curve_study,
)


@dataclass(frozen=True, slots=True)
class ReplayEfficiencyInterval:
    start_pressure: float
    end_pressure: float
    added_steps: int
    loss_gain: float
    gain_per_step: float


@dataclass(frozen=True, slots=True)
class ReplayEfficiencySeedResult:
    seed: int
    intervals: tuple[ReplayEfficiencyInterval, ...]
    diminishing_returns: bool
    best_gain_per_step: float
    final_gain_per_step: float


@dataclass(frozen=True, slots=True)
class ReplayEfficiencyStudy:
    seeds: tuple[int, ...]
    ticks: int
    per_seed: tuple[ReplayEfficiencySeedResult, ...]
    diminishing_return_seeds: int
    mean_best_gain_per_step: float
    mean_final_gain_per_step: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _intervals(doses: tuple[ReplayDose, ...]) -> tuple[ReplayEfficiencyInterval, ...]:
    values: list[ReplayEfficiencyInterval] = []
    for left, right in zip(doses, doses[1:]):
        added_steps = right.steps - left.steps
        if added_steps <= 0:
            raise ValueError("replay step budget must increase strictly across doses")
        loss_gain = left.test_loss - right.test_loss
        values.append(ReplayEfficiencyInterval(
            start_pressure=left.pressure,
            end_pressure=right.pressure,
            added_steps=added_steps,
            loss_gain=loss_gain,
            gain_per_step=loss_gain / added_steps,
        ))
    return tuple(values)


def run_replay_efficiency_study(
    *,
    seeds: Sequence[int] = (101, 127, 149),
    ticks: int = 128,
) -> ReplayEfficiencyStudy:
    curve = run_replay_pressure_curve_study(seeds=seeds, ticks=ticks)
    results: list[ReplayEfficiencySeedResult] = []
    for item in curve.per_seed:
        intervals = _intervals(item.doses)
        gains = [interval.gain_per_step for interval in intervals]
        diminishing = all(
            later <= earlier + 1e-12
            for earlier, later in zip(gains, gains[1:])
        )
        results.append(ReplayEfficiencySeedResult(
            seed=item.seed,
            intervals=intervals,
            diminishing_returns=diminishing,
            best_gain_per_step=max(gains),
            final_gain_per_step=gains[-1],
        ))

    return ReplayEfficiencyStudy(
        seeds=curve.seeds,
        ticks=curve.ticks,
        per_seed=tuple(results),
        diminishing_return_seeds=sum(item.diminishing_returns for item in results),
        mean_best_gain_per_step=sum(item.best_gain_per_step for item in results) / len(results),
        mean_final_gain_per_step=sum(item.final_gain_per_step for item in results) / len(results),
    )


__all__ = [
    "ReplayEfficiencyInterval",
    "ReplayEfficiencySeedResult",
    "ReplayEfficiencyStudy",
    "run_replay_efficiency_study",
]
