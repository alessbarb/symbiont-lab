from __future__ import annotations

import pytest

from symbiont.core.domains.context import TickContext
from symbiont.core.domains.embodiment import EmbodimentDomain


def test_embodiment_domain_rejects_foreign_body_and_clock() -> None:
    domain = EmbodimentDomain()
    domain.bind(
        embodiment_id="embodiment.a",
        body_id="body.a",
        embodiment_tick=4,
        new_episode=True,
    )
    with pytest.raises(ValueError, match="another Body"):
        domain.validate_context(
            TickContext(
                symbiont_id="symbiont.a",
                symbiont_tick=10,
                embodiment_id="embodiment.a",
                embodiment_tick=4,
                body_id="body.other",
            )
        )
    with pytest.raises(ValueError, match="expected body time"):
        domain.validate_context(
            TickContext(
                symbiont_id="symbiont.a",
                symbiont_tick=10,
                embodiment_id="embodiment.a",
                embodiment_tick=5,
                body_id="body.a",
            )
        )


def test_embodiment_clock_advances_only_after_completed_context() -> None:
    domain = EmbodimentDomain()
    domain.bind(
        embodiment_id="embodiment.a",
        body_id="body.a",
        embodiment_tick=7,
        new_episode=True,
    )
    context = TickContext(
        symbiont_id="symbiont.a",
        symbiont_tick=20,
        embodiment_id="embodiment.a",
        embodiment_tick=7,
        body_id="body.a",
    )
    domain.validate_context(context)
    assert domain.identity.expected_embodiment_tick == 7
    domain.complete_context(context)
    assert domain.identity.expected_embodiment_tick == 8
