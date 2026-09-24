from __future__ import annotations

from pathlib import Path

import pytest

from symbiont.actuation.action import (
    ActionEvaluation,
    ActionJustification,
    ActionProposal,
    ActionSource,
    MotorCommand,
)
from symbiont.actuation.arbitration import ActionArbitrator
from symbiont.actuation.commitment import ActionCommitment
from symbiont.actuation.competence import (
    CompetenceEvidence,
    CompetenceMaturity,
    MotorCompetence,
)
from symbiont.actuation.effects import EffectSpace
from symbiont.actuation.evidence import (
    CausalEvidenceLedger,
    SensorimotorTransition,
)
from symbiont.actuation.model import ControllabilityModel
from symbiont.actuation.surface import derive_actuator_constitution


def _proposal(source: ActionSource, proposal_id: str, competence_id: str | None = None):
    return ActionProposal(
        proposal_id=proposal_id,
        source=source,
        effect_target_id=None,
        competence_id=competence_id,
        justification=ActionJustification(competence_id=competence_id),
        evaluation=ActionEvaluation(
            epistemic_relevance=1.0 if source is ActionSource.EXPLORATION else 0.0,
            protective_relevance=1.0 if source is ActionSource.PROTECTION else 0.0,
            effect_confidence=0.8 if competence_id else 0.0,
            controllability=0.8 if competence_id else None,
            uncertainty=0.2 if competence_id else 1.0,
        ),
    )


def test_feedback_commands_inherit_one_commitment():
    commitment = ActionCommitment(
        commitment_id="commitment.1",
        proposal_id="proposal.1",
        effect_target_id=None,
        competence_id="competence.1",
        started_tick=1,
        controller_id="controller.1",
    )
    first = MotorCommand.from_mapping(
        commitment_id=commitment.commitment_id,
        controller_id=commitment.controller_id,
        competence_id=commitment.competence_id,
        channels={"actuator.a": 0.2},
    )
    second = MotorCommand.from_mapping(
        commitment_id=commitment.commitment_id,
        controller_id=commitment.controller_id,
        competence_id=commitment.competence_id,
        channels={"actuator.a": 0.4},
    )
    assert first.commitment_id == second.commitment_id == "commitment.1"


def test_protection_dominates_without_direct_motor_route():
    arbitrator = ActionArbitrator()
    result = arbitrator.choose(
        proposals=(
            _proposal(ActionSource.EXPLORATION, "proposal.explore"),
            _proposal(ActionSource.PROTECTION, "proposal.protect", "competence.safe"),
        ),
        current=None,
        tick=10,
    )
    assert result.proposal is not None
    assert result.proposal.source is ActionSource.PROTECTION


def test_effect_target_can_only_reference_discovered_effect():
    space = EffectSpace()
    with pytest.raises(KeyError):
        space.target("effect.external")
    effect = space.observe({"signal.abc": 0.5})
    assert effect is not None
    target = space.target(effect.effect_id)
    assert target.effect_id == effect.effect_id


def test_actuator_surface_contains_no_learned_health_or_cost():
    channel = derive_actuator_constitution(1).slots[0]
    assert not hasattr(channel, "health")
    assert not hasattr(channel, "reliability")
    assert not hasattr(channel, "basal_cost")
    assert not hasattr(channel, "initial_health")
    assert not hasattr(channel, "execution_threshold")


def test_competence_maturity_is_projection_of_evidence():
    evidence = CompetenceEvidence(
        controller_seed_ref="seed.1",
        support=8,
        failures=0,
        reproducibility=0.9,
        controllability=0.3,
        directional_consistency=0.9,
    )
    assert evidence.maturity is CompetenceMaturity.ROBUST


def test_surface_mismatch_does_not_mutate_competence_evidence():
    evidence = CompetenceEvidence(
        controller_seed_ref="seed.1",
        support=8,
        reproducibility=0.9,
        controllability=0.3,
        directional_consistency=0.9,
    )
    competence = MotorCompetence(
        competence_id="competence.1",
        controller_id="controller.1",
        effect_id=None,
        evidence=evidence,
        surface_binding="surface.A",
    )
    before = (
        competence.evidence.support,
        competence.evidence.controllability,
        competence.effect_id,
    )
    assert competence.surface_binding != "surface.B"
    after = (
        competence.evidence.support,
        competence.evidence.controllability,
        competence.effect_id,
    )
    assert after == before


def test_controllability_requires_advantage_over_alternative_actions():
    ledger = CausalEvidenceLedger()
    for index, competence in enumerate(("competence.a", "competence.a", "competence.b", "competence.b")):
        transition = SensorimotorTransition(
            transition_id=f"transition.{index}",
            tick_start=index,
            tick_end=index + 1,
            context_ref="context.1",
            commitment_id=f"commitment.{index}",
            controller_id=f"controller.{competence}",
            competence_id=competence,
            state_before_ref=f"state.before.{index}",
            motor_command_ref=f"command.{index}",
            actuation_ref=f"actuation.{index}",
            prediction_ref=None,
            state_after_ref=f"state.after.{index}",
            observed_effect_id="effect.x",
        )
        ledger.observe(transition)

    estimate = ControllabilityModel().update_from_ledger(
        ledger,
        effect_id="effect.x",
        competence_id="competence.a",
        context_id=None,
        tick=10,
    )
    assert estimate.reliability == 1.0
    assert estimate.counterfactual_rate == 1.0
    assert estimate.causal_advantage == 0.0
    assert estimate.confidence == 0.0


def test_runtime_has_no_motor_mode_or_posthoc_origin_classifier():
    source = Path("src/symbiont/core/orchestration/runtime.py").read_text(encoding="utf-8")
    assert "motor_exploration_mode" not in source
    assert "_classify_executed_motor_origin" not in source
    assert '"mixed"' not in source
    assert '"primitive_reactive"' not in source
    assert '"primitive_prospective"' not in source
