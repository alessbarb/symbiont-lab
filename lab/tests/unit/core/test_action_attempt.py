"""ActionAttempt: one issued command, one concrete intervention (§9-§10, §92)."""

from __future__ import annotations

import dataclasses

import pytest

from lab.studies.learning.agency_acquisition_body import CausalBody, build_subject
from symbiont.actuation.acquisition import AgencyAcquisition
from symbiont.actuation.action import MotorCommand
from symbiont.actuation.attempt import ActionAttempt
from symbiont.actuation.commitment import ActionCommitment
from symbiont.actuation.surface import derive_actuator_constitution


def _runtime_with_command():
    body = CausalBody(actuator_count=3, seed=11)
    runtime = build_subject(body, organism_id="attempt-subject")
    domain = runtime._action_domain
    for _ in range(64):
        runtime.tick()
        body.advance(runtime.last_actuations)
        if domain.acquisition.pending_attempt is not None:
            return runtime, body, domain
    raise AssertionError("fresh organism never issued a motor command")


def test_exploration_creates_attempt_without_competence():
    runtime, _body, domain = _runtime_with_command()
    attempt = domain.acquisition.pending_attempt
    assert runtime.last_action_source == "exploration"
    assert attempt is not None and attempt.competence_id is None
    assert domain.competence_library.items == ()


def test_competence_action_creates_attempt_with_competence():
    surface = derive_actuator_constitution(1, physical_contract="attempt-competence")
    commitment = ActionCommitment(
        commitment_id="commitment.c",
        proposal_id="proposal.c",
        effect_target_id=None,
        competence_id="competence.c",
        started_tick=4,
        controller_id="controller.competence.c",
        surface_fingerprint=surface.contract_fingerprint,
    )
    command = MotorCommand.from_mapping(
        command_id="command.c",
        commitment_id="commitment.c",
        controller_id="controller.competence.c",
        competence_id="competence.c",
        surface_fingerprint=surface.contract_fingerprint,
        channels={surface.actuator_ids[0]: 0.5},
        issued_at_tick=4,
    )
    attempt = AgencyAcquisition().open_attempt(
        command=command,
        commitment=commitment,
        context_ref="context.c",
        actuation_ref="actuation.c",
        tick=4,
    )
    assert attempt.competence_id == "competence.c"


def test_attempt_references_exact_commitment():
    _runtime, _body, domain = _runtime_with_command()
    attempt = domain.acquisition.pending_attempt
    assert domain.active_commitment is not None
    assert attempt.commitment_id == domain.active_commitment.commitment_id
    assert attempt.controller_id == domain.active_commitment.controller_id


def test_attempt_references_exact_motor_command():
    _runtime, _body, domain = _runtime_with_command()
    attempt = domain.acquisition.pending_attempt
    command = domain.last_motor_command
    assert command is not None
    assert attempt.motor_command_ref == command.command_id
    assert domain.trace_action(attempt.motor_command_ref) is not None


def test_attempt_keeps_embodiment_identity():
    _runtime, _body, domain = _runtime_with_command()
    attempt = domain.acquisition.pending_attempt
    command = domain.last_motor_command
    assert attempt.embodiment_id == command.embodiment_id == domain.embodiment_id
    assert attempt.surface_fingerprint == domain.current_surface_fingerprint


def test_attempt_closes_on_observation():
    runtime, body, domain = _runtime_with_command()
    attempt = domain.acquisition.pending_attempt
    runtime.tick()
    body.advance(runtime.last_actuations)
    closed = domain.acquisition.last_attempt
    assert closed is not None and closed.attempt_id == attempt.attempt_id
    assert closed.completed_tick == attempt.started_tick + 1
    assert domain.last_transition is not None
    assert domain.last_transition.attempt_id == attempt.attempt_id
    assert domain.causal_evidence.intervention_evidence[-1].attempt_id == attempt.attempt_id


def test_attempt_does_not_assert_effect_before_observation():
    _runtime, _body, domain = _runtime_with_command()
    attempt = domain.acquisition.pending_attempt
    assert "effect" not in {field.name for field in dataclasses.fields(ActionAttempt)}
    assert attempt.open
    assert all(item.attempt_id != attempt.attempt_id for item in domain.causal_evidence.evidence)


def test_attempt_cannot_close_on_its_own_tick():
    attempt = ActionAttempt(
        attempt_id="attempt.x",
        commitment_id="commitment.x",
        controller_id="controller.x",
        competence_id=None,
        intervention_signature_id="intervention.signature.x",
        context_ref="context.x",
        embodiment_id=None,
        surface_fingerprint="surface.x",
        motor_command_ref="command.x",
        actuation_ref="actuation.x",
        started_tick=3,
    )
    with pytest.raises(ValueError):
        attempt.close(tick=3)
