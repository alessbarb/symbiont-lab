"""Episode projections built without re-validation equal validated ones."""

from __future__ import annotations

import pytest

from symbiont.modeling.episodic import EpisodicMemoryError, EpisodicProjection


def test_trusted_projection_equals_validated_projection() -> None:
    fields = dict(
        sense_ids=("sense.a", "sense.b"),
        concept_ids=("concept.c",),
        internal_tokens=(),
        action_token="action.x",
        effect_features=("effect.stable",),
    )
    assert EpisodicProjection._from_validated(**fields) == EpisodicProjection(**fields)


def test_public_construction_still_validates_tokens() -> None:
    with pytest.raises(EpisodicMemoryError):
        EpisodicProjection(sense_ids=("bad token",))
