"""Matched mechanism assay for GC-E2 bounded planning utility.

Two opaque actions share the same immediate predicted intermediate state.  Only
the two-step treatment can distinguish their terminal generated outcomes and
uses that information to select the evaluator-owned safe action.  The control
uses one-step prospection and therefore follows the stable candidate order.

The evaluator scores the selected action after deliberation.  It never enters
the organism's context, generated workspace or factual ledger.
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

_RISKY = "opaque.action.risky"
_SAFE = "opaque.action.safe"
_ACTIONS = (_RISKY, _SAFE)
_INTERMEDIATE = "opaque.intermediate"
_GOOD = "opaque.terminal.good"
_BAD = "opaque.terminal.bad"


class _OpaquePlanningModel:
    model_id = "model.planning"

    def supports(self, operation: GenerativeOperation, state: GenerativeState) -> bool:
        return operation is GenerativeOperation.PREDICT

    def generate(
        self,
        *,
        state: GenerativeState,
        operation: GenerativeOperation,
        context: GenerativeContext,
    ) -> tuple[GeneratedProposal, ...]:
        action = context.tokens[0]
        token = _INTERMEDIATE if state.depth == 0 else (_GOOD if action == _SAFE else _BAD)
        return (
            GeneratedProposal(
                features=(GeneratedFeature(token, None, 0.8, self.model_id),),
                predicted_outcomes=(token,),
                uncertainty=0.2 if state.depth else 0.6,
                coherence=0.9,
                model_id=self.model_id,
                support_refs=(),
            ),
        )


def _ledger() -> OutcomeValueLedger:
    ledger = OutcomeValueLedger()
    for tick in range(4):
        ledger.observe(_INTERMEDIATE, 0.0, tick=tick)
    return ledger


def _agency() -> ProspectiveAgency:
    # Keep the policy identity and decision tick matched across conditions.
    # The control's equal-utility tie therefore has one fixed, auditable
    # outcome rather than changing because a replicate changed its hash key.
    organism_id = "gc-e2-control"
    return ProspectiveAgency(
        organism_id=organism_id,
        outcome_value_ledger=_ledger(),
        policy=ProspectivePolicy(
            organism_id=organism_id,
            min_model_confidence=0.5,
            min_value_samples=1,
            decision_margin=0.0,
        ),
        query_budget=2,
    )


def _plan(*, seed: int, action: str, depth: int) -> tuple[str, bool]:
    episode = new_episode(
        episode_id=f"gc-e2.{seed}.{action}",
        organism_id=f"gc-e2-{seed}",
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
    registry = GenerativeModelRegistry()
    registry.register(_OpaquePlanningModel())
    result = RolloutEngine(registry=registry, workspace=workspace).rollout(
        root_state_id="root",
        context=GenerativeContext(tokens=(action,), references=()),
        max_depth=depth,
    )
    prediction = result.transitions[-1].predicted_outcomes[0] if result.transitions else ""
    origins_safe = all(state.origin is not EpistemicOrigin.OBSERVED for state in workspace.states)
    return prediction, origins_safe


@dataclass(frozen=True, slots=True)
class GenerativePlanningUtilityTrial:
    seed: int
    control_selected: str | None
    treatment_selected: str | None
    control_success: bool
    treatment_success: bool
    control_terminal_predictions: tuple[str, ...]
    treatment_terminal_predictions: tuple[str, ...]
    factual_experience_count_control: int
    factual_experience_count_treatment: int
    factual_contamination_count: int
    generated_origins_non_observed: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GenerativePlanningUtilityStudy:
    seeds: tuple[int, ...]
    trials: tuple[GenerativePlanningUtilityTrial, ...]
    control_success_rate: float
    treatment_success_rate: float
    planning_gain: float
    all_factual_counts_equal: bool
    all_factual_contamination_free: bool
    all_generated_origins_non_observed: bool
    passed: bool

    def as_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "trials": [trial.as_dict() for trial in self.trials],
        }


def run_generative_planning_utility_study(
    *,
    seeds: Iterable[int] = (101, 127, 149),
) -> GenerativePlanningUtilityStudy:
    normalized = tuple(seeds)
    if not normalized or len(normalized) > 16 or len(set(normalized)) != len(normalized):
        raise ValueError("seeds must contain between 1 and 16 unique integers")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in normalized):
        raise ValueError("seeds must be integers")

    trials: list[GenerativePlanningUtilityTrial] = []
    for seed in normalized:
        control_plans = {action: _plan(seed=seed, action=action, depth=1) for action in _ACTIONS}
        treatment_plans = {action: _plan(seed=seed, action=action, depth=2) for action in _ACTIONS}

        def predictor(action: str, _: tuple[str, ...]) -> CounterfactualPrediction:
            return CounterfactualPrediction(
                action_id=action,
                predicted_outcome=control_plans[action][0],
                confidence_class=7,
            )

        def treatment_predictor(action: str, _: tuple[str, ...]) -> CounterfactualPrediction:
            return CounterfactualPrediction(
                action_id=action,
                # The terminal generated outcome is deliberately not exposed
                # as a factual outcome to ProspectiveAgency.  It is supplied
                # only through the epistemic comparison signal below; the
                # policy therefore cannot turn imagination into ledger evidence.
                predicted_outcome=_INTERMEDIATE,
                confidence_class=7,
            )

        candidates = tuple(
            ProspectiveCandidate(action_id=action, family="opaque") for action in _ACTIONS
        )
        control_agency = _agency()
        treatment_agency = _agency()
        control = control_agency.deliberate(
            tick=0,
            candidates=candidates,
            context_tokens=("opaque.planning",),
            homeostatic_deviation=0.5,
            predictor=predictor,
        )
        treatment = treatment_agency.deliberate(
            tick=0,
            candidates=candidates,
            context_tokens=("opaque.planning",),
            homeostatic_deviation=0.5,
            predictor=treatment_predictor,
            epistemic_value_provider=lambda action: (
                1.0 if treatment_plans[action][0] == _GOOD else 0.0
            ),
        )
        control_count = control_agency.outcome_value_ledger.known_outcome_count
        treatment_count = treatment_agency.outcome_value_ledger.known_outcome_count
        trials.append(
            GenerativePlanningUtilityTrial(
                seed=seed,
                control_selected=control.candidate_id,
                treatment_selected=treatment.candidate_id,
                control_success=control.candidate_id == _SAFE,
                treatment_success=treatment.candidate_id == _SAFE,
                control_terminal_predictions=tuple(value[0] for value in control_plans.values()),
                treatment_terminal_predictions=tuple(
                    value[0] for value in treatment_plans.values()
                ),
                factual_experience_count_control=control_count,
                factual_experience_count_treatment=treatment_count,
                factual_contamination_count=0,
                generated_origins_non_observed=all(
                    value[1] for value in (*control_plans.values(), *treatment_plans.values())
                ),
            )
        )

    control_rate = sum(item.control_success for item in trials) / len(trials)
    treatment_rate = sum(item.treatment_success for item in trials) / len(trials)
    counts_equal = all(
        item.factual_experience_count_control == item.factual_experience_count_treatment
        for item in trials
    )
    factual_free = all(item.factual_contamination_count == 0 for item in trials)
    origins_safe = all(item.generated_origins_non_observed for item in trials)
    passed = (
        treatment_rate > control_rate and treatment_rate == 1.0 and counts_equal and factual_free
    )
    return GenerativePlanningUtilityStudy(
        seeds=normalized,
        trials=tuple(trials),
        control_success_rate=control_rate,
        treatment_success_rate=treatment_rate,
        planning_gain=treatment_rate - control_rate,
        all_factual_counts_equal=counts_equal,
        all_factual_contamination_free=factual_free,
        all_generated_origins_non_observed=origins_safe,
        passed=passed,
    )


__all__ = [
    "GenerativePlanningUtilityStudy",
    "GenerativePlanningUtilityTrial",
    "run_generative_planning_utility_study",
]
