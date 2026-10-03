"""Matched mechanism assay for GC-E7 model correction.

The assay presents an opaque candidate whose first generated prediction is
wrong.  A factual outcome contradicts that hypothesis, the model adapter
learns the changed outcome, and the next generated prediction is evaluated.
The evaluator owns the factual outcome and the model's explicit learning
hook; generated states never enter the factual evidence path.

This is a correction-mechanism gate, not evidence of general intelligence or
external-world utility.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from symbiont.cognition.generative import (
    GeneratedFeature,
    GeneratedProposal,
    GenerativeContext,
    GenerativeMode,
    GenerativeOperation,
    GenerativeState,
    HypothesisStatus,
    ResidentGenerativeCognition,
)

_ACTION = "opaque.regime"
_OLD_OUTCOME = "opaque.outcome.old"
_NEW_OUTCOME = "opaque.outcome.new"


class _AdaptiveOpaqueModel:
    """Small model adapter with an explicit factual-learning boundary."""

    model_id = "model.adaptive-opaque"

    def __init__(self) -> None:
        self._outcome = _OLD_OUTCOME

    @property
    def outcome(self) -> str:
        return self._outcome

    def supports(self, operation: GenerativeOperation, state: GenerativeState) -> bool:
        return operation is GenerativeOperation.PREDICT

    def generate(
        self,
        *,
        state: GenerativeState,
        operation: GenerativeOperation,
        context: GenerativeContext,
    ) -> tuple[GeneratedProposal, ...]:
        return (
            GeneratedProposal(
                features=(
                    GeneratedFeature(
                        self._outcome,
                        None,
                        0.8,
                        self.model_id,
                    ),
                ),
                predicted_outcomes=(self._outcome,),
                uncertainty=0.5,
                coherence=0.9,
                model_id=self.model_id,
                support_refs=context.references,
            ),
        )

    def learn_from_factual_outcome(self, outcome: str) -> None:
        """Apply an evaluator-owned factual correction to the model adapter."""
        if outcome not in {_OLD_OUTCOME, _NEW_OUTCOME}:
            raise ValueError("unexpected opaque factual outcome")
        self._outcome = outcome


def _prediction(resident: ResidentGenerativeCognition) -> str:
    if resident.last_rollout is None or not resident.last_rollout.transitions:
        return ""
    return resident.last_rollout.transitions[-1].predicted_outcomes[0]


def _active_hypothesis(resident: ResidentGenerativeCognition):
    return next(
        (
            hypothesis
            for hypothesis in resident.hypotheses.values()
            if hypothesis.status in {HypothesisStatus.PREDICTED, HypothesisStatus.HYPOTHESIZED}
        ),
        None,
    )


@dataclass(frozen=True, slots=True)
class GenerativeModelCorrectionTrial:
    seed: int
    initial_prediction: str
    factual_outcome: str
    corrected_prediction: str
    initial_hypothesis_contradicted: bool
    corrected_hypothesis_supported: bool
    reconciliation_count: int
    contradicted_hypothesis_count: int
    factual_contamination_count: int
    agenda_contamination_count: int
    generated_origins_non_observed: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GenerativeModelCorrectionStudy:
    seeds: tuple[int, ...]
    trials: tuple[GenerativeModelCorrectionTrial, ...]
    contradiction_rate: float
    corrected_prediction_rate: float
    all_factual_contamination_free: bool
    all_agenda_contamination_free: bool
    all_generated_origins_non_observed: bool
    passed: bool

    def as_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "trials": [trial.as_dict() for trial in self.trials],
        }


def run_generative_model_correction_study(
    *,
    seeds: Iterable[int] = (101, 127, 149),
) -> GenerativeModelCorrectionStudy:
    normalized = tuple(seeds)
    if not normalized or len(normalized) > 16 or len(set(normalized)) != len(normalized):
        raise ValueError("seeds must contain between 1 and 16 unique integers")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in normalized):
        raise ValueError("seeds must be integers")

    trials: list[GenerativeModelCorrectionTrial] = []
    for seed in normalized:
        model = _AdaptiveOpaqueModel()
        resident = ResidentGenerativeCognition(organism_id=f"gc-e7-{seed}")
        resident.register_model(model)

        resident.step(
            tick=seed,
            cognition=None,
            prospective_candidate_ids=(_ACTION,),
            mode=GenerativeMode.OFFLINE,
        )
        initial_prediction = _prediction(resident)
        initial_hypothesis = _active_hypothesis(resident)

        reconciled_before_learning = resident.note_factual_outcome(
            action_id=_ACTION,
            outcome_tokens=(_NEW_OUTCOME,),
            evidence_refs=(f"evaluator.fact.{seed}.1",),
        )
        model.learn_from_factual_outcome(_NEW_OUTCOME)
        resident.step(
            tick=seed + 1,
            cognition=None,
            prospective_candidate_ids=(_ACTION,),
            mode=GenerativeMode.OFFLINE,
        )
        corrected_prediction = _prediction(resident)
        corrected_hypothesis = _active_hypothesis(resident)
        reconciled_after_learning = resident.note_factual_outcome(
            action_id=_ACTION,
            outcome_tokens=(_NEW_OUTCOME,),
            evidence_refs=(f"evaluator.fact.{seed}.2",),
        )
        origins_safe = all(
            state.origin.value != "observed"
            for state in (
                *(resident.last_workspace.states if resident.last_workspace is not None else ()),
            )
        )
        trials.append(
            GenerativeModelCorrectionTrial(
                seed=seed,
                initial_prediction=initial_prediction,
                factual_outcome=_NEW_OUTCOME,
                corrected_prediction=corrected_prediction,
                initial_hypothesis_contradicted=(
                    initial_prediction == _OLD_OUTCOME
                    and initial_hypothesis is not None
                    and initial_hypothesis.status is HypothesisStatus.CONTRADICTED
                ),
                corrected_hypothesis_supported=(
                    corrected_prediction == _NEW_OUTCOME
                    and corrected_hypothesis is not None
                    and corrected_hypothesis.status is HypothesisStatus.SUPPORTED
                ),
                reconciliation_count=resident.reconciliation_count,
                contradicted_hypothesis_count=resident.contradicted_hypothesis_count,
                factual_contamination_count=resident.factual_contamination_count,
                agenda_contamination_count=resident.agenda.agenda_contamination_count,
                generated_origins_non_observed=(
                    origins_safe
                    and reconciled_before_learning == 1
                    and reconciled_after_learning == 1
                ),
            )
        )

    count = len(trials)
    contradiction_rate = sum(item.initial_hypothesis_contradicted for item in trials) / count
    corrected_prediction_rate = sum(item.corrected_hypothesis_supported for item in trials) / count
    factual_safe = all(item.factual_contamination_count == 0 for item in trials)
    agenda_safe = all(item.agenda_contamination_count == 0 for item in trials)
    origins_safe = all(item.generated_origins_non_observed for item in trials)
    passed = (
        contradiction_rate == 1.0
        and corrected_prediction_rate == 1.0
        and factual_safe
        and agenda_safe
        and origins_safe
        and all(item.reconciliation_count == 2 for item in trials)
        and all(item.contradicted_hypothesis_count == 1 for item in trials)
    )
    return GenerativeModelCorrectionStudy(
        seeds=normalized,
        trials=tuple(trials),
        contradiction_rate=contradiction_rate,
        corrected_prediction_rate=corrected_prediction_rate,
        all_factual_contamination_free=factual_safe,
        all_agenda_contamination_free=agenda_safe,
        all_generated_origins_non_observed=origins_safe,
        passed=passed,
    )


__all__ = [
    "GenerativeModelCorrectionStudy",
    "GenerativeModelCorrectionTrial",
    "run_generative_model_correction_study",
]
