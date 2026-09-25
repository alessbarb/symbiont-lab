import pytest
from symbiont.core.assimilation import AssimilationAction, InformationAssimilator


def test_endogenous_value_actions_and_bound():
    a = InformationAssimilator(max_deferred=1)
    assert (
        a.evaluate(novelty=1, surprise=1, attention=1, reliability=1).action
        is AssimilationAction.INCORPORATE
    )
    assert (
        a.evaluate(novelty=0.5, surprise=0.2, attention=0.2, reliability=0.6).action
        is AssimilationAction.DEFER
    )
    assert (
        a.evaluate(novelty=0.5, surprise=0.2, attention=0.2, reliability=0.6).action
        is AssimilationAction.REJECT
    )


def test_checkpoint_round_trip():
    a = InformationAssimilator()
    a.evaluate(novelty=1, surprise=0, attention=1, reliability=1)
    b = InformationAssimilator.from_checkpoint(a.checkpoint())
    assert b.assimilated == 1
    with pytest.raises(ValueError):
        b.evaluate(novelty=2, surprise=0, attention=0, reliability=0)
