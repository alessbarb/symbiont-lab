from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from typing import Iterable

from symbiont_lab.modeling import SparseEchoStateRegressor


def _huber(error: float) -> float:
    magnitude = abs(error)
    return 0.5 * error * error if magnitude <= 1.0 else magnitude - 0.5


@dataclass(frozen=True, slots=True)
class ContinuousCausalCondition:
    condition: str
    test_loss: float
    persistence_loss: float
    gain_over_persistence: float


@dataclass(frozen=True, slots=True)
class ContinuousCausalSeedResult:
    seed: int
    causal: ContinuousCausalCondition
    action_shuffled: ContinuousCausalCondition
    no_action: ContinuousCausalCondition
    causal_margin_over_best_control: float
    causal_beats_controls: bool


@dataclass(frozen=True, slots=True)
class ContinuousTemporalControlsStudy:
    seeds: tuple[int, ...]
    ticks: int
    per_seed: tuple[ContinuousCausalSeedResult, ...]
    all_seeds_causal_beats_controls: bool
    mean_causal_margin: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _trajectory(seed: int, ticks: int) -> tuple[list[float], list[float]]:
    rng = random.Random(seed)
    states = [0.15]
    actions: list[float] = []
    for _ in range(ticks):
        action = -1.0 if rng.random() < 0.5 else 1.0
        next_state = (
            0.58 * states[-1]
            + 0.34 * action
            + rng.gauss(0.0, 0.04)
        )
        next_state = max(-0.98, min(0.98, next_state))
        actions.append(action)
        states.append(next_state)
    return states, actions


def _condition_actions(
    actions: list[float],
    *,
    condition: str,
    seed: int,
) -> list[float]:
    if condition == "causal":
        return list(actions)
    if condition == "no_action":
        return [0.0] * len(actions)
    if condition == "action_shuffled":
        shuffled = list(actions)
        rng = random.Random(seed)
        rng.shuffle(shuffled)
        if len(shuffled) > 1 and shuffled == actions:
            shuffled = shuffled[1:] + shuffled[:1]
        return shuffled
    raise ValueError("unknown condition")


def _run_condition(
    *,
    seed: int,
    states: list[float],
    actions: list[float],
    condition: str,
) -> ContinuousCausalCondition:
    conditioned_actions = _condition_actions(
        actions,
        condition=condition,
        seed=seed + 31_337,
    )
    model = SparseEchoStateRegressor(
        input_dim=2,
        output_dim=1,
        reservoir_size=64,
        connectivity=0.1,
        spectral_scale=0.85,
        leak_rate=0.35,
        learning_rate=0.4,
        seed=seed,
        mechanism_id=f"esn-nlms-{condition}",
    )

    split = max(64, int(0.7 * len(actions)))
    split = min(split, len(actions) - 32)

    for index in range(split):
        model.observe((states[index], conditioned_actions[index]))
        model.learn((states[index + 1],))

    losses: list[float] = []
    persistence_losses: list[float] = []
    for index in range(split, len(actions)):
        model.observe((states[index], conditioned_actions[index]))
        prediction = model.predict()
        if prediction is None:
            raise RuntimeError("ESN produced no held-out prediction")
        target = states[index + 1]
        losses.append(_huber(target - prediction.value[0]))
        persistence_losses.append(_huber(target - states[index]))

    loss = sum(losses) / len(losses)
    persistence = sum(persistence_losses) / len(persistence_losses)
    return ContinuousCausalCondition(
        condition=condition,
        test_loss=loss,
        persistence_loss=persistence,
        gain_over_persistence=persistence - loss,
    )


def run_continuous_temporal_controls(
    seeds: Iterable[int] = (101, 127, 149),
    *,
    ticks: int = 320,
) -> ContinuousTemporalControlsStudy:
    seed_list = tuple(seeds)
    if not seed_list:
        raise ValueError("seeds must not be empty")
    if isinstance(ticks, bool) or not isinstance(ticks, int) or ticks < 128:
        raise ValueError("ticks must be at least 128")

    results: list[ContinuousCausalSeedResult] = []
    for seed in seed_list:
        states, actions = _trajectory(seed, ticks)
        causal = _run_condition(
            seed=seed,
            states=states,
            actions=actions,
            condition="causal",
        )
        shuffled = _run_condition(
            seed=seed,
            states=states,
            actions=actions,
            condition="action_shuffled",
        )
        no_action = _run_condition(
            seed=seed,
            states=states,
            actions=actions,
            condition="no_action",
        )
        best_control = max(
            shuffled.gain_over_persistence,
            no_action.gain_over_persistence,
        )
        margin = causal.gain_over_persistence - best_control
        results.append(
            ContinuousCausalSeedResult(
                seed=seed,
                causal=causal,
                action_shuffled=shuffled,
                no_action=no_action,
                causal_margin_over_best_control=margin,
                causal_beats_controls=(
                    causal.gain_over_persistence
                    > shuffled.gain_over_persistence
                    and causal.gain_over_persistence
                    > no_action.gain_over_persistence
                ),
            )
        )

    return ContinuousTemporalControlsStudy(
        seeds=seed_list,
        ticks=ticks,
        per_seed=tuple(results),
        all_seeds_causal_beats_controls=all(
            result.causal_beats_controls for result in results
        ),
        mean_causal_margin=(
            sum(result.causal_margin_over_best_control for result in results)
            / len(results)
        ),
    )


__all__ = [
    "ContinuousCausalCondition",
    "ContinuousCausalSeedResult",
    "ContinuousTemporalControlsStudy",
    "run_continuous_temporal_controls",
]
