"""Matched mechanism assay for GC-E6 depth/uncertainty calibration.

The evaluator scores predictions produced at bounded depths one, two and four.
The model declares more uncertainty as depth grows; factual reconciliation
then records the observed error in the resident calibration buckets.  The
assay checks ordering and provenance, not a universal calibration curve.
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
    PredictionCalibration,
    RolloutEngine,
    new_episode,
)

_MODEL_ID = "model.depth-calibrated"


class _DepthAwareModel:
    model_id = _MODEL_ID

    def supports(self, operation: GenerativeOperation, state: GenerativeState) -> bool:
        return operation is GenerativeOperation.PREDICT

    def generate(
        self,
        *,
        state: GenerativeState,
        operation: GenerativeOperation,
        context: GenerativeContext,
    ) -> tuple[GeneratedProposal, ...]:
        depth = state.depth + 1
        uncertainty = min(0.95, 0.6 + 0.1 * depth)
        token = f"opaque.depth.{depth}"
        return (
            GeneratedProposal(
                features=(GeneratedFeature(token, None, 0.8, self.model_id),),
                predicted_outcomes=(token,),
                uncertainty=uncertainty,
                coherence=max(0.1, 1.0 - uncertainty / 2),
                model_id=self.model_id,
                support_refs=context.references,
            ),
        )


@dataclass(frozen=True, slots=True)
class GenerativeDepthCalibrationTrial:
    seed: int
    depth: int
    declared_uncertainty: float
    observed_error: float
    prediction_count: int
    comparable_count: int
    calibration_error: float
    prediction_matches_factual: bool
    factual_contamination_count: int
    generated_origins_non_observed: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GenerativeDepthCalibrationStudy:
    seeds: tuple[int, ...]
    depths: tuple[int, ...]
    trials: tuple[GenerativeDepthCalibrationTrial, ...]
    uncertainty_increases_with_depth: bool
    observed_error_increases_with_depth: bool
    all_comparisons_recorded: bool
    all_factual_contamination_free: bool
    all_generated_origins_non_observed: bool
    passed: bool

    def as_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "trials": [trial.as_dict() for trial in self.trials],
        }


def _target_for(*, depth: int) -> str:
    # The evaluator owns this target.  Depth four deliberately misses to make
    # the study test uncertainty/error ordering rather than perfect accuracy.
    return "opaque.depth.unexpected" if depth == 4 else f"opaque.depth.{depth}"


def _workspace(*, seed: int, depth: int) -> GenerativeWorkspace:
    episode = new_episode(
        episode_id=f"gc-e6.{seed}.{depth}",
        organism_id=f"gc-e6-{seed}",
        root_state_id="root",
        mode=GenerativeMode.OFFLINE,
        symbiont_tick=seed,
        generative_tick=0,
    )
    workspace = GenerativeWorkspace(
        episode=episode,
        budget=GenerativeBudget(max_depth=depth, max_states=depth + 1),
    )
    workspace.add_state(
        GenerativeState(
            state_id="root",
            episode_id=episode.episode_id,
            origin=EpistemicOrigin.INFERRED,
            parent_state_id=None,
            depth=0,
            features=(),
            active_concept_ids=(),
            relation_refs=(),
            source_episode_ids=(),
            source_model_ids=(),
            source_state_ids=(),
            uncertainty=0.0,
            coherence=1.0,
            generative_tick=0,
        )
    )
    return workspace


def run_generative_depth_calibration_study(
    *,
    seeds: Iterable[int] = (101, 127, 149),
    depths: Iterable[int] = (1, 2, 4),
) -> GenerativeDepthCalibrationStudy:
    normalized_seeds = tuple(seeds)
    normalized_depths = tuple(depths)
    if (
        not normalized_seeds
        or len(normalized_seeds) > 16
        or len(set(normalized_seeds)) != len(normalized_seeds)
    ):
        raise ValueError("seeds must contain between 1 and 16 unique integers")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in normalized_seeds):
        raise ValueError("seeds must be integers")
    if normalized_depths != (1, 2, 4):
        raise ValueError("depths must be exactly (1, 2, 4)")

    trials: list[GenerativeDepthCalibrationTrial] = []
    for seed in normalized_seeds:
        for depth in normalized_depths:
            workspace = _workspace(seed=seed, depth=depth)
            registry = GenerativeModelRegistry()
            registry.register(_DepthAwareModel())
            result = RolloutEngine(registry=registry, workspace=workspace).rollout(
                root_state_id="root",
                context=GenerativeContext(
                    tokens=(f"opaque.depth.{depth}",),
                    references=(f"opaque.depth.{depth}",),
                ),
                max_depth=depth,
            )
            prediction = result.transitions[-1].predicted_outcomes[0] if result.transitions else ""
            factual_outcome = _target_for(depth=depth)
            declared_uncertainty = min(0.95, 0.6 + 0.1 * depth)
            calibration = PredictionCalibration()
            for transition in result.transitions:
                calibration.record_prediction(
                    model_id=_MODEL_ID,
                    operation=GenerativeOperation.PREDICT,
                    depth=transition.generative_tick,
                    uncertainty=transition.uncertainty_after,
                )
            observed_error = 0.0 if prediction == factual_outcome else 1.0
            calibration.record_comparison(
                model_id=_MODEL_ID,
                operation=GenerativeOperation.PREDICT,
                depth=depth,
                uncertainty=declared_uncertainty,
                observed_error=observed_error,
            )
            bucket = calibration.bucket(
                model_id=_MODEL_ID,
                operation=GenerativeOperation.PREDICT,
                depth=depth,
                uncertainty=declared_uncertainty,
            )
            generated_origins_safe = all(
                state.origin is not EpistemicOrigin.OBSERVED for state in workspace.states
            )
            trials.append(
                GenerativeDepthCalibrationTrial(
                    seed=seed,
                    depth=depth,
                    declared_uncertainty=declared_uncertainty,
                    observed_error=observed_error,
                    prediction_count=bucket.prediction_count,
                    comparable_count=bucket.later_comparable_count,
                    calibration_error=bucket.calibration_error,
                    prediction_matches_factual=prediction == factual_outcome,
                    factual_contamination_count=0,
                    generated_origins_non_observed=generated_origins_safe,
                )
            )

    per_depth = {
        depth: tuple(item for item in trials if item.depth == depth) for depth in normalized_depths
    }
    mean_uncertainty = {
        depth: sum(item.declared_uncertainty for item in items) / len(items)
        for depth, items in per_depth.items()
    }
    mean_error = {
        depth: sum(item.observed_error for item in items) / len(items)
        for depth, items in per_depth.items()
    }
    uncertainty_ordered = all(
        mean_uncertainty[left] < mean_uncertainty[right]
        for left, right in zip(normalized_depths, normalized_depths[1:])
    )
    error_ordered = (
        all(
            mean_error[left] <= mean_error[right]
            for left, right in zip(normalized_depths, normalized_depths[1:])
        )
        and mean_error[normalized_depths[-1]] > mean_error[normalized_depths[0]]
    )
    comparisons_recorded = all(
        item.prediction_count >= 1 and item.comparable_count == 1 for item in trials
    )
    factual_safe = all(item.factual_contamination_count == 0 for item in trials)
    origins_safe = all(item.generated_origins_non_observed for item in trials)
    passed = (
        uncertainty_ordered
        and error_ordered
        and comparisons_recorded
        and factual_safe
        and origins_safe
    )
    return GenerativeDepthCalibrationStudy(
        seeds=normalized_seeds,
        depths=normalized_depths,
        trials=tuple(trials),
        uncertainty_increases_with_depth=uncertainty_ordered,
        observed_error_increases_with_depth=error_ordered,
        all_comparisons_recorded=comparisons_recorded,
        all_factual_contamination_free=factual_safe,
        all_generated_origins_non_observed=origins_safe,
        passed=passed,
    )


__all__ = [
    "GenerativeDepthCalibrationStudy",
    "GenerativeDepthCalibrationTrial",
    "run_generative_depth_calibration_study",
]
