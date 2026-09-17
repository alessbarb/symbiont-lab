import pytest

from symbiont.modeling import (
    CulturalComposite,
    SocialChannel,
    SocialEvidenceLedger,
)


def _three():
    a, b, c = SocialEvidenceLedger("A"), SocialEvidenceLedger("B"), SocialEvidenceLedger("C")
    channel = SocialChannel(authorized_pairs={("A", "B"), ("B", "C")})
    x = a.originate(proposition_tokens=("x",), evidence_id="e.x", tick=0)
    y = b.originate(proposition_tokens=("y",), evidence_id="e.y", tick=0)
    c1 = a.compose((x.claim_id,), tick=1)
    channel.deliver_composite(c1, sender_id="A", receiver=b, tick=2, source=a)
    c2 = b.compose((y.claim_id,), parent_composite_ids=(c1.composite_id,), tick=3, operation="extend")
    return a, b, c, channel, x, y, c1, c2


def test_composite_hash_roots_contributors_and_generation_are_causal():
    a, b, c, channel, x, y, c1, c2 = _three()
    z = c.originate(proposition_tokens=("z",), evidence_id="e.z", tick=4)
    channel.deliver_composite(c2, sender_id="B", receiver=c, tick=5, source=b)
    c3 = c.compose((z.claim_id,), parent_composite_ids=(c2.composite_id,), tick=6, operation="extend")
    assert c.composite_graph.root_evidence_ids(c3) == ("e.x", "e.y", "e.z")
    assert set(c3.contributing_organism_ids) == {"A", "B", "C"}
    assert c3.generation == 2
    assert c3.content_hash == CulturalComposite.restore(c3.canonical_payload()).content_hash
    assert c.composite_graph.ancestors(c3.composite_id) == tuple(sorted((c1.composite_id, c2.composite_id)))


def test_composition_rejects_missing_components_and_cycles_or_wrong_generation():
    ledger = SocialEvidenceLedger("A")
    with pytest.raises(ValueError):
        ledger.compose(("missing",), tick=0)
    claim = ledger.originate(proposition_tokens=("x",), evidence_id="e", tick=0)
    first = ledger.compose((claim.claim_id,), tick=1)
    with pytest.raises(ValueError):
        ledger.composite_graph.add(first, claim_graph=ledger.graph)
    malformed = CulturalComposite("bad", (claim.claim_id,), (first.composite_id,), ("A",), ("e",), 7, 2)
    with pytest.raises(ValueError):
        ledger.composite_graph.add(malformed, claim_graph=ledger.graph)


def test_composite_transport_is_bounded_and_preserves_component_identity():
    a, b, _, channel, _, _, c1, _ = _three()
    receiver = SocialEvidenceLedger("C")
    with pytest.raises(ValueError):
        channel.deliver_composite(c1, sender_id="spoof", receiver=receiver, tick=3, source=a)
    # The authorized receiver can acquire only the bounded component claims
    # referenced by the composite, not arbitrary source state.
    channel = SocialChannel(authorized_pairs={("A", "C")})
    channel.deliver_composite(c1, sender_id="A", receiver=receiver, tick=3, source=a)
    assert {claim.claim_id for claim in receiver.claims} == set(c1.component_claim_ids)
    assert receiver.composites == (c1,)


def test_replace_retire_checkpoint_and_clone_isolation():
    ledger = SocialEvidenceLedger("A")
    wrong = ledger.originate(proposition_tokens=("wrong",), evidence_id="e.wrong", tick=0)
    bad = ledger.compose((wrong.claim_id,), tick=1)
    ledger.assess(wrong.claim_id, evidence_id="e.contradict", supported=False, tick=2)
    correct = ledger.originate(proposition_tokens=("correct",), evidence_id="e.correct", tick=3)
    fixed = ledger.compose((correct.claim_id,), parent_composite_ids=(bad.composite_id,), tick=4, operation="replace", replace_component_claim_ids=(wrong.claim_id,))
    assert wrong.claim_id not in fixed.component_claim_ids
    retired = ledger.retire_composite(fixed.composite_id, tick=5)
    assert retired.retired and ledger.current_composites == ()
    restored = SocialEvidenceLedger.restore(ledger.checkpoint(), organism_id="A")
    assert restored.checkpoint() == ledger.checkpoint()
    child = SocialEvidenceLedger("child")
    assert not child.composites
    assert restored.costs["composition"] >= 3


def test_composite_does_not_create_independent_root():
    ledger = SocialEvidenceLedger("A")
    claim = ledger.originate(proposition_tokens=("x",), evidence_id="e", tick=0)
    composite = ledger.compose((claim.claim_id,), tick=1)
    assert ledger.composite_graph.root_evidence_ids(composite) == ("e",)
    assert len(ledger.composite_graph.root_evidence_ids(composite)) == 1


def test_composite_checkpoint_and_observatory_surface_are_passive():
    from symbiont.modeling import ModeledOrganismRuntime

    runtime = ModeledOrganismRuntime(organism_id="runtime-culture", bootstrap_semantic_senses=False)
    claim = runtime.originate_social_claim(proposition_tokens=("x",), evidence_id="e.runtime")
    composite = runtime.compose_cultural_claims((claim.claim_id,))
    observations = runtime.cultural_observations()
    assert observations["composite_count"] == 1
    assert observations["cultural_generation"] == composite.generation == 0
    assert observations["composite_lineage"][0]["roots"] == ("e.runtime",)
    restored = ModeledOrganismRuntime.from_checkpoint(runtime.checkpoint(), bootstrap_semantic_senses=False)
    assert restored.cultural_observations() == observations
