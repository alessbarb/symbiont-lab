from symbiont.budget import _ScoredEvent
from symbiont.causal_budget import _online_indices
from symbiont.collective import CollectiveMemory
from symbiont.evidence import run_second_look_study
from symbiont.evidence_noise_sweep import run_evidence_noise_sweep
from symbiont.model import Observation
from symbiont.simulation import EventContext


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
    assert min(steps) >= 38  # six ineligible + 32 historical eligible scores
    assert not any(step < 6 for step in steps)
    assert forced == 10  # with a deterministic high tiebreak, quota is spent at the end


def test_identical_vote_replay_does_not_manufacture_trust_evidence():
    collective = CollectiveMemory()
    fingerprint = "M-H-M-H-M"
    for index in range(5):
        assert collective.report(
            fingerprint,
            threat=index < 4,
            confidence=0.9,
            source=f"source-{index}",
            evidence_id="initial",
        )
    collective.recalibrate_sources(min_peers=4)

    baseline = {
        source: (state.score, state.evaluations)
        for source, state in collective.source_trust.items()
    }
    reports = collective.patterns[fingerprint].reports

    for _ in range(50):
        assert not collective.report(
            fingerprint,
            True,
            0.9,
            "source-0",
            evidence_id="initial",
        )
        collective.recalibrate_sources(min_peers=4)

    assert collective.patterns[fingerprint].reports == reports
    assert {
        source: (state.score, state.evaluations)
        for source, state in collective.source_trust.items()
    } == baseline


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
    assert {
        row.strategy: row.selected_event_digest for row in low.outcomes
    } == {
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
