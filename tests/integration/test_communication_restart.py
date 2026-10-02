"""Longitudinal Integrity v1 §8: communication state survives a restart."""

from __future__ import annotations

import json

import pytest

from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.core.social.communication import ConsentBoundChannel, SignedMessage
from symbiont.core.social.exchange import ExchangeEnvelope
from symbiont.core.social.source_evidence import SourceEvidenceOutcome
from symbiont.host.checkpoint import CheckpointError

RUNTIME_KWARGS = dict(bootstrap_semantic_senses=True, discover_senses=False, min_samples=1)
PEER = "peer-a"


def _channel(organism_id: str) -> ConsentBoundChannel:
    channel = ConsentBoundChannel("habitat-test", b"shared-key")
    channel.authorize(PEER, organism_id)
    channel.authorize(organism_id, PEER)
    return channel


def _message(
    channel: ConsentBoundChannel, recipient: str, sequence: int, claim: str
) -> SignedMessage:
    envelope = ExchangeEnvelope(PEER, sequence, {claim: json.dumps({"payload": claim})})
    return channel.send(envelope, recipient)


def _restart(runtime: OrganismRuntime, channel: ConsentBoundChannel) -> OrganismRuntime:
    """Cross a real serialization boundary; the original object graph is discarded."""
    serialized = json.dumps(runtime.checkpoint())
    del runtime
    restored = OrganismRuntime.from_checkpoint(json.loads(serialized), **RUNTIME_KWARGS)
    restored.attach_communication_channel(channel)
    return restored


def _broadcast_reconciled(runtime: OrganismRuntime, claim: str) -> SignedMessage:
    runtime._epistemic_ledger.record_local_reconciliation(
        claim,
        tick=1,
        outcome=SourceEvidenceOutcome.AGREEMENT,
        compatibility=1.0,
        quality=1.0,
        freshness=1.0,
        evidence_ref=claim,
    )
    (message,) = runtime.broadcast_claims([PEER])
    return message


def test_replayed_envelope_stays_rejected_after_restart() -> None:
    runtime = OrganismRuntime(**RUNTIME_KWARGS)
    runtime.tick()
    channel = _channel(runtime.organism_id)
    runtime.attach_communication_channel(channel)
    runtime.receive_communication(_message(channel, runtime.organism_id, 1, "claim-1"))
    assert "claim-1" in runtime._epistemic_ledger.claims

    restored = _restart(runtime, channel)
    # An envelope at an already accepted sequence is a replay whatever it carries.
    restored.receive_communication(_message(channel, restored.organism_id, 1, "claim-stale"))

    assert "claim-stale" not in restored._epistemic_ledger.claims
    assert restored._exchange_guard.checkpoint() == {PEER: 1}
    restored.receive_communication(_message(channel, restored.organism_id, 2, "claim-2"))
    assert "claim-2" in restored._epistemic_ledger.claims


def test_outbound_sequence_continues_after_restart() -> None:
    runtime = OrganismRuntime(**RUNTIME_KWARGS)
    runtime.tick()
    channel = _channel(runtime.organism_id)
    runtime.attach_communication_channel(channel)
    runtime.receive_communication(_message(channel, runtime.organism_id, 1, "claim-1"))
    assert _broadcast_reconciled(runtime, "claim-1").sequence == 1

    restored = _restart(runtime, channel)
    restored.receive_communication(_message(channel, restored.organism_id, 2, "claim-2"))

    assert _broadcast_reconciled(restored, "claim-2").sequence == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("exchange_guard", ["peer-a"]),
        ("exchange_guard", {"peer-a": -1}),
        ("exchange_guard", {"peer-a": True}),
        ("exchange_guard", {"": 1}),
        ("exchange_sequence", -1),
        ("exchange_sequence", "3"),
        ("exchange_sequence", True),
    ],
)
def test_malformed_exchange_state_is_rejected(field: str, value: object) -> None:
    runtime = OrganismRuntime(**RUNTIME_KWARGS)
    runtime.tick()
    payload = json.loads(json.dumps(runtime.checkpoint()))
    payload[field] = value

    with pytest.raises(CheckpointError):
        OrganismRuntime.from_checkpoint(payload, **RUNTIME_KWARGS)
