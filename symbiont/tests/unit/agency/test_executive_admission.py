"""Activation is not intention: explicit executive admission (§47-§48, §101)."""

from __future__ import annotations

from symbiont.agency.affordance import ActionAffordance, affordance_id_for
from symbiont.agency.intention import AdmissionRoute
from symbiont.agency.prospective import (
    ExecutiveAdmissionPolicy,
    GenerativeAnticipation,
    admit_afforded_action,
)

POLICY = ExecutiveAdmissionPolicy(readout_threshold=0.1, minimum_relevance=0.2)


def _affordance(competence_id: str, *, prediction_confidence: float) -> ActionAffordance:
    return ActionAffordance(
        affordance_id=affordance_id_for(
            competence_id=competence_id,
            anticipated_effect_id="effect.e",
            context_ref=None,
            embodiment_id=None,
        ),
        competence_id=competence_id,
        anticipated_effect_id="effect.e",
        context_ref=None,
        embodiment_id=None,
        prediction_confidence=prediction_confidence,
        controllability=0.6,
        executability_confidence=0.8,
        prediction_ref="prediction.p",
        evidence_refs=("causal.x",),
    )


def _admit(affordances, readouts, **kwargs):
    return admit_afforded_action(
        affordances=affordances,
        primitive_readouts=readouts,
        epistemic_value=kwargs.get("epistemic_value", lambda _cid: None),
        homeostatic_relevance=kwargs.get("homeostatic_relevance", lambda _cid: 0.0),
        generative_affordances=kwargs.get("generative_affordances", ()),
        policy=POLICY,
    )


def test_primitive_readout_alone_does_not_form_intent():
    # Strongly active readout, but nothing is currently afforded.
    assert _admit((), {"competence.c": 0.9}) is None


def test_readout_plus_affordance_without_executive_admission_does_not_form_intent():
    # Represented and afforded, but fully predictable and with no current need:
    # there is no executive reason to realize it now.
    affordance = _affordance("competence.c", prediction_confidence=1.0)
    assert _admit((affordance,), {"competence.c": 0.9}, epistemic_value=lambda _cid: 0.0) is None


def test_readout_plus_affordance_plus_admission_can_form_intent():
    affordance = _affordance("competence.c", prediction_confidence=0.4)
    decision = _admit((affordance,), {"competence.c": 0.9})
    assert decision is not None
    assert decision.competence_id == "competence.c"
    assert decision.anticipated_effect_id == "effect.e"
    assert decision.admission is AdmissionRoute.COGNITIVE
    assert decision.supporting_affordance_id == affordance.affordance_id
    assert "readout.primitive.competence.c" in decision.origin_refs


def test_inactive_readout_is_not_represented():
    affordance = _affordance("competence.c", prediction_confidence=0.4)
    assert _admit((affordance,), {"competence.c": 0.05}) is None


def test_homeostatic_relevance_can_admit_a_predictable_competence():
    affordance = _affordance("competence.c", prediction_confidence=1.0)
    decision = _admit(
        (affordance,),
        {"competence.c": 0.9},
        epistemic_value=lambda _cid: 0.0,
        homeostatic_relevance=lambda _cid: 0.7,
    )
    assert decision is not None and decision.homeostatic_relevance == 0.7


def test_generative_anticipation_is_a_representation_route():
    affordance = _affordance("competence.c", prediction_confidence=0.4)
    anticipation = GenerativeAnticipation(effect_id="effect.e", hypothesis_refs=("hypothesis.h",))
    decision = _admit((affordance,), {}, generative_affordances=((affordance, anticipation),))
    assert decision is not None
    assert decision.admission is AdmissionRoute.GENERATIVE
    assert "hypothesis.h" in decision.origin_refs
