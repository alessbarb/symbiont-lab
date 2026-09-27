"""Agency is contingency + specificity + counterfactual evidence, not prediction (§22-§23, §96)."""

from __future__ import annotations

from symbiont.actuation.evidence import CausalEvidenceLedger
from symbiont.actuation.model import AgencyModel, CausalSourceKind
from tests.unit.actuation.acquisition_support import A, act, fresh_acquisition, rest


def _agency(acquisition, update):
    return acquisition.agency_model.estimate(
        source_kind=CausalSourceKind.INTERVENTION,
        source_ref=update.evidence.intervention_signature_id,
        effect_id=update.evidence.effect_id,
    )


def test_prediction_match_alone_does_not_create_agency():
    acquisition = fresh_acquisition()
    # The effect is as common without intervention as with it.
    for tick in range(0, 20, 2):
        rest(acquisition, tick, {"signal.a": 0.4})
    for tick in range(30, 40, 2):
        update = act(acquisition, tick, {A: 0.5}, {"signal.a": 0.4})
    ledger = acquisition.causal_evidence
    estimate = AgencyModel().update_from_ledger(
        ledger,
        source_kind=CausalSourceKind.INTERVENTION,
        source_ref=update.evidence.intervention_signature_id,
        effect_id=update.evidence.effect_id,
        context_id=None,
        tick=40,
        prediction_match=1.0,
    )
    assert estimate.prediction_match == 1.0
    assert estimate.causal_specificity == 0.0
    assert estimate.confidence == 0.0


def test_prediction_match_without_contingency_is_zero():
    ledger = CausalEvidenceLedger()
    estimate = AgencyModel().update_from_ledger(
        ledger,
        source_kind=CausalSourceKind.INTERVENTION,
        source_ref="intervention.signature.none",
        effect_id="effect.none",
        context_id=None,
        tick=1,
        prediction_match=1.0,
    )
    assert estimate.confidence == 0.0


def test_temporal_contingency_increases_agency():
    reliable = fresh_acquisition()
    unreliable = fresh_acquisition()
    for tick in range(0, 16, 2):
        rest(reliable, tick, {})
        rest(unreliable, tick, {})
    for index, tick in enumerate(range(20, 36, 2)):
        reliable_update = act(reliable, tick, {A: 0.5}, {"signal.a": 0.4})
        # The same intervention produces the effect only half of the time.
        unreliable_update = act(
            unreliable, tick, {A: 0.5}, {"signal.a": 0.4} if index % 2 == 0 else {}
        )
    reliable_estimate = _agency(reliable, reliable_update)
    effect_id = reliable_update.evidence.effect_id
    unreliable_estimate = unreliable.agency_model.estimate(
        source_kind=CausalSourceKind.INTERVENTION,
        source_ref=unreliable_update.evidence.intervention_signature_id,
        effect_id=effect_id,
    )
    assert reliable_estimate.temporal_contingency > unreliable_estimate.temporal_contingency
    assert reliable_estimate.confidence > unreliable_estimate.confidence


def test_counterfactual_specificity_increases_agency():
    specific = fresh_acquisition()
    unspecific = fresh_acquisition()
    for index, tick in enumerate(range(0, 16, 2)):
        rest(specific, tick, {})
        rest(unspecific, tick, {"signal.a": 0.4} if index % 2 == 0 else {})
    for tick in range(20, 36, 2):
        specific_update = act(specific, tick, {A: 0.5}, {"signal.a": 0.4})
        unspecific_update = act(unspecific, tick, {A: 0.5}, {"signal.a": 0.4})
    specific_estimate = _agency(specific, specific_update)
    unspecific_estimate = _agency(unspecific, unspecific_update)
    assert specific_estimate.causal_specificity > unspecific_estimate.causal_specificity
    assert specific_estimate.confidence > unspecific_estimate.confidence


def test_effect_common_without_action_reduces_agency():
    rare = fresh_acquisition()
    common = fresh_acquisition()
    for tick in range(0, 16, 2):
        rest(rare, tick, {})
        rest(common, tick, {"signal.a": 0.4})
    for tick in range(20, 36, 2):
        rare_update = act(rare, tick, {A: 0.5}, {"signal.a": 0.4})
        common_update = act(common, tick, {A: 0.5}, {"signal.a": 0.4})
    assert _agency(rare, rare_update).confidence > _agency(common, common_update).confidence


def test_agency_can_exist_before_motor_competence():
    acquisition = fresh_acquisition()
    for tick in range(0, 16, 2):
        rest(acquisition, tick, {})
    for tick in range(20, 36, 2):
        update = act(acquisition, tick, {A: 0.5}, {"signal.a": 0.4})
    estimate = _agency(acquisition, update)
    assert update.evidence.competence_id is None
    assert estimate.confidence > 0.0
    assert acquisition.agency_model.estimates_for(CausalSourceKind.COMPETENCE) == ()
