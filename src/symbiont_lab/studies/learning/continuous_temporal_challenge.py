from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Iterable

from symbiont_lab.modeling import SparseEchoStateRegressor


def _huber(error: float, delta: float = 1.0) -> float:
    magnitude = abs(error)
    if magnitude <= delta:
        return 0.5 * error * error
    return delta * (magnitude - 0.5 * delta)


@dataclass(frozen=True, slots=True)
class ContinuousTemporalTrial:
    seed: int
    ticks: int
    shift_tick: int
    esn_pre_shift_loss: float
    persistence_pre_shift_loss: float
    mean_pre_shift_loss: float
    esn_post_shift_early_loss: float
    persistence_post_shift_early_loss: float
    esn_post_shift_late_loss: float
    persistence_post_shift_late_loss: float
    esn_gain_pre_shift: float
    esn_gain_post_shift_late: float
    adaptation_recovery_ratio: float
    learned_values: int
    fixed_values: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ContinuousTemporalStudy:
    seeds: tuple[int, ...]
    trials: tuple[ContinuousTemporalTrial, ...]
    mean_gain_pre_shift: float
    mean_gain_post_shift_late: float
    mean_recovery_ratio: float

    def as_dict(self) -> dict[str, object]:
        return {
            "seeds": list(self.seeds),
            "trials": [trial.as_dict() for trial in self.trials],
            "mean_gain_pre_shift": self.mean_gain_pre_shift,
            "mean_gain_post_shift_late": self.mean_gain_post_shift_late,
            "mean_recovery_ratio": self.mean_recovery_ratio,
        }


def _mean(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot average an empty sequence")
    return sum(values) / len(values)


def _trial(seed: int, *, ticks: int) -> ContinuousTemporalTrial:
    if ticks < 160:
        raise ValueError("continuous temporal trial requires at least 160 ticks")

    rng = random.Random(seed)
    shift_tick = ticks // 2
    model = SparseEchoStateRegressor(
        input_dim=1,
        output_dim=1,
        reservoir_size=48,
        connectivity=0.12,
        spectral_scale=0.85,
        leak_rate=0.35,
        learning_rate=0.35,
        seed=seed,
    )

    value = 0.4
    history: list[float] = []
    esn_losses: list[float] = []
    persistence_losses: list[float] = []
    mean_losses: list[float] = []

    # Prediction at t is made from x_t, then evaluated against x_(t+1).
    for tick in range(ticks):
        coefficient = 0.82 if tick < shift_tick else -0.68
        noise = rng.gauss(0.0, 0.08)
        next_value = max(-0.98, min(0.98, coefficient * value + noise))

        model.observe((value,))
        prediction = model.predict()
        predicted_value = 0.0 if prediction is None else prediction.value[0]
        persistence = value
        running_mean = sum(history) / len(history) if history else 0.0

        esn_losses.append(_huber(next_value - predicted_value))
        persistence_losses.append(_huber(next_value - persistence))
        mean_losses.append(_huber(next_value - running_mean))

        model.learn((next_value,))
        history.append(value)
        value = next_value

    window = max(20, ticks // 10)
    pre_slice = slice(shift_tick - window, shift_tick)
    early_slice = slice(shift_tick, shift_tick + window)
    late_slice = slice(ticks - window, ticks)

    esn_pre = _mean(esn_losses[pre_slice])
    persist_pre = _mean(persistence_losses[pre_slice])
    mean_pre = _mean(mean_losses[pre_slice])
    esn_early = _mean(esn_losses[early_slice])
    persist_early = _mean(persistence_losses[early_slice])
    esn_late = _mean(esn_losses[late_slice])
    persist_late = _mean(persistence_losses[late_slice])

    best_pre = min(persist_pre, mean_pre)
    early_excess = max(1e-12, esn_early - esn_late)
    shift_damage = max(1e-12, esn_early - esn_pre)
    recovery = max(0.0, min(1.0, early_excess / shift_damage))

    usage = model.resource_usage()
    return ContinuousTemporalTrial(
        seed=seed,
        ticks=ticks,
        shift_tick=shift_tick,
        esn_pre_shift_loss=esn_pre,
        persistence_pre_shift_loss=persist_pre,
        mean_pre_shift_loss=mean_pre,
        esn_post_shift_early_loss=esn_early,
        persistence_post_shift_early_loss=persist_early,
        esn_post_shift_late_loss=esn_late,
        persistence_post_shift_late_loss=persist_late,
        esn_gain_pre_shift=best_pre - esn_pre,
        esn_gain_post_shift_late=persist_late - esn_late,
        adaptation_recovery_ratio=recovery,
        learned_values=usage.learned_values,
        fixed_values=model.fixed_values,
    )


def run_continuous_temporal_challenge(
    seeds: Iterable[int] = (101, 127, 149),
    *,
    ticks: int = 400,
) -> ContinuousTemporalStudy:
    seed_list = tuple(seeds)
    if not seed_list:
        raise ValueError("seeds must not be empty")
    trials = tuple(_trial(seed, ticks=ticks) for seed in seed_list)
    count = len(trials)
    return ContinuousTemporalStudy(
        seeds=seed_list,
        trials=trials,
        mean_gain_pre_shift=sum(t.esn_gain_pre_shift for t in trials) / count,
        mean_gain_post_shift_late=sum(t.esn_gain_post_shift_late for t in trials) / count,
        mean_recovery_ratio=sum(t.adaptation_recovery_ratio for t in trials) / count,
    )


__all__ = [
    "ContinuousTemporalStudy",
    "ContinuousTemporalTrial",
    "run_continuous_temporal_challenge",
]
