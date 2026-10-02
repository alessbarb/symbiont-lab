"""Longitudinal Integrity v1 §7.2: acquired social knowledge survives a restart."""

from __future__ import annotations

import json

import pytest

from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.core.social.communication import ConsentBoundChannel
from symbiont.core.social.exchange import ExchangeEnvelope
from symbiont.core.social.ledger import SocialEvidenceLedger
from symbiont.core.social.source_evidence import SourceEvidenceOutcome
from symbiont.host.checkpoint import CheckpointError, stamp_checkpoint_identity

RUNTIME_KWARGS = dict(bootstrap_semantic_senses=True, discover_senses=False, min_samples=1)
PEER = "peer-a"


def _developed() -> tuple[OrganismRuntime, ConsentBoundChannel]:
    runtime = OrganismRuntime(**RUNTIME_KWARGS)
    runtime.tick()
    channel = ConsentBoundChannel("habitat-test", b"shared-key")
    channel.authorize(PEER, runtime.organism_id)
    channel.authorize(runtime.organism_id, PEER)
    runtime.attach_communication_channel(channel)
    for sequence, claim in enumerate(("claim-1", "claim-2"), start=1):
        envelope = ExchangeEnvelope(PEER, sequence, {claim: json.dumps({"payload": claim})})
        runtime.receive_communication(channel.send(envelope, runtime.organism_id))
    runtime._epistemic_ledger.record_local_reconciliation(
        "claim-1",
        tick=1,
        outcome=SourceEvidenceOutcome.AGREEMENT,
        compatibility=0.75,
        quality=0.5,
        freshness=1.0,
        evidence_ref="evidence-1",
    )
    assert len(runtime.broadcast_claims([PEER])) == 1
    return runtime, channel


def _restart(runtime: OrganismRuntime, channel: ConsentBoundChannel) -> OrganismRuntime:
    serialized = json.dumps(runtime.checkpoint())
    del runtime
    restored = OrganismRuntime.from_checkpoint(json.loads(serialized), **RUNTIME_KWARGS)
    restored.attach_communication_channel(channel)
    return restored


def test_social_epistemic_state_round_trips() -> None:
    runtime, channel = _developed()
    before = runtime._epistemic_ledger

    restored = _restart(runtime, channel)
    after = restored._epistemic_ledger

    assert after.claims == before.claims
    assert after.reconciliations == before.reconciliations
    assert after.seen_evidence == before.seen_evidence
    assert after.source_states == before.source_states
    assert after.source_states[PEER].source_reliability == 1.0
    assert [claim.claim_id for claim in after.unresolved_claims()] == ["claim-2"]


def test_already_broadcast_claims_are_not_emitted_again_after_restart() -> None:
    runtime, channel = _developed()

    restored = _restart(runtime, channel)

    assert restored.broadcast_claims([PEER]) == []


def test_replayed_local_evidence_stays_rejected_after_restart() -> None:
    runtime, channel = _developed()
    restored = _restart(runtime, channel)

    restored._epistemic_ledger.record_local_reconciliation(
        "claim-1",
        tick=5,
        outcome=SourceEvidenceOutcome.CONTRADICTION,
        compatibility=0.0,
        quality=0.5,
        freshness=1.0,
        evidence_ref="evidence-1",
    )

    assert restored._epistemic_ledger.reconciliations["claim-1"] is SourceEvidenceOutcome.AGREEMENT


def test_restart_does_not_change_state_identity() -> None:
    runtime, channel = _developed()
    identity = runtime.state_hash()

    assert _restart(runtime, channel).state_hash() == identity


def test_ledger_checkpoint_is_json_and_round_trips_alone() -> None:
    runtime, _ = _developed()
    payload = json.loads(json.dumps(runtime._epistemic_ledger.checkpoint()))

    assert SocialEvidenceLedger.restore(payload) == runtime._epistemic_ledger
    assert SocialEvidenceLedger.restore(None) == SocialEvidenceLedger()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.update(schema_version=99),
        lambda payload: payload.update(claims="not-a-list"),
        lambda payload: payload["claims"][0].pop("source_id"),
        lambda payload: payload["reconciliations"].update({"unknown-claim": "agreement"}),
        lambda payload: payload["reconciliations"].update({"claim-1": "maybe"}),
        lambda payload: payload["source_states"][0]["samples"][0].update(tick=-1),
        lambda payload: payload.update(broadcast_claim_ids=["unknown-claim"]),
    ],
)
def test_malformed_ledger_checkpoint_is_rejected(mutate) -> None:
    runtime, _ = _developed()
    saved = json.loads(json.dumps(runtime.checkpoint()))
    mutate(saved["epistemic_ledger"])
    saved = stamp_checkpoint_identity(saved, transform="test-corruption")

    with pytest.raises(CheckpointError, match="epistemic ledger"):
        OrganismRuntime.from_checkpoint(saved, **RUNTIME_KWARGS)
