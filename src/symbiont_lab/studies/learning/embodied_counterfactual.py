"""Frozen, apparatus-side evaluation for paired opaque interventions.

This module does not create an organism or select candidates.  A caller must
provide a pre-defined candidate set and a training boundary.  Predictors are
fit on the baseline prefix, frozen, and then evaluated against a paired replay
and an intervention trajectory.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class OpaqueLagCandidate:
    source_effector: int
    target_receptor: int
    lag: int = 1

    def __post_init__(self) -> None:
        if self.source_effector < 0 or self.target_receptor < 0:
            raise ValueError("opaque channel indexes must be non-negative")
        if self.lag < 1:
            raise ValueError("lag must be positive")


@dataclass(frozen=True, slots=True)
class FrozenOpaqueLagPredictor:
    candidate: OpaqueLagCandidate
    slope: float


@dataclass(frozen=True, slots=True)
class FrozenCounterfactualResult:
    candidate: OpaqueLagCandidate
    normal_prediction_loss: float
    observed_intervention_delta: float
    predicted_intervention_delta: float
    intervention_prediction_error: float


def _validate_trace_lengths(
    actions: Sequence[Sequence[float]], observations: Sequence[Sequence[float]],
) -> None:
    if len(actions) != len(observations):
        raise ValueError("actions and observations must have equal length")
    if len(actions) < 2:
        raise ValueError("traces must contain at least two ticks")


def fit_frozen_lag_predictors(
    actions: Sequence[Sequence[float]],
    observations: Sequence[Sequence[float]],
    candidates: Sequence[OpaqueLagCandidate],
    *,
    train_end: int,
) -> tuple[FrozenOpaqueLagPredictor, ...]:
    """Fit fixed candidates on the baseline prefix and return frozen models."""
    _validate_trace_lengths(actions, observations)
    if not candidates:
        raise ValueError("candidates must not be empty")
    if train_end < 2 or train_end > len(actions):
        raise ValueError("train_end must leave at least two training ticks")

    predictors: list[FrozenOpaqueLagPredictor] = []
    for candidate in candidates:
        if candidate.lag >= train_end:
            raise ValueError("candidate lag must fit within the training prefix")
        pairs = [
            (float(actions[t - candidate.lag][candidate.source_effector]),
             float(observations[t][candidate.target_receptor]))
            for t in range(candidate.lag, train_end)
        ]
        denominator = sum(source * source for source, _ in pairs)
        slope = (
            sum(source * target for source, target in pairs) / denominator
            if denominator > 1e-12 else 0.0
        )
        predictors.append(FrozenOpaqueLagPredictor(candidate, slope))
    return tuple(predictors)


def evaluate_frozen_counterfactual(
    predictor: FrozenOpaqueLagPredictor,
    *,
    baseline_observations: Sequence[Sequence[float]],
    intervention_observations: Sequence[Sequence[float]],
    baseline_actions: Sequence[Sequence[float]],
    intervention_actions: Sequence[Sequence[float]],
    intervention_tick: int,
) -> FrozenCounterfactualResult:
    """Evaluate one frozen candidate on a paired intervention suffix."""
    _validate_trace_lengths(baseline_actions, baseline_observations)
    _validate_trace_lengths(intervention_actions, intervention_observations)
    if len(baseline_actions) != len(intervention_actions):
        raise ValueError("paired traces must have equal length")
    candidate = predictor.candidate
    if not 0 < intervention_tick < len(baseline_actions):
        raise ValueError("intervention_tick must be inside the trace")
    first = max(candidate.lag, intervention_tick)
    normal_losses: list[float] = []
    observed_deltas: list[float] = []
    predicted_deltas: list[float] = []
    for tick in range(first, len(baseline_actions)):
        source = baseline_actions[tick - candidate.lag][candidate.source_effector]
        target = baseline_observations[tick][candidate.target_receptor]
        normal_losses.append((float(target) - predictor.slope * float(source)) ** 2)
        if tick < intervention_tick:
            continue
        observed_delta = (
            float(intervention_observations[tick][candidate.target_receptor]) - float(target)
        )
        action_delta = (
            float(intervention_actions[tick - candidate.lag][candidate.source_effector]) - float(source)
        )
        observed_deltas.append(observed_delta)
        predicted_deltas.append(predictor.slope * action_delta)
    if not observed_deltas:
        raise ValueError("intervention suffix contains no evaluable ticks")
    observed = sum(observed_deltas) / len(observed_deltas)
    predicted = sum(predicted_deltas) / len(predicted_deltas)
    return FrozenCounterfactualResult(
        candidate=candidate,
        normal_prediction_loss=sum(normal_losses) / len(normal_losses),
        observed_intervention_delta=observed,
        predicted_intervention_delta=predicted,
        intervention_prediction_error=abs(observed - predicted),
    )


__all__ = [
    "FrozenCounterfactualResult",
    "FrozenOpaqueLagPredictor",
    "OpaqueLagCandidate",
    "evaluate_frozen_counterfactual",
    "fit_frozen_lag_predictors",
]
