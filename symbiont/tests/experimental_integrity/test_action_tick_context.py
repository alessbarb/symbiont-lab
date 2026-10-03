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
from symbiont.core.domains.context import TickContext


def test_action_domain_rejects_foreign_embodiment_context() -> None:
    surface = derive_actuator_constitution(1, physical_contract="context-body")
    domain = ActionDomain(
        organism_id="symbiont.context",
        enabled=True,
        surface=surface,
        embodiment_id="embodiment.expected",
    )
    proposal = ActionProposal(
        proposal_id="proposal.context",
        source=ActionSource.EXPLORATION,
        effect_target_id=None,
        competence_id=None,
        justification=ActionJustification(),
        evaluation=ActionEvaluation(epistemic_relevance=1.0),
    )
    domain.commit(proposal, tick=1, controller_id="controller.context")
    with pytest.raises(ValueError, match="another EmbodimentEpisode"):
        domain.step(
            None,
            (),
            context=TickContext(
                symbiont_id="symbiont.context",
                symbiont_tick=2,
                embodiment_id="embodiment.other",
            ),
            services=None,  # type: ignore[arg-type]
        )
