"""Evaluator-only causal controls for L8 prospective agency.

This study validates the agency mechanism in a closed opaque environment before
running expensive Physics3D trials. The evaluator owns the hidden contingency
used only to score choices. The ProspectiveAgency instance receives only opaque
action ids, opaque predicted outcomes, model confidence and its own learned
OutcomeValueLedger.

Passing this study is a mechanism gate, not evidence of embodied resource
seeking or ecological competence.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass

from symbiont.agency import (
    CounterfactualPrediction,
    OutcomeValueLedger,
    ProspectiveAgency,
    ProspectiveCandidate,
    ProspectivePolicy,
)

_ACTIONS = (
    "primitive.opaque.a",
    "primitive.opaque.b",
    "primitive.opaque.c",
)
_OUTCOMES = (
    "outcome.opaque.a",
    "outcome.opaque.b",
    "outcome.opaque.c",
)
_TRUE_VALUES = {
    _OUTCOMES[0]: 0.30,
    _OUTCOMES[1]: 0.02,
    _OUTCOMES[2]: -0.25,
}


@dataclass(frozen=True, slots=True)
class ProspectiveAgencyControlSeedResult:
    seed: int
    full_action_context_a: str | None
    full_action_context_b: str | None
    full_future_value: float
    no_counterfactual_future_value: float
    shuffled_model_future_value: float
    shuffled_value_future_value: float
    babbling_future_value: float
    prediction_diversity: int
    context_sensitive: bool
    full_selected_optimal: bool
    model_shuffle_degraded: bool
    value_shuffle_degraded: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProspectiveAgencyControlsStudy:
    seeds: tuple[int, ...]
    per_seed: tuple[ProspectiveAgencyControlSeedResult, ...]
    mean_full_future_value: float
    mean_no_counterfactual_future_value: float
    mean_shuffled_model_future_value: float
    mean_shuffled_value_future_value: float
    mean_babbling_future_value: float
    gate_prediction_discrimination: bool
    gate_context_sensitive_choice: bool
    gate_model_control: bool
    gate_value_control: bool
    gate_causal_benefit: bool
    all_gates_pass: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _normalize_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if isinstance(seeds, (str, bytes)) or not isinstance(seeds, Sequence):
        raise ValueError("seeds must be a sequence of unique integers")
    normalized = tuple(seeds)
    if not normalized or len(normalized) > 16:
        raise ValueError("seeds must contain between 1 and 16 entries")
    if len(set(normalized)) != len(normalized) or any(
        isinstance(seed, bool) or not isinstance(seed, int) for seed in normalized
    ):
        raise ValueError("seeds must be unique integers")
    return normalized


def _trained_ledger(*, shuffled: bool = False) -> OutcomeValueLedger:
    ledger = OutcomeValueLedger()
    values = (
        (_TRUE_VALUES[_OUTCOMES[2]], _TRUE_VALUES[_OUTCOMES[0]], _TRUE_VALUES[_OUTCOMES[1]])
        if shuffled
        else (_TRUE_VALUES[_OUTCOMES[0]], _TRUE_VALUES[_OUTCOMES[1]], _TRUE_VALUES[_OUTCOMES[2]])
    )
    for tick in range(8):
        for outcome_id, value in zip(_OUTCOMES, values, strict=True):
            # These are evaluator-generated *observed-history fixtures* for the
            # mechanism study. ProspectiveAgency sees only the resulting ledger.
            ledger.observe(outcome_id, value, tick=tick)
    return ledger


def _agency(*, seed: int, shuffled_value: bool = False) -> ProspectiveAgency:
    organism_id = f"prospective-control-{seed}"
    ledger = _trained_ledger(shuffled=shuffled_value)
    policy = ProspectivePolicy(
        organism_id=organism_id,
        min_model_confidence=0.5,
        min_value_samples=4,
        decision_margin=0.01,
    )
    return ProspectiveAgency(
        organism_id=organism_id,
        outcome_value_ledger=ledger,
        policy=policy,
        query_budget=8,
    )


def _mapping(*, context: str, shuffled: bool) -> dict[str, str]:
    # Context A: action A predicts the historically best outcome.
    # Context B: the same best outcome is predicted by action B. This checks
    # context-sensitive selection without changing the value ledger.
    if context == "context.a":
        mapping = {
            _ACTIONS[0]: _OUTCOMES[0],
            _ACTIONS[1]: _OUTCOMES[1],
            _ACTIONS[2]: _OUTCOMES[2],
        }
    elif context == "context.b":
        mapping = {
            _ACTIONS[0]: _OUTCOMES[1],
            _ACTIONS[1]: _OUTCOMES[0],
            _ACTIONS[2]: _OUTCOMES[2],
        }
    else:
        raise ValueError("unsupported controlled context")

    if not shuffled:
        return mapping

    # Rotate predictions relative to action identity. The value model stays
    # intact, so any degradation is specifically due to action/outcome model
    # correspondence being wrong.
    return {
        action_id: mapping[_ACTIONS[(index + 1) % len(_ACTIONS)]]
        for index, action_id in enumerate(_ACTIONS)
    }


def _deliberate(
    *,
    agency: ProspectiveAgency,
    tick: int,
    context: str,
    shuffled_model: bool = False,
):
    mapping = _mapping(context=context, shuffled=shuffled_model)
    candidates = tuple(
        ProspectiveCandidate(action_id=action_id, family="primitive") for action_id in _ACTIONS
    )

    def predictor(action_id: str, context_tokens: tuple[str, ...]) -> CounterfactualPrediction:
        assert context_tokens == (context,)
        return CounterfactualPrediction(
            action_id=action_id,
            predicted_outcome=mapping[action_id],
            confidence_class=7,
        )

    return agency.deliberate(
        tick=tick,
        candidates=candidates,
        context_tokens=(context,),
        homeostatic_deviation=0.75,
        predictor=predictor,
        has_active_model=True,
        organism_alive=True,
    )


def _true_future_value(action_id: str | None, *, context: str = "context.a") -> float:
    if action_id is None:
        return 0.0
    outcome = _mapping(context=context, shuffled=False)[action_id]
    return float(_TRUE_VALUES[outcome])


def run_prospective_agency_controls_study(
    *,
    seeds: Sequence[int] = (101, 127, 149),
) -> ProspectiveAgencyControlsStudy:
    """Run preregistered opaque mechanism controls for L8.

    The full condition uses correct action->outcome prediction and correctly
    learned outcome values. Controls independently remove or scramble the two
    causal links. No resource coordinate, distance, locomotion label or
    evaluator score is passed into ProspectiveAgency.
    """

    normalized = _normalize_seeds(seeds)
    results: list[ProspectiveAgencyControlSeedResult] = []

    for seed in normalized:
        full = _agency(seed=seed)
        decision_a = _deliberate(
            agency=full,
            tick=10,
            context="context.a",
        )
        decision_b = _deliberate(
            agency=full,
            tick=11,
            context="context.b",
        )

        shuffled_model = _agency(seed=seed + 10_000)
        shuffled_model_decision = _deliberate(
            agency=shuffled_model,
            tick=10,
            context="context.a",
            shuffled_model=True,
        )

        shuffled_value = _agency(seed=seed + 20_000, shuffled_value=True)
        shuffled_value_decision = _deliberate(
            agency=shuffled_value,
            tick=10,
            context="context.a",
        )

        # No-counterfactual is an explicit abstention control: without a model
        # query there is no L8-selected action.
        no_counterfactual_action = None

        # Seeded babbling control, deliberately independent from model/value
        # information. Seed modulo is transparent and replayable.
        babbling_action = _ACTIONS[seed % len(_ACTIONS)]

        mapping_a = _mapping(context="context.a", shuffled=False)
        prediction_diversity = len(set(mapping_a.values()))
        full_value = _true_future_value(
            decision_a.candidate_id if decision_a.reason == "selected" else None
        )
        shuffled_model_value = _true_future_value(
            shuffled_model_decision.candidate_id
            if shuffled_model_decision.reason == "selected"
            else None
        )
        shuffled_value_future = _true_future_value(
            shuffled_value_decision.candidate_id
            if shuffled_value_decision.reason == "selected"
            else None
        )
        babbling_value = _true_future_value(babbling_action)

        results.append(
            ProspectiveAgencyControlSeedResult(
                seed=seed,
                full_action_context_a=decision_a.candidate_id,
                full_action_context_b=decision_b.candidate_id,
                full_future_value=full_value,
                no_counterfactual_future_value=_true_future_value(no_counterfactual_action),
                shuffled_model_future_value=shuffled_model_value,
                shuffled_value_future_value=shuffled_value_future,
                babbling_future_value=babbling_value,
                prediction_diversity=prediction_diversity,
                context_sensitive=(
                    decision_a.reason == "selected"
                    and decision_b.reason == "selected"
                    and decision_a.candidate_id != decision_b.candidate_id
                ),
                full_selected_optimal=(
                    decision_a.reason == "selected" and decision_a.candidate_id == _ACTIONS[0]
                ),
                model_shuffle_degraded=shuffled_model_value < full_value,
                value_shuffle_degraded=shuffled_value_future < full_value,
            )
        )

    count = len(results)
    mean_full = sum(item.full_future_value for item in results) / count
    mean_no_counterfactual = sum(item.no_counterfactual_future_value for item in results) / count
    mean_shuffled_model = sum(item.shuffled_model_future_value for item in results) / count
    mean_shuffled_value = sum(item.shuffled_value_future_value for item in results) / count
    mean_babbling = sum(item.babbling_future_value for item in results) / count

    gate_prediction_discrimination = all(item.prediction_diversity >= 2 for item in results)
    gate_context_sensitive_choice = all(item.context_sensitive for item in results)
    gate_model_control = all(item.model_shuffle_degraded for item in results)
    gate_value_control = all(item.value_shuffle_degraded for item in results)
    gate_causal_benefit = (
        mean_full > mean_no_counterfactual
        and mean_full > mean_shuffled_model
        and mean_full > mean_shuffled_value
        and mean_full > mean_babbling
        and all(item.full_selected_optimal for item in results)
    )
    all_gates_pass = all(
        (
            gate_prediction_discrimination,
            gate_context_sensitive_choice,
            gate_model_control,
            gate_value_control,
            gate_causal_benefit,
        )
    )

    return ProspectiveAgencyControlsStudy(
        seeds=normalized,
        per_seed=tuple(results),
        mean_full_future_value=mean_full,
        mean_no_counterfactual_future_value=mean_no_counterfactual,
        mean_shuffled_model_future_value=mean_shuffled_model,
        mean_shuffled_value_future_value=mean_shuffled_value,
        mean_babbling_future_value=mean_babbling,
        gate_prediction_discrimination=gate_prediction_discrimination,
        gate_context_sensitive_choice=gate_context_sensitive_choice,
        gate_model_control=gate_model_control,
        gate_value_control=gate_value_control,
        gate_causal_benefit=gate_causal_benefit,
        all_gates_pass=all_gates_pass,
    )


__all__ = [
    "ProspectiveAgencyControlSeedResult",
    "ProspectiveAgencyControlsStudy",
    "run_prospective_agency_controls_study",
]
