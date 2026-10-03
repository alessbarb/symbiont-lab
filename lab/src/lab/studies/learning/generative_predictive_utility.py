"""Matched mechanism assay for bounded multi-step predictive utility.

The assay compares persistence, one-step rollout and multi-step rollout on an
opaque deterministic sequence.  The evaluator owns the hidden target token;
the generative model receives only the current generated state and advances it
one step at a time.  This is a substrate utility gate, not evidence of broad
intelligence or external-world generalisation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from symbiont.cognition.generative import (
    EpistemicOrigin,
    GeneratedFeature,
    GeneratedProposal,
    GenerativeBudget,
    GenerativeContext,
    GenerativeMode,
    GenerativeModelRegistry,
    GenerativeOperation,
    GenerativeState,
    GenerativeWorkspace,
    RolloutEngine,
    new_episode,
)


class _OpaqueSequenceModel:
    model_id = "model.sequence"

    def supports(self, operation: GenerativeOperation, state: GenerativeState) -> bool:
        return operation is GenerativeOperation.PREDICT

    def generate(
        self,
        *,
        state: GenerativeState,
        operation: GenerativeOperation,
        context: GenerativeContext,
    ) -> tuple[GeneratedProposal, ...]:
        next_token = f"opaque.signal.{state.depth + 1}"
        return (
            GeneratedProposal(
                features=(GeneratedFeature(next_token, None, 0.9, self.model_id),),
                predicted_outcomes=(next_token,),
                uncertainty=0.2 + min(0.05 * state.depth, 0.5),
                coherence=0.9,
                model_id=self.model_id,
                support_refs=context.references,
            ),
        )


@dataclass(frozen=True, slots=True)
class GenerativePredictiveUtilityTrial:
    seed: int
    horizon: int
    target_token: str
    persistence_token: str
    one_step_token: str
    multi_step_token: str
    persistence_correct: bool
    one_step_correct: bool
    multi_step_correct: bool
    multi_step_termination: str
    all_generated_origins_non_observed: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GenerativePredictiveUtilityStudy:
    seeds: tuple[int, ...]
    horizons: tuple[int, ...]
    trials: tuple[GenerativePredictiveUtilityTrial, ...]
    persistence_accuracy: float
    one_step_accuracy: float
    multi_step_accuracy: float
    all_generated_origins_non_observed: bool
    passed: bool

    def as_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "trials": [trial.as_dict() for trial in self.trials],
        }


def _target_token(horizon: int) -> str:
    """Evaluator-owned hidden target; it is not passed to the model."""
    return f"opaque.signal.{horizon}"


def _rollout_token(*, seed: int, max_depth: int) -> tuple[str, str, bool]:
    episode = new_episode(
        episode_id=f"gc-e1.{seed}.{max_depth}",
        organism_id=f"gc-e1-{seed}",
        root_state_id="root",
        mode=GenerativeMode.OFFLINE,
        symbiont_tick=seed,
        generative_tick=0,
    )
    workspace = GenerativeWorkspace(
        episode=episode,
        budget=GenerativeBudget(max_depth=max_depth, max_states=max_depth + 1),
    )
    workspace.add_state(
        GenerativeState(
            state_id="root",
            episode_id=episode.episode_id,
            origin=EpistemicOrigin.INFERRED,
            parent_state_id=None,
            depth=0,
            features=(GeneratedFeature("opaque.signal.0", None, 1.0),),
            active_concept_ids=(),
            relation_refs=(),
            source_episode_ids=(),
            source_model_ids=(),
            source_state_ids=(),
            uncertainty=0.1,
            coherence=1.0,
            generative_tick=0,
        )
    )
    registry = GenerativeModelRegistry()
    registry.register(_OpaqueSequenceModel())
    result = RolloutEngine(registry=registry, workspace=workspace).rollout(
        root_state_id="root",
        context=GenerativeContext(tokens=("opaque.sequence",), references=("opaque.sequence",)),
        max_depth=max_depth,
    )
    if max_depth == 0:
        token = "opaque.signal.0"
    elif result.states:
        token = result.states[-1].features[0].token
    else:
        token = ""
    origins_safe = all(state.origin is not EpistemicOrigin.OBSERVED for state in workspace.states)
    return token, result.termination.value, origins_safe


def run_generative_predictive_utility_study(
    *,
    seeds: Iterable[int] = (101, 127, 149),
    horizons: Iterable[int] = (1, 2, 4),
) -> GenerativePredictiveUtilityStudy:
    normalized_seeds = tuple(seeds)
    normalized_horizons = tuple(horizons)
    if (
        not normalized_seeds
        or len(normalized_seeds) > 16
        or len(set(normalized_seeds)) != len(normalized_seeds)
    ):
        raise ValueError("seeds must contain between 1 and 16 unique integers")
    if any(isinstance(item, bool) or not isinstance(item, int) for item in normalized_seeds):
        raise ValueError("seeds must be integers")
    if (
        not normalized_horizons
        or len(normalized_horizons) > 8
        or len(set(normalized_horizons)) != len(normalized_horizons)
    ):
        raise ValueError("horizons must contain between 1 and 8 unique integers")
    if any(
        isinstance(item, bool) or not isinstance(item, int) or item < 1
        for item in normalized_horizons
    ):
        raise ValueError("horizons must be positive integers")

    trials: list[GenerativePredictiveUtilityTrial] = []
    for seed in normalized_seeds:
        for horizon in normalized_horizons:
            target = _target_token(horizon)
            persistence = "opaque.signal.0"
            one_step, one_step_termination, one_step_safe = _rollout_token(seed=seed, max_depth=1)
            multi_step, termination, multi_step_safe = _rollout_token(seed=seed, max_depth=horizon)
            trials.append(
                GenerativePredictiveUtilityTrial(
                    seed=seed,
                    horizon=horizon,
                    target_token=target,
                    persistence_token=persistence,
                    one_step_token=one_step,
                    multi_step_token=multi_step,
                    persistence_correct=persistence == target,
                    one_step_correct=one_step == target,
                    multi_step_correct=multi_step == target,
                    multi_step_termination=termination,
                    all_generated_origins_non_observed=one_step_safe and multi_step_safe,
                )
            )

    count = len(trials)
    persistence_accuracy = sum(item.persistence_correct for item in trials) / count
    one_step_accuracy = sum(item.one_step_correct for item in trials) / count
    multi_step_accuracy = sum(item.multi_step_correct for item in trials) / count
    origins_safe = all(item.all_generated_origins_non_observed for item in trials)
    passed = (
        multi_step_accuracy == 1.0
        and multi_step_accuracy > persistence_accuracy
        and multi_step_accuracy > one_step_accuracy
        and origins_safe
        and all(item.multi_step_termination == "completed" for item in trials)
    )
    return GenerativePredictiveUtilityStudy(
        seeds=normalized_seeds,
        horizons=normalized_horizons,
        trials=tuple(trials),
        persistence_accuracy=persistence_accuracy,
        one_step_accuracy=one_step_accuracy,
        multi_step_accuracy=multi_step_accuracy,
        all_generated_origins_non_observed=origins_safe,
        passed=passed,
    )


__all__ = [
    "GenerativePredictiveUtilityStudy",
    "GenerativePredictiveUtilityTrial",
    "run_generative_predictive_utility_study",
]
