from __future__ import annotations

import pytest

from symbiont.actuation.action import (
    ActionEvaluation,
    ActionJustification,
    ActionProposal,
    ActionSource,
)
from symbiont.actuation.surface import derive_actuator_constitution
from symbiont.core.domains.action import ActionDomain


def _proposal() -> ActionProposal:
    return ActionProposal(
        proposal_id="proposal.test",
        source=ActionSource.EXPLORATION,
        effect_target_id=None,
        competence_id=None,
        justification=ActionJustification(originating_need_id="internal.uncertainty"),
        evaluation=ActionEvaluation(epistemic_relevance=1.0),
    )


def test_action_domain_is_only_command_authority() -> None:
    surface = derive_actuator_constitution(2, physical_contract="domain-test")
    domain = ActionDomain(
        organism_id="organism.test",
        enabled=True,
        surface=surface,
    )
    commitment = domain.commit(_proposal(), tick=3, controller_id="controller.explore")
    command = domain.issue_command({surface.actuator_ids[0]: 0.4}, tick=3)
    assert command.commitment_id == commitment.commitment_id
    assert command.surface_fingerprint == surface.contract_fingerprint
    assert domain.trace_action(command.command_id) is not None
    actuations = domain.execute_command(command)
    assert len(actuations) == 1
    assert actuations[0].delivered == 0.4


def test_surface_does_not_bootstrap_action_dimensions() -> None:
    """A fresh organism knows 0 of its N physical motor opportunities (§17, §120)."""
    surface = derive_actuator_constitution(3, physical_contract="domain-test")
    domain = ActionDomain(
        organism_id="organism.test",
        enabled=True,
        surface=surface,
    )

    assert len(surface.actuator_ids) == 3
    assert domain.action_dimensions.items == ()
    assert domain.intervention_signatures.items == ()


def test_action_domain_without_surface_has_no_action_dimensions() -> None:
    domain = ActionDomain(organism_id="organism.test", enabled=False, surface=None)

    assert domain.action_dimensions.items == ()


def test_command_cannot_execute_after_embodiment_change() -> None:
    first = derive_actuator_constitution(1, physical_contract="body-a")
    second = derive_actuator_constitution(1, physical_contract="body-b")
    domain = ActionDomain(
        organism_id="organism.test",
        enabled=True,
        surface=first,
        embodiment_id="embodiment.a",
    )
    domain.commit(_proposal(), tick=1, controller_id="controller.explore")
    command = domain.issue_command({first.actuator_ids[0]: 0.2}, tick=1)
    domain.begin_embodiment(surface=second, embodiment_id="embodiment.b", tick=2)
    with pytest.raises(RuntimeError):
        domain.execute_command(command)


def test_command_requires_active_commitment() -> None:
    surface = derive_actuator_constitution(1, physical_contract="body-a")
    domain = ActionDomain(
        organism_id="organism.test",
        enabled=True,
        surface=surface,
    )
    with pytest.raises(RuntimeError, match="active organism-owned commitment"):
        domain.issue_command({surface.actuator_ids[0]: 0.5}, tick=1)


def test_competence_whose_controller_left_the_pool_is_not_executable():
    """Regression: a library competence outliving its controller seed was
    admitted on every tick and failed its controller in a loop."""
    from symbiont_lab.studies.learning.agency_acquisition_body import CausalBody, build_subject

    body = CausalBody(actuator_count=4, seed=127)
    runtime = build_subject(body, organism_id="controller-pool", factorized_effects=True)
    for _ in range(600):
        runtime.tick()
        body.advance(runtime.last_actuations)
    domain = runtime._action_domain
    engine = domain._competence_development
    for competence in domain.competence_library.items:
        if domain.competence_is_executable(competence):
            assert engine.can_activate(competence.competence_id)
