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


def test_action_domain_discovers_action_dimensions_from_surface() -> None:
    surface = derive_actuator_constitution(3, physical_contract="domain-test")
    domain = ActionDomain(
        organism_id="organism.test",
        enabled=True,
        surface=surface,
    )

    assert len(domain.action_dimensions.items) == len(surface.actuator_ids)
    for actuator_id in surface.actuator_ids:
        dimension_id = domain.action_dimensions.discover(actuator_id)
        dimension = domain.action_dimensions.get(dimension_id)
        assert dimension is not None
        assert dimension.actuator_slot_id == actuator_id


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
