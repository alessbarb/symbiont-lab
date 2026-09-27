from symbiont.core.model import Observation

from symbiont.core.social.ledger import SocialClaim, SocialEvidenceLedger
from symbiont.core.social.source_evidence import SourceEvidenceOutcome
from symbiont.simulation import EventContext
from symbiont_lab.studies.attention.causal import _online_indices
from symbiont_lab.studies.attention.retrospective import _ScoredEvent
from symbiont_lab.studies.common.causal_selection import (
    OrderStatisticHistory as _OrderStatisticHistory,
)
from symbiont_lab.studies.common.causal_selection import (
    historical_threshold as _historical_threshold,
)
from symbiont_lab.studies.evidence.noise_sweep import run_evidence_noise_sweep
from symbiont_lab.studies.evidence.second_look import run_second_look_study


def _scored(step: int, *, novelty: float = 0.0, random_score: float = 1.0) -> _ScoredEvent:
    return _ScoredEvent(
        event=EventContext(
            step=step,
            host_index=0,
            truth_label="benign:normal",
            is_threat=False,
            phase="warmup" if step < 50 else "pre_drift",
            drift_state="pre_drift",
            observation=Observation(0.2, 0.2, 0.2, 0.2, 0.2),
        ),
        risk=0.2,
        novelty=novelty,
        random_score=random_score,
    )


def test_zero_novelty_startup_does_not_consume_front_of_budget():
    scored = [_scored(step) for step in range(100)]

    indices, forced = _online_indices(scored, strategy="novelty", budget=10)
    steps = [scored[index].event.step for index in indices]

    assert len(indices) == 10
    assert min(steps) >= 38
    assert not any(step < 6 for step in steps)
    assert forced == 10


def test_online_order_statistics_match_reference_sorting_exactly():
    values = [((index * 37) % 101) / 100 for index in range(160)] + [0.0] * 40 + [0.5] * 40
    history = _OrderStatisticHistory()
    reference: list[float] = []

    for index, value in enumerate(values):
        if index >= 32:
            for target_rate in (0.01, 0.05, 0.12, 0.20, 0.50, 0.95):
                assert history.threshold(target_rate, 0.35) == _historical_threshold(
                    reference,
                    target_rate,
                    0.35,
                )
        history.add(value)
        reference.append(value)


def test_identical_vote_replay_does_not_manufacture_trust_evidence():
    ledger = _ledger_with_five_sources("initial")
    baseline = _trust(ledger)
    samples = {source: list(state.samples) for source, state in ledger.source_states.items()}

    for _ in range(50):
        _reconcile(ledger, "claim-0", "initial")

    assert {source: list(state.samples) for source, state in ledger.source_states.items()} == (
        samples
    )
    assert _trust(ledger) == baseline


def test_second_look_exposes_exact_world_and_selection_digests():
    low = run_second_look_study(
        hosts=8,
        steps=70,
        seed=211,
        threat_rate=0.05,
        budget=12,
        sensor_noise=0.08,
    )
    high = run_second_look_study(
        hosts=8,
        steps=70,
        seed=211,
        threat_rate=0.05,
        budget=12,
        sensor_noise=0.30,
    )

    assert low.world_digest == high.world_digest
    assert {row.strategy: row.selected_event_digest for row in low.outcomes} == {
        row.strategy: row.selected_event_digest for row in high.outcomes
    }


def test_noise_sweep_accepts_only_exactly_paired_worlds_and_selections():
    result = run_evidence_noise_sweep(
        seeds=(211, 223),
        noise_levels=(0.08, 0.30),
        hosts=8,
        steps=70,
        threat_rate=0.05,
        budget_per_1000=15,
    )

    assert result.seeds == (211, 223)
    assert result.noise_levels == (0.08, 0.30)


def _ledger_with_five_sources(evidence_ref: str = "initial") -> SocialEvidenceLedger:
    ledger = SocialEvidenceLedger()
    for index in range(5):
        claim_id = f"claim-{index}"
        ledger.receive_claim(
            SocialClaim(
                claim_id=claim_id,
                source_id=f"source-{index}",
                root_evidence_ids=frozenset(),
                parent_claim_ids=frozenset(),
                payload="M-H-M-H-M",
                received_tick=0,
                freshness=1.0,
            )
        )
        _reconcile(ledger, claim_id, evidence_ref, agree=index < 4)
    return ledger


def _reconcile(ledger, claim_id: str, evidence_ref: str, *, agree: bool = True) -> None:
    ledger.record_local_reconciliation(
        claim_id=claim_id,
        tick=1,
        outcome=(SourceEvidenceOutcome.AGREEMENT if agree else SourceEvidenceOutcome.CONTRADICTION),
        compatibility=0.9,
        quality=0.9,
        freshness=1.0,
        evidence_ref=evidence_ref,
    )


def _trust(ledger: SocialEvidenceLedger) -> dict[str, tuple]:
    return {
        source: (
            state.source_reliability,
            state.agreements,
            state.contradictions,
            len(state.samples),
        )
        for source, state in ledger.source_states.items()
    }
