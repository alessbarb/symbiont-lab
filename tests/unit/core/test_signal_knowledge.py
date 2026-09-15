import pytest

from symbiont.core.signal_identity import SignalIdentity, claim_id
from symbiont.core.signal_knowledge import SignalKnowledgeEngine
from symbiont.core.signal_knowledge_types import SignalObservation, SignalObservationBatch


def obs(identity, name, *, selected=True, value=1.0, quality="nominal"):
    return SignalObservation(identity.signal_id(name), True, selected, value, quality)


def test_identity_and_claims_are_opaque_and_deterministic():
    identity = SignalIdentity(bytes(range(32)))
    token = identity.signal_id("compute.logical_cpu")
    assert token.startswith("signal.") and len(token) == 71
    assert "compute" not in token
    assert claim_id(token, "stability", None, None).startswith("claim.")


def test_invalid_observation_and_duplicate_batch_are_rejected():
    identity = SignalIdentity(b"k" * 32)
    with pytest.raises(ValueError):
        SignalObservation(identity.signal_id("x"), True, True, float("nan"))
    item = obs(identity, "x")
    with pytest.raises(ValueError):
        SignalObservationBatch(1, (item, item))


def test_engine_counts_only_selected_valid_readings_and_is_strictly_monotonic():
    identity = SignalIdentity(b"k" * 32)
    engine = SignalKnowledgeEngine()
    token = identity.signal_id("x")
    engine.observe(SignalObservationBatch(1, (obs(identity, "x", selected=False),)))
    engine.observe(SignalObservationBatch(2, (obs(identity, "x", quality="degraded"),)))
    profile = engine.view()[0]
    assert profile["observed_opportunities"] == 1
    assert profile["valid_observations"] == 0
    with pytest.raises(ValueError):
        engine.observe(SignalObservationBatch(2, (SignalObservation(token, True, True, 1.0),)))


def test_engine_emits_stability_hypothesis_after_warmup():
    identity = SignalIdentity(b"k" * 32)
    engine = SignalKnowledgeEngine()
    for tick in range(1, 33):
        engine.observe(SignalObservationBatch(tick, (obs(identity, "x"),)))
    claim = engine.view()[0]["claims"][0]
    assert claim["kind"] == "stability"
    assert claim["status"] == "hypothesis"
    assert engine.drain_events()


def test_checkpoint_roundtrip_keeps_public_claim_state():
    identity = SignalIdentity(b"k" * 32)
    engine = SignalKnowledgeEngine()
    for tick in range(1, 3):
        engine.observe(SignalObservationBatch(tick, (obs(identity, "x"),)))
    restored = SignalKnowledgeEngine.from_checkpoint(engine.checkpoint())
    assert restored.view() == engine.view()
