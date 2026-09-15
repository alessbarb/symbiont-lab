import pytest
from symbiont.core.social import RelationLedger, RelationValence

def test_relation_valence_is_evidence_based():
 l=RelationLedger(); assert l.observe("a","b",benefit=2).valence is RelationValence.POSITIVE; assert l.observe("a","b",cost=3).valence is RelationValence.NEGATIVE

def test_engine_supports_exchange_and_finite_competition():
 from symbiont.core.interactions import EcologicalResourcePool
 from symbiont.core.social import SocialInteractionEngine
 e=SocialInteractionEngine(EcologicalResourcePool({"food":1.0}))
 assert e.exchange("a","b","food",0.4).granted == 0.4
 out=e.compete([("a","food",0.8),("b","food",0.8)])
 assert sum(x.granted for x in out) == 0.6


def test_relation_ledger_checkpoint_round_trip_preserves_aggregate_evidence() -> None:
    ledger = RelationLedger()
    ledger.observe("a", "b", benefit=2.0)
    ledger.observe("a", "b", cost=0.5)
    restored = RelationLedger.from_checkpoint(ledger.checkpoint())
    assert restored.relations == ledger.relations


def test_social_habitat_requires_authorized_members() -> None:
    from symbiont.core.interactions import EcologicalResourcePool
    from symbiont.core.social import SocialHabitat
    habitat = SocialHabitat(EcologicalResourcePool({"food": 1.0}))
    assert habitat.admit("a") and habitat.admit("b")
    assert habitat.exchange("a", "b", "food", 0.2).granted == 0.2
    habitat.release("b")
    try:
        habitat.exchange("a", "b", "food", 0.1)
    except ValueError:
        pass
    else:
        raise AssertionError("released organisms must not interact")


def test_habitat_checkpoint_roundtrip_preserves_boundary_and_evidence() -> None:
    from symbiont.core.interactions import EcologicalResourcePool
    from symbiont.core.social import SocialHabitat
    habitat = SocialHabitat(EcologicalResourcePool({"food": 10.0}), max_members=3)
    assert habitat.admit("a") and habitat.admit("b")
    habitat.exchange("a", "b", "food", 2.0)
    restored = SocialHabitat.from_checkpoint(habitat.checkpoint())
    assert restored.members == ("a", "b")
    assert restored.engine.pool.snapshot() == {"food": 8.0}
    assert restored.engine.ledger.relations[0].observations == 1


def test_habitat_checkpoint_rejects_duplicate_members() -> None:
    from symbiont.core.interactions import EcologicalResourcePool
    from symbiont.core.social import SocialHabitat
    payload = SocialHabitat(EcologicalResourcePool({"food": 1.0})).checkpoint()
    payload["members"] = ["a", "a"]
    with pytest.raises(ValueError, match="duplicate"):
        SocialHabitat.from_checkpoint(payload)


def test_relation_tracks_reciprocity_conflict_and_freshness() -> None:
    ledger = RelationLedger()
    relation = ledger.observe("a", "b", benefit=1.0, reciprocal=True, conflict=True, tick=4)
    assert relation.reciprocal_observations == 1
    assert relation.conflicts == 1
    assert relation.freshness(4) == 1.0
    assert 0.0 < relation.freshness(36) < 1.0
    restored = RelationLedger.from_checkpoint(ledger.checkpoint()).relations[0]
    assert restored == relation


def test_social_habitat_can_suspend_and_resume_pair_interaction() -> None:
    from symbiont.core.interactions import EcologicalResourcePool
    from symbiont.core.social import SocialHabitat
    habitat = SocialHabitat(EcologicalResourcePool({"food": 2.0}))
    habitat.admit("a"); habitat.admit("b")
    habitat.suspend("a", "b")
    with pytest.raises(ValueError, match="suspended"):
        habitat.exchange("a", "b", "food", 1.0)
    checkpoint = habitat.checkpoint()
    restored = SocialHabitat.from_checkpoint(checkpoint)
    with pytest.raises(ValueError, match="suspended"):
        restored.exchange("a", "b", "food", 1.0)
    assert restored.resume("a", "b")
    assert restored.exchange("a", "b", "food", 1.0).granted == 1.0
