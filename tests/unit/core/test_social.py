import pytest
from symbiont.core.social import RelationLedger, RelationValence

def test_relation_valence_is_evidence_based():
 l=RelationLedger(); assert l.observe("a","b",benefit=2).valence is RelationValence.POSITIVE; assert l.observe("a","b",cost=3).valence is RelationValence.NEGATIVE

def test_engine_supports_exchange_and_finite_competition():
 from symbiont.core.interactions import EcologicalResourcePool
 from symbiont.core.social.engine import SocialInteractionEngine
 e=SocialInteractionEngine(EcologicalResourcePool({"food":1.0}))
 assert e.exchange("a","b","food",0.4).granted == 0.4
 out=e.compete([("a","food",0.8),("b","food",0.8)])
 assert sum(x.granted for x in out) == 0.6
 assert {x.relation.target_id for x in out} == {"a", "b"}


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
    assert 0.0 < relation.reliability(4) < 1.0
    restored = RelationLedger.from_checkpoint(ledger.checkpoint()).relations[0]
    assert restored == relation


@pytest.mark.parametrize("kwargs", [
    {"benefit": float("nan")},
    {"cost": float("inf")},
    {"tick": True},
    {"channel": ""},
])
def test_relation_observation_rejects_non_finite_or_ambiguous_values(kwargs) -> None:
    with pytest.raises(ValueError, match="invalid relation observation"):
        RelationLedger().observe("a", "b", **kwargs)


def test_relation_checkpoint_rejects_non_finite_and_fractional_ticks() -> None:
    ledger = RelationLedger()
    payload = ledger.checkpoint()
    payload["relations"] = [{
        "source_id": "a", "target_id": "b", "support": float("nan"),
        "harm": 0.0, "observations": 1, "last_tick": 1,
    }]
    with pytest.raises(ValueError, match="invalid relation values"):
        RelationLedger.from_checkpoint(payload)
    payload["relations"][0]["support"] = 1.0
    payload["relations"][0]["last_tick"] = 1.5
    with pytest.raises(ValueError, match="invalid relation values"):
        RelationLedger.from_checkpoint(payload)


def test_resource_evidence_chooses_local_availability_and_roundtrips() -> None:
    from symbiont.core.social import ResourceEvidenceLedger

    ledger = ResourceEvidenceLedger()
    assert ledger.choose(("food", "water"), current_tick=0) == "food"
    ledger.observe("food", requested=1.0, granted=0.0, tick=1)
    ledger.observe("water", requested=1.0, granted=1.0, tick=1)
    assert ledger.choose(("food", "water"), current_tick=1) == "water"
    restored = ResourceEvidenceLedger.from_checkpoint(ledger.checkpoint())
    assert restored.evidence == ledger.evidence
    assert restored.choose(("food", "water"), current_tick=1) == "water"


def test_resource_evidence_revisits_stale_tokens_without_erasing_learning() -> None:
    from symbiont.core.social import ResourceEvidenceLedger

    ledger = ResourceEvidenceLedger()
    ledger.observe("food", requested=1.0, granted=0.0, tick=0)
    ledger.observe("water", requested=1.0, granted=1.0, tick=0)
    assert ledger.choose(("food", "water"), current_tick=1) == "water"
    # A local quiet period makes the old denial revisable rather than
    # permanent; no evaluator signal is involved.
    assert ledger.choose(("food", "water"), current_tick=8) == "food"


def test_resource_evidence_revises_a_previously_useful_token_after_repeated_denials() -> None:
    from symbiont.core.social import ResourceEvidenceLedger

    ledger = ResourceEvidenceLedger()
    for tick in range(3):
        ledger.observe("food", requested=1.0, granted=1.0, tick=tick)
        ledger.observe("water", requested=1.0, granted=1.0, tick=tick)
    # Aggregate history still favours food, but a new local run of denials
    # must create exploration pressure rather than pinning the runtime to it.
    ledger.observe("food", requested=1.0, granted=0.0, tick=3)
    assert ledger.choose(("food", "water"), current_tick=3) == "water"
    assert ledger.evidence[0].consecutive_denied == 1
    restored = ResourceEvidenceLedger.from_checkpoint(ledger.checkpoint())
    assert restored.evidence == ledger.evidence


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


def test_runtime_social_requests_are_explicit_and_stop_after_death() -> None:
    from symbiont.core.physiology import PhysiologyController, VitalState
    from symbiont.core.runtime import OrganismDeadError, OrganismRuntime
    from symbiont.core.interactions import EcologicalResourcePool
    from symbiont.core.social import SocialHabitat

    social = SocialHabitat(EcologicalResourcePool({"food": 1.0}))
    social.admit("a"); social.admit("b")
    runtime = OrganismRuntime(organism_id="a", social_habitat=social)
    assert runtime.request_social_exchange("b", "food", 0.25).granted == 0.25
    restored = OrganismRuntime.from_checkpoint(runtime.checkpoint(), social_habitat=social)
    assert restored.social_ledger.relations[0].support == 0.25
    assert restored.social_ledger.relations[0].channel == "food"
    dead = OrganismRuntime(organism_id="dead", physiology=PhysiologyController(state=VitalState.DEAD, death_tick=1), social_habitat=social)
    social.admit("dead")
    with pytest.raises(OrganismDeadError):
        dead.request_social_exchange("b", "food", 0.1)


def test_runtime_can_suspend_and_resume_its_own_social_channel() -> None:
    from symbiont.core.interactions import EcologicalResourcePool
    from symbiont.core.runtime import OrganismRuntime
    from symbiont.core.social import SocialHabitat

    social = SocialHabitat(EcologicalResourcePool({"food": 2.0}))
    social.admit("a"); social.admit("b")
    runtime = OrganismRuntime(organism_id="a", social_habitat=social)
    runtime.suspend_social_interaction("b")
    with pytest.raises(ValueError, match="suspended"):
        runtime.request_social_exchange("b", "food", 0.1)
    checkpoint = social.checkpoint()
    restored_social = SocialHabitat.from_checkpoint(checkpoint)
    restored = OrganismRuntime.from_checkpoint(runtime.checkpoint(), social_habitat=restored_social)
    assert restored.resume_social_interaction("b")
    assert restored.request_social_exchange("b", "food", 0.1).granted == 0.1


def test_runtime_can_reject_and_retain_directional_evidence() -> None:
    from symbiont.core.interactions import EcologicalResourcePool
    from symbiont.core.runtime import OrganismRuntime
    from symbiont.core.social import SocialHabitat

    social = SocialHabitat(EcologicalResourcePool({"food": 2.0}))
    social.admit("a"); social.admit("b")
    runtime = OrganismRuntime(organism_id="a", social_habitat=social)
    runtime.reject_social_interaction("b")
    relation = runtime.social_ledger.relations[0]
    assert relation.rejections == 1
    with pytest.raises(ValueError, match="suspended"):
        runtime.request_social_exchange("b", "food", 0.1)
    restored = OrganismRuntime.from_checkpoint(runtime.checkpoint(), social_habitat=social)
    assert restored.social_ledger.relations[0].rejections == 1


def test_runtime_competition_records_resource_availability_evidence() -> None:
    from symbiont.core.interactions import EcologicalResourcePool
    from symbiont.core.runtime import OrganismRuntime
    from symbiont.core.social import SocialHabitat

    social = SocialHabitat(EcologicalResourcePool({"food": 0.25}))
    social.admit("a"); social.admit("b")
    runtime = OrganismRuntime(organism_id="a", social_habitat=social)
    outcomes = runtime.request_social_competition([("a", "food", 1.0)])
    assert outcomes[0].granted == 0.25
    assert runtime.social_resource_ledger.evidence[0].availability == 0.25


def test_runtime_social_selection_uses_local_evidence_without_forcing_a_label() -> None:
    from symbiont.core.interactions import EcologicalResourcePool
    from symbiont.core.runtime import OrganismRuntime
    from symbiont.core.social import SocialHabitat

    social = SocialHabitat(EcologicalResourcePool({"food": 4.0}))
    for member in ("a", "good", "costly"):
        social.admit(member)
    runtime = OrganismRuntime(organism_id="a", social_habitat=social)
    runtime.social_ledger.observe("a", "good", benefit=4.0, tick=0)
    runtime.social_ledger.observe("a", "costly", cost=4.0, tick=0)
    assert runtime.select_social_opportunity().target_id == "good"


def test_runtime_selection_considers_the_best_opaque_channel_per_target() -> None:
    from symbiont.core.interactions import EcologicalResourcePool
    from symbiont.core.runtime import OrganismRuntime
    from symbiont.core.social import SocialHabitat

    social = SocialHabitat(EcologicalResourcePool({"food": 4.0, "water": 4.0}))
    for member in ("a", "mixed", "good"):
        social.admit(member)
    runtime = OrganismRuntime(organism_id="a", social_habitat=social)
    runtime.social_ledger.observe("a", "mixed", cost=4.0, channel="food", tick=0)
    runtime.social_ledger.observe("a", "mixed", benefit=4.0, channel="water", tick=0)
    runtime.social_ledger.observe("a", "good", benefit=1.0, channel="food", tick=0)
    assert runtime.select_social_opportunity().target_id == "mixed"


def test_runtime_autonomous_social_step_selects_opaque_target_and_resource() -> None:
    from symbiont.core.interactions import EcologicalResourcePool
    from symbiont.core.runtime import OrganismRuntime
    from symbiont.core.social import SocialHabitat

    social = SocialHabitat(EcologicalResourcePool({"opaque-resource": 1.0}))
    social.admit("a"); social.admit("b")
    runtime = OrganismRuntime(organism_id="a", social_habitat=social, social_exchange_quantum=0.2)
    outcome = runtime.autonomous_social_step()
    assert outcome is not None
    assert outcome.target_id == "b"
    assert outcome.resource == "opaque-resource"
    assert outcome.granted == 0.2
    assert runtime.social_resource_ledger.evidence[0].granted == 0.2
    restored = OrganismRuntime.from_checkpoint(runtime.checkpoint(), social_habitat=social)
    assert restored.effective_configuration()["social_exchange_quantum"] == 0.2
    assert restored.social_resource_ledger.evidence == runtime.social_resource_ledger.evidence


def test_social_exchange_charges_declared_cognitive_metabolism_and_roundtrips() -> None:
    from symbiont.core.interactions import EcologicalResourcePool
    from symbiont.core.metabolism import MetabolicLedger
    from symbiont.core.runtime import OrganismRuntime
    from symbiont.core.social import SocialHabitat

    zero = {kind: 0.0 for kind in ("observation", "cognition", "persistence", "maintenance")}
    habitat = SocialHabitat(EcologicalResourcePool({"food": 1.0}))
    habitat.admit("a"); habitat.admit("b")
    runtime = OrganismRuntime(
        organism_id="a", social_habitat=habitat, explicit_metabolism=True,
        metabolism=MetabolicLedger(replenishment=zero), social_exchange_cost=0.04,
    )
    runtime.request_social_exchange("b", "food", 0.1)
    assert runtime.metabolism.snapshot().spent["cognition"] == 0.04
    restored = OrganismRuntime.from_checkpoint(runtime.checkpoint(), social_habitat=habitat)
    assert restored.effective_configuration()["social_exchange_cost"] == 0.04




def test_runtime_death_releases_social_membership_once() -> None:
    from symbiont.core.metabolism import MetabolicLedger
    from symbiont.core.physiology import PhysiologyController
    from symbiont.core.runtime import OrganismRuntime
    from symbiont.core.social import SocialHabitat
    from symbiont.core.interactions import EcologicalResourcePool
    social = SocialHabitat(EcologicalResourcePool({"food": 1.0}))
    social.admit("a")
    metabolism = MetabolicLedger(replenishment={k: 0.0 for k in ("observation", "cognition", "persistence", "maintenance")})
    metabolism.charge("maintenance", metabolism.body_state.energy_reserve)
    runtime = OrganismRuntime(organism_id="a", social_habitat=social, metabolism=metabolism, explicit_metabolism=True,
                              physiology=PhysiologyController())
    runtime.tick()
    assert "a" not in social.members


def test_relation_evidence_is_scoped_to_opaque_channel() -> None:
    ledger = RelationLedger()
    first = ledger.observe("a", "b", benefit=1.0, channel="food", tick=1)
    second = ledger.observe("a", "b", cost=1.0, channel="water", tick=2)

    assert first.channel == "food"
    assert second.channel == "water"
    assert first.valence is RelationValence.POSITIVE
    assert second.valence is RelationValence.NEGATIVE
    restored = RelationLedger.from_checkpoint(ledger.checkpoint())
    assert restored.relations == ledger.relations
