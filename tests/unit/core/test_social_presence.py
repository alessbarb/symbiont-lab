import pytest

from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.runtime import OrganismRuntime
from symbiont.core.social import SocialHabitat


def test_runtime_can_perceive_only_opaque_admitted_presence() -> None:
    habitat = SocialHabitat(EcologicalResourcePool({"food": 1.0}))
    habitat.admit("a")
    habitat.admit("b")
    runtime = OrganismRuntime(organism_id="a", social_habitat=habitat)
    signals = runtime.observe_social_presence()
    assert [(item.observer_id, item.target_id, item.available) for item in signals] == [("a", "b", True)]
    assert not hasattr(signals[0], "metadata")


def test_presence_requires_authorized_membership() -> None:
    habitat = SocialHabitat(EcologicalResourcePool({"food": 1.0}))
    with pytest.raises(ValueError):
        habitat.observe_presence("unknown")

