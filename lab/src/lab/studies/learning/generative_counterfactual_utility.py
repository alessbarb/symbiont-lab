"""Matched observer-only assay for GC-E3 hypothesis discrimination.

The assay gives two opaque probes identical pragmatic value.  Two internal
models disagree about the outcome of one probe and agree about the other.  A
Generative Cognition treatment can therefore use internal discrimination as a
tie-break; the no-GC control receives the same candidates, predictions and
factual value ledger but no epistemic provider.

This is a mechanism assay, not evidence of embodied intelligence.  The hidden
``discriminating_probe`` label belongs only to the evaluator and is used to
score the choice after deliberation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from symbiont.agency import (
    CounterfactualPrediction,
    OutcomeValueLedger,
    ProspectiveAgency,
    ProspectiveCandidate,
    ProspectivePolicy,
)
from symbiont.cognition.generative import (
    GeneratedFeature,
    GeneratedProposal,
    GenerativeContext,
    GenerativeMode,
    GenerativeOperation,
    GenerativeState,
    ResidentGenerativeCognition,
)

_DISCRIMINATING = "probe.discriminating"
_BASELINE = "probe.baseline"
_CANDIDATES = (_DISCRIMINATING, _BASELINE)


class _CompetingHypothesisModel:
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id

    def supports(self, operation: GenerativeOperation, state: GenerativeState) -> bool:
        return operation is GenerativeOperation.BRANCH

    def generate(
        self,
        *,
        state: GenerativeState,
        operation: GenerativeOperation,
        context: GenerativeContext,
    ) -> tuple[GeneratedProposal, ...]:
        if context.tokens == (_DISCRIMINATING,):
            outcome = "outcome.h1" if self.model_id == "model.h1" else "outcome.h2"
        else:
            outcome = "outcome.agreed"
        return (
            GeneratedProposal(
                features=(GeneratedFeature(outcome, None, 0.8, self.model_id),),
                predicted_outcomes=(outcome,),
                uncertainty=0.2,
                coherence=0.9,
                model_id=self.model_id,
                support_refs=context.references,
            ),
        )


@dataclass(frozen=True, slots=True)
class GenerativeCounterfactualUtilitySeedResult:
    seed: int
    treatment_selected: str | None
    control_selected: str | None
    treatment_discrimination: float
    control_discrimination: float
    treatment_factual_contamination: int
    control_factual_contamination: int

    @property
    def treatment_selected_discriminating_probe(self) -> bool:
        return self.treatment_selected == _DISCRIMINATING

    @property
    def control_selected_baseline_probe(self) -> bool:
        return self.control_selected == _BASELINE

    @property
    def control_selected_discriminating_probe(self) -> bool:
        return self.control_selected == _DISCRIMINATING

    def as_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "treatment_selected_discriminating_probe": self.treatment_selected_discriminating_probe,
            "control_selected_baseline_probe": self.control_selected_baseline_probe,
            "control_selected_discriminating_probe": self.control_selected_discriminating_probe,
        }


@dataclass(frozen=True, slots=True)
class GenerativeCounterfactualUtilityStudy:
    seeds: tuple[int, ...]
    results: tuple[GenerativeCounterfactualUtilitySeedResult, ...]
    treatment_selection_rate: float
    control_baseline_selection_rate: float
    control_discriminating_selection_rate: float
    mean_discrimination_gain: float
    all_factual_contamination_free: bool
    passed: bool

    def as_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "results": [result.as_dict() for result in self.results],
        }


def _resident(*, seed: int, candidate: str) -> ResidentGenerativeCognition:
    resident = ResidentGenerativeCognition(organism_id=f"gc-e3-{seed}-{candidate}")
    resident.register_model(_CompetingHypothesisModel("model.h1"))
    resident.register_model(_CompetingHypothesisModel("model.h2"))
    resident.step(
        tick=1,
        cognition=None,
        prospective_candidate_ids=(candidate,),
        mode=GenerativeMode.IDLE,
    )
    return resident


def _ledger() -> OutcomeValueLedger:
    ledger = OutcomeValueLedger()
    for tick in range(8):
        for outcome in ("outcome.h1", "outcome.h2", "outcome.agreed"):
            # Equal observed value makes the choice epistemic rather than
            # pragmatic. These are evaluator-owned factual training fixtures.
            ledger.observe(outcome, 0.2, tick=tick)
    return ledger


def _agency(*, seed: int) -> ProspectiveAgency:
    organism_id = f"gc-e3-agency-{seed}"
    return ProspectiveAgency(
        organism_id=organism_id,
        outcome_value_ledger=_ledger(),
        policy=ProspectivePolicy(
            organism_id=organism_id,
            min_model_confidence=0.5,
            min_value_samples=4,
            decision_margin=0.0,
        ),
        query_budget=4,
    )


def _deliberate(
    *,
    agency: ProspectiveAgency,
    epistemic_value_provider=None,
    tick: int,
):
    def predictor(action_id: str, context_tokens: tuple[str, ...]) -> CounterfactualPrediction:
        outcome = "outcome.h1" if action_id == _DISCRIMINATING else "outcome.agreed"
        return CounterfactualPrediction(
            action_id=action_id,
            predicted_outcome=outcome,
            confidence_class=7,
        )

    return agency.deliberate(
        tick=tick,
        candidates=tuple(
            ProspectiveCandidate(action_id=item, family="probe") for item in _CANDIDATES
        ),
        context_tokens=("context.opaque",),
        homeostatic_deviation=0.5,
        predictor=predictor,
        epistemic_value_provider=epistemic_value_provider,
    )


def run_generative_counterfactual_utility_study(
    *,
    seeds: Iterable[int] = (101, 127, 149),
) -> GenerativeCounterfactualUtilityStudy:
    normalized = tuple(seeds)
    if not normalized or len(normalized) > 16 or len(set(normalized)) != len(normalized):
        raise ValueError("seeds must contain between 1 and 16 unique integers")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in normalized):
        raise ValueError("seeds must be integers")

    results: list[GenerativeCounterfactualUtilitySeedResult] = []
    for seed in normalized:
        discriminating = _resident(seed=seed, candidate=_DISCRIMINATING)
        baseline = _resident(seed=seed, candidate=_BASELINE)
        treatment_scores = {
            _DISCRIMINATING: discriminating.epistemic_value_for(_DISCRIMINATING).comparison_score,
            _BASELINE: baseline.epistemic_value_for(_BASELINE).comparison_score,
        }
        treatment = _deliberate(
            agency=_agency(seed=seed),
            epistemic_value_provider=treatment_scores.get,
            tick=seed,
        )
        control = _deliberate(agency=_agency(seed=seed), tick=seed)
        results.append(
            GenerativeCounterfactualUtilitySeedResult(
                seed=seed,
                treatment_selected=treatment.candidate_id,
                control_selected=control.candidate_id,
                treatment_discrimination=(
                    discriminating.epistemic_value_for(
                        _DISCRIMINATING
                    ).expected_hypothesis_discrimination
                ),
                control_discrimination=baseline.epistemic_value_for(
                    _BASELINE
                ).expected_hypothesis_discrimination,
                treatment_factual_contamination=discriminating.factual_contamination_count,
                control_factual_contamination=baseline.factual_contamination_count,
            )
        )

    count = len(results)
    treatment_rate = sum(item.treatment_selected_discriminating_probe for item in results) / count
    control_rate = sum(item.control_selected_baseline_probe for item in results) / count
    control_discriminating_rate = (
        sum(item.control_selected_discriminating_probe for item in results) / count
    )
    gain = (
        sum(item.treatment_discrimination - item.control_discrimination for item in results) / count
    )
    contamination_free = all(
        item.treatment_factual_contamination == 0 and item.control_factual_contamination == 0
        for item in results
    )
    return GenerativeCounterfactualUtilityStudy(
        seeds=normalized,
        results=tuple(results),
        treatment_selection_rate=treatment_rate,
        control_baseline_selection_rate=control_rate,
        control_discriminating_selection_rate=control_discriminating_rate,
        mean_discrimination_gain=gain,
        all_factual_contamination_free=contamination_free,
        passed=(
            treatment_rate == 1.0
            and treatment_rate > control_discriminating_rate
            and gain > 0.0
            and contamination_free
        ),
    )


__all__ = [
    "GenerativeCounterfactualUtilitySeedResult",
    "GenerativeCounterfactualUtilityStudy",
    "run_generative_counterfactual_utility_study",
]
