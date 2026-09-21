"""Compare the recurrent shadow challenger with a transparent linear control."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from symbiont_lab.modeling import SparseEchoStateRegressor

from .embodied_sensorimotor_shadow import _condition_actions, _huber, _trace


@dataclass(frozen=True, slots=True)
class ModelComparisonCondition:
    condition: str
    reservoir_gain: float
    linear_gain: float
    reservoir_minus_linear: float


@dataclass(frozen=True, slots=True)
class ModelComparisonSeedResult:
    seed: int
    conditions: tuple[ModelComparisonCondition, ...]
    recurrent_beats_linear_causally: bool


@dataclass(frozen=True, slots=True)
class EmbodiedModelComparisonStudy:
    seeds: tuple[int, ...]
    ticks: int
    physics_substeps_per_tick: int
    reservoir_size: int
    per_seed: tuple[ModelComparisonSeedResult, ...]
    recurrent_beats_linear_all_seeds: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class _LinearNlms:
    def __init__(self, input_dim: int, output_dim: int, learning_rate: float = 0.4):
        self._weights = [[0.0] * (input_dim + 1) for _ in range(output_dim)]
        self._last: list[float] | None = None
        self._learning_rate = learning_rate

    def observe(self, values: list[float]) -> None:
        self._last = [1.0, *values]

    def predict(self) -> list[float]:
        if self._last is None:
            raise RuntimeError("observe must precede predict")
        return [sum(weight * value for weight, value in zip(row, self._last)) for row in self._weights]

    def learn(self, target: list[float]) -> None:
        prediction = self.predict()
        assert self._last is not None
        denominator = 1e-9 + sum(value * value for value in self._last)
        for row, expected, actual in zip(self._weights, target, prediction):
            step = self._learning_rate * (expected - actual) / denominator
            for index, value in enumerate(self._last):
                row[index] += step * value


def _gain(
    *, observations: list[list[float]], actions: list[list[float]], condition: str,
    seed: int, reservoir: bool, reservoir_size: int,
) -> float:
    conditioned = _condition_actions(actions, condition=condition, seed=seed + 31_337)
    input_dim = len(observations[0]) + len(conditioned[0])
    model = (
        SparseEchoStateRegressor(
            input_dim=input_dim, output_dim=len(observations[0]),
            reservoir_size=reservoir_size, connectivity=0.15,
            spectral_scale=0.85, leak_rate=0.35, learning_rate=0.2,
            seed=seed, mechanism_id=f"embodied-comparison-{condition}",
        )
        if reservoir
        else _LinearNlms(input_dim, len(observations[0]))
    )
    split = min(max(32, int(0.7 * len(actions))), len(actions) - 16)
    for index in range(split):
        model.observe([*observations[index], *conditioned[index]])
        model.learn(observations[index + 1])
    losses: list[float] = []
    persistence: list[float] = []
    for index in range(split, len(actions) - 1):
        model.observe([*observations[index], *conditioned[index]])
        prediction = model.predict()
        values = prediction.value if hasattr(prediction, "value") else prediction
        target = observations[index + 1]
        losses.extend(_huber(target[i] - values[i]) for i in range(len(target)))
        persistence.extend(_huber(target[i] - observations[index][i]) for i in range(len(target)))
    return sum(persistence) / len(persistence) - sum(losses) / len(losses)


def run_embodied_model_comparison(
    seeds: Iterable[int] = (101, 127, 149),
    *, ticks: int = 320, physics_substeps_per_tick: int = 2, reservoir_size: int = 32,
) -> EmbodiedModelComparisonStudy:
    seed_list = tuple(seeds)
    if not seed_list:
        raise ValueError("seeds must not be empty")
    if ticks < 64 or physics_substeps_per_tick < 1:
        raise ValueError("ticks must be at least 64 and substeps must be positive")
    results: list[ModelComparisonSeedResult] = []
    for seed in seed_list:
        observations, actions = _trace(seed=seed, ticks=ticks, substeps=physics_substeps_per_tick)
        conditions = tuple(
            ModelComparisonCondition(
                condition=condition,
                reservoir_gain=_gain(
                    observations=observations, actions=actions, condition=condition,
                    seed=seed, reservoir=True, reservoir_size=reservoir_size,
                ),
                linear_gain=_gain(
                    observations=observations, actions=actions, condition=condition,
                    seed=seed, reservoir=False, reservoir_size=reservoir_size,
                ),
                reservoir_minus_linear=0.0,
            )
            for condition in ("causal", "action_shuffled", "no_action")
        )
        conditions = tuple(
            ModelComparisonCondition(
                item.condition, item.reservoir_gain, item.linear_gain,
                item.reservoir_gain - item.linear_gain,
            )
            for item in conditions
        )
        causal = next(item for item in conditions if item.condition == "causal")
        results.append(ModelComparisonSeedResult(
            seed=seed, conditions=conditions,
            recurrent_beats_linear_causally=causal.reservoir_gain > causal.linear_gain,
        ))
    return EmbodiedModelComparisonStudy(
        seeds=seed_list, ticks=ticks, physics_substeps_per_tick=physics_substeps_per_tick,
        reservoir_size=reservoir_size, per_seed=tuple(results),
        recurrent_beats_linear_all_seeds=all(item.recurrent_beats_linear_causally for item in results),
    )


__all__ = ["EmbodiedModelComparisonStudy", "run_embodied_model_comparison"]
