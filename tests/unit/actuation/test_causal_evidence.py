"""Causal evidence exists before competence and keeps multiscale identity (§13-§16, §95)."""

from __future__ import annotations

import pytest

from symbiont.actuation.evidence import CausalEvidenceLedger, SensorimotorTransition
from symbiont.actuation.model import CausalSourceKind
from tests.unit.actuation.acquisition_support import A, act, fresh_acquisition, rest


def test_exploration_without_competence_produces_causal_evidence():
    acquisition = fresh_acquisition()
    update = act(acquisition, 0, {A: 0.5}, {"signal.a": 0.4})
    evidence = update.evidence
    assert evidence.competence_id is None
    assert evidence.attempt_id is not None
    assert evidence.intervention_signature_id is not None
    assert evidence.effect_id is not None
    assert not evidence.is_passive


def test_causal_evidence_preserves_attempt_id():
    acquisition = fresh_acquisition()
    update = act(acquisition, 0, {A: 0.5}, {"signal.a": 0.4})
    assert acquisition.last_attempt is not None
    assert update.evidence.attempt_id == acquisition.last_attempt.attempt_id


def test_causal_evidence_preserves_commitment_id():
    acquisition = fresh_acquisition()
    update = act(acquisition, 0, {A: 0.5}, {"signal.a": 0.4})
    assert update.evidence.commitment_id == "commitment.0"
    assert acquisition.causal_evidence.commitment_evidence("commitment.0") == (update.evidence,)


def test_causal_evidence_preserves_intervention_signature_id():
    acquisition = fresh_acquisition()
    update = act(acquisition, 0, {A: 0.5}, {"signal.a": 0.4})
    assert acquisition.last_attempt is not None
    assert (
        update.evidence.intervention_signature_id
        == acquisition.last_attempt.intervention_signature_id
    )


def test_motor_transition_requires_attempt_and_signature():
    with pytest.raises(ValueError):
        SensorimotorTransition(
            transition_id="transition.x",
            tick_start=0,
            tick_end=1,
            context_ref="context.x",
            commitment_id="commitment.x",
            controller_id="controller.x",
            competence_id=None,
            attempt_id=None,
            intervention_signature_id=None,
            state_before_ref="state.0",
            motor_command_ref="command.x",
            actuation_ref="actuation.x",
            prediction_ref=None,
            state_after_ref="state.1",
        )


def test_passive_window_contributes_counterfactual_evidence():
    acquisition = fresh_acquisition()
    update = act(acquisition, 0, {A: 0.5}, {"signal.a": 0.4})
    effect_id = update.evidence.effect_id
    signature_id = update.evidence.intervention_signature_id
    ledger = acquisition.causal_evidence
    before = ledger.signature_effect_opportunities(
        effect_id, intervention_signature_id=signature_id
    )
    rest(acquisition, 10, {"signal.a": 0.4})
    after = ledger.signature_effect_opportunities(effect_id, intervention_signature_id=signature_id)
    assert after[:2] == before[:2]
    assert after[2] == before[2] + 1 and after[3] == before[3] + 1
    assert ledger.passive_evidence[-1].is_passive


def _signature_controllability(acquisition, update):
    return acquisition.controllability_model.estimate(
        source_kind=CausalSourceKind.INTERVENTION,
        source_ref=update.evidence.intervention_signature_id,
        effect_id=update.evidence.effect_id,
    )


def test_effect_present_without_intervention_reduces_causal_advantage():
    quiet = fresh_acquisition()
    noisy = fresh_acquisition()
    for tick in range(0, 16, 2):
        rest(quiet, tick, {})
        rest(noisy, tick, {"signal.a": 0.4})
    for tick in range(20, 30, 2):
        quiet_update = act(quiet, tick, {A: 0.5}, {"signal.a": 0.4})
        noisy_update = act(noisy, tick, {A: 0.5}, {"signal.a": 0.4})
    quiet_estimate = _signature_controllability(quiet, quiet_update)
    noisy_estimate = _signature_controllability(noisy, noisy_update)
    assert quiet_estimate.causal_advantage > noisy_estimate.causal_advantage
    assert quiet_estimate.confidence > noisy_estimate.confidence


def test_repeated_specific_intervention_increases_controllability():
    acquisition = fresh_acquisition()
    for tick in range(0, 16, 2):
        rest(acquisition, tick, {})
    confidences = []
    for tick in range(20, 36, 2):
        update = act(acquisition, tick, {A: 0.5}, {"signal.a": 0.4})
        confidences.append(_signature_controllability(acquisition, update).confidence)
    assert confidences[-1] > confidences[0]
    assert all(later >= earlier for earlier, later in zip(confidences, confidences[1:]))


def test_ledger_bounds_passive_windows_separately():
    ledger = CausalEvidenceLedger(capacity=8, passive_capacity=2)
    for tick in range(5):
        ledger.observe_passive_window(
            tick_start=tick,
            tick_end=tick + 1,
            context_ref=None,
            prior_state_ref=f"state.{tick}",
            resulting_state_ref=f"state.{tick + 1}",
            effect_id=None,
        )
    assert len(ledger.passive_evidence) == 2
    assert ledger.intervention_evidence == ()


def test_ledger_v3_roundtrip_and_v2_migration_marks_no_passive_windows():
    acquisition = fresh_acquisition()
    act(acquisition, 0, {A: 0.5}, {"signal.a": 0.4})
    rest(acquisition, 4, {})
    ledger = acquisition.causal_evidence
    restored = CausalEvidenceLedger.restore(ledger.checkpoint())
    assert restored.evidence == ledger.evidence
    legacy = {
        "schema_version": 2,
        "capacity": 16,
        "evidence": [
            {
                "evidence_id": "causal.legacy",
                "transition_id": "transition.legacy",
                "action_ref": "command.legacy",
                "competence_id": "competence.legacy",
                "effect_id": "effect.legacy",
                "context_ref": "context.legacy",
                "prior_state_ref": "state.a",
                "resulting_state_ref": "state.b",
                "prediction_ref": None,
                "observation_tick": 3,
            }
        ],
    }
    migrated = CausalEvidenceLedger.restore(legacy)
    (item,) = migrated.evidence
    assert not item.is_passive
    assert item.attempt_id is None and item.intervention_signature_id is None
    assert item.competence_id == "competence.legacy"
