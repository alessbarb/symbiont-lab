from __future__ import annotations

from symbiont.core.social.ledger import SocialClaim, SocialEvidenceLedger
from symbiont.core.social.source_evidence import SourceEvidenceOutcome


def _claim(claim_id: str, source: str) -> SocialClaim:
    return SocialClaim(
        claim_id=claim_id,
        source_id=source,
        root_evidence_ids=frozenset(),
        parent_claim_ids=frozenset(),
        payload="H-M-L-M-L",
        received_tick=0,
        freshness=1.0,
    )


def _reconcile(ledger: SocialEvidenceLedger, claim_id: str, evidence_ref: str) -> None:
    ledger.record_local_reconciliation(
        claim_id=claim_id,
        tick=1,
        outcome=SourceEvidenceOutcome.AGREEMENT,
        compatibility=0.85,
        quality=0.85,
        freshness=1.0,
        evidence_ref=evidence_ref,
    )


def test_evidence_replay_idempotence():
    ledger = SocialEvidenceLedger()
    ledger.receive_claim(_claim("claim-100", "agent-001"))
    ledger.receive_claim(_claim("claim-100", "agent-001"))  # replayed claim
    assert list(ledger.claims) == ["claim-100"]

    _reconcile(ledger, "claim-100", "ev-100")
    _reconcile(ledger, "claim-100", "ev-100")  # replayed evidence

    state = ledger.source_states["agent-001"]
    assert len(state.samples) == 1
    assert state.agreements == 1
