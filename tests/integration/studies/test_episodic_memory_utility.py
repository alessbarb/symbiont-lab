from __future__ import annotations

from symbiont.modeling.experience import EpistemicStatus, ExperienceRecord, SourceKind
from symbiont_lab.studies.learning.episodic_memory_utility import (
    evaluate_episodic_predictive_utility,
    run_episodic_memory_utility_study,
)


ORG = "study-org"


def rec(tick: int, state: str, outcome: str) -> ExperienceRecord:
    return ExperienceRecord(
        record_id=f"transition.{tick}",
        organism_id=ORG,
        tick_class=tick,
        context_tokens=("sense.shared", state),
        action_token="action.same",
        outcome_tokens=(outcome,),
        epistemic_status=EpistemicStatus.OBSERVED,
        evidence_refs=(f"e.{tick}",),
        confidence_class=7,
        source_kind=SourceKind.ACTION_OUTCOME,
    )


def test_state_conditioned_memory_beats_action_only_when_action_is_ambiguous() -> None:
    train = tuple(
        rec(
            tick * 10,
            "state.a" if tick % 2 == 0 else "state.b",
            "outcome.a" if tick % 2 == 0 else "outcome.b",
        )
        for tick in range(40)
    )
    test = tuple(
        rec(
            1000 + tick * 10,
            "state.a" if tick % 2 == 0 else "state.b",
            "outcome.a" if tick % 2 == 0 else "outcome.b",
        )
        for tick in range(20)
    )

    report = evaluate_episodic_predictive_utility(
        train,
        test,
        organism_id=ORG,
    )

    assert report.test_records == 20
    assert report.memory_coverage == 1.0
    assert report.memory_top1_accuracy > report.action_only_top1_accuracy
    assert report.state_conditioned_gain_vs_action_only > 0.0



def test_replicated_episodic_utility_study_is_reproducible() -> None:
    first = run_episodic_memory_utility_study(
        seeds=(101, 127, 149),
        ticks=128,
    )
    second = run_episodic_memory_utility_study(
        seeds=(101, 127, 149),
        ticks=128,
    )

    assert first == second
    assert first.mean_memory_coverage > 0.95
    assert first.mean_state_conditioned_gain_vs_action_only > 0.0
    assert first.mean_state_conditioned_gain_vs_global > 0.0
    assert len(first.results) == 3
