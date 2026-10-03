import pytest

from symbiont.modeling import (
    ClaimGraph,
    ModeledOrganismRuntime,
    SocialChannel,
    SocialClaim,
    SocialEpistemicStatus,
    SocialEvidenceLedger,
)


def _chain():
    a = SocialEvidenceLedger("A")
    b = SocialEvidenceLedger("B")
    c = SocialEvidenceLedger("C")
    channel = SocialChannel(authorized_pairs={("A", "B"), ("B", "C")})
    root = a.originate(proposition_tokens=("signal.foo", "outcome.bar"), evidence_id="e.a", tick=1)
    ab = a.retransmit(root.claim_id, receiver_id="B", tick=2)
    channel.deliver(ab, sender_id="A", receiver=b, tick=2, source=a)
    bc = b.retransmit(ab.claim_id, receiver_id="C", tick=3)
    channel.deliver(bc, sender_id="B", receiver=c, tick=3, source=b)
    return a, b, c, root, ab, bc


def test_claim_hash_serialization_and_faithful_dag_chain():
    a, _, c, root, _, leaf = _chain()
    assert SocialClaim.restore(root.canonical_payload()) == root
    assert root.content_hash == SocialClaim.restore(root.canonical_payload()).content_hash
    assert c.graph.root_evidence_ids(leaf) == ("e.a",)
    assert c.graph.independent_root_count((leaf,)) == 1
    assert c.graph.ancestors(leaf.claim_id)
    assert leaf.transmission_depth == 2
    assert a.costs["retransmission"] == 1


def test_duplicate_spoof_and_unauthorized_delivery_rejected():
    a, b, _, root, _, _ = _chain()
    with pytest.raises(ValueError):
        b.receive(next(iter(b.claims)), sender_id="spoof", tick=3)
    with pytest.raises(ValueError):
        b.receive(next(iter(b.claims)), sender_id="A", tick=3)
    channel = SocialChannel(authorized_pairs={("A", "B")})
    receiver = SocialEvidenceLedger("C")
    with pytest.raises(ValueError):
        channel.deliver(
            a.retransmit(root.claim_id, receiver_id="C", tick=4),
            sender_id="A",
            receiver=receiver,
            tick=4,
            source=a,
        )


def test_mass_copy_does_not_inflate_independent_roots():
    a = SocialEvidenceLedger("A")
    root = a.originate(proposition_tokens=("x",), evidence_id="root", tick=0)
    ledgers = [SocialEvidenceLedger(f"B{i}") for i in range(10)]
    channel = SocialChannel(authorized_pairs={("A", f"B{i}") for i in range(10)})
    leaves = []
    for i, ledger in enumerate(ledgers):
        claim = a.retransmit(root.claim_id, receiver_id=ledger.organism_id, tick=i + 1)
        channel.deliver(claim, sender_id="A", receiver=ledger, tick=i + 1, source=a)
        leaves.append(next(iter(ledger.claims)))
    assert len(leaves) == 10
    assert a.graph.independent_root_count(leaves) == 1


def test_independent_confirmation_and_contradiction_remain_separate():
    _, b, _, _, ab, _ = _chain()
    supported = b.assess(ab.claim_id, evidence_id="e.b", supported=True, tick=4)
    contradicted = b.assess(ab.claim_id, evidence_id="e.b2", supported=False, tick=5)
    assert supported.status is SocialEpistemicStatus.SOCIAL_SUPPORTED
    assert contradicted.status is SocialEpistemicStatus.SOCIAL_CONTRADICTED
    assert {item.evidence_id for item in b.assessments} == {"e.b", "e.b2"}
    assert b.graph.root_evidence_ids(ab) == ("e.a",)
    assert b.graph.independent_root_count((ab,)) == 1


def test_mutation_freshness_forgetting_checkpoint_and_restore():
    a = SocialEvidenceLedger("A")
    root = a.originate(proposition_tokens=("x",), evidence_id="e", tick=1)
    mutated = a.mutate_and_retransmit(
        root.claim_id, receiver_id="B", proposition_tokens=("y",), tick=2
    )
    assert mutated.mutation_depth == 1
    assert a.graph.root_evidence_ids(mutated) == ("e",)
    assert a.freshness(mutated.claim_id, current_tick=2) < 1.0
    restored = SocialEvidenceLedger.restore(a.checkpoint(), organism_id="A")
    assert restored.graph.root_evidence_ids(mutated) == ("e",)
    assert restored.costs == a.costs
    assert restored.forget(current_tick=100, max_age=10)
    assert restored.graph.independent_root_count(restored.graph.claims) == 1


def test_graph_rejects_cycles_and_bound_overflow():
    graph = ClaimGraph()
    root = SocialClaim.originate(
        organism_id="A", proposition_tokens=("x",), evidence_id="e", tick=0
    )
    graph.add(root)
    bad = SocialClaim(
        "bad",
        ("x",),
        "A",
        "A",
        ("e",),
        ("missing",),
        0,
        None,
        SocialEpistemicStatus.SOCIAL_CLAIM,
        0,
        0,
        0,
    )
    with pytest.raises(ValueError):
        graph.add(bad)
    with pytest.raises(ValueError):
        SocialClaim(
            "bad2",
            tuple(f"t{i}" for i in range(33)),
            "A",
            "A",
            ("e",),
            (),
            0,
            None,
            SocialEpistemicStatus.SOCIAL_CLAIM,
            0,
            0,
            0,
        )


def test_social_claim_is_not_private_experience_or_training_target():
    a = SocialEvidenceLedger("A")
    claim = a.originate(proposition_tokens=("x",), evidence_id="e", tick=0)
    assert not hasattr(claim, "weights")
    assert not hasattr(claim, "corpus")
    assert claim.epistemic_status is SocialEpistemicStatus.SOCIAL_CLAIM


def test_modeled_runtime_checkpoint_and_observatory_projection_are_passive():
    runtime = ModeledOrganismRuntime(organism_id="runtime-A", bootstrap_semantic_senses=False)
    claim = runtime.originate_social_claim(proposition_tokens=("x",), evidence_id="e.runtime")
    projection = runtime.cultural_observations()
    assert projection["claim_count"] == 1
    assert projection["independent_roots"] == 1
    assert projection["claim_lineage"][0]["claim_id"] == claim.claim_id
    restored = ModeledOrganismRuntime.from_checkpoint(
        runtime.checkpoint(), bootstrap_semantic_senses=False
    )
    assert restored.cultural_observations() == runtime.cultural_observations()
