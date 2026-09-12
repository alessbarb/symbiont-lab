from __future__ import annotations

from symbiont.core.collective import CollectiveMemory


def test_evidence_replay_idempotence():
    memory = CollectiveMemory()
    fp = "H-M-L-M-L"

    # First report from agent-001
    fresh = memory.report(fp, threat=True, confidence=0.85, source="agent-001", evidence_id="ev-100")
    assert fresh is True

    # Replay identical report with same evidence_id
    replayed = memory.report(fp, threat=True, confidence=0.85, source="agent-001", evidence_id="ev-100")
    assert replayed is False

    # Consensus must reflect single report
    pattern = memory.patterns[fp]
    assert len(pattern.votes) == 1
