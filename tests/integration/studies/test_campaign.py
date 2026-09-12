from symbiont_lab.archive.studies import StudyRecord
from symbiont_lab.studies.campaigns.campaign import analyze_campaign


def _record(
    record_id: str,
    *,
    parent: str | None,
    baseline: float,
    variant: float,
    confidence: float = 0.8,
    summary: str = "The variant consistently changed the system.",
) -> StudyRecord:
    return StudyRecord(
        record_id=record_id,
        created_at="2026-01-01T00:00:00+00:00",
        source="test",
        parent_record_id=parent,
        base_spec={"hosts": 10, "steps": 20},
        study={
            "title": record_id,
            "parameter": "poison_fraction",
            "seeds": [1, 2, 3, 4, 5],
            "baseline": {"parameter_value": baseline},
            "variant": {"parameter_value": variant},
        },
        interpretation={
            "summary": summary,
            "confidence": confidence,
            "follow_up": {
                "parameter": "poison_fraction",
                "baseline": baseline,
                "variant": (baseline + variant) / 2,
                "recommended_seed_count": 7,
                "rationale": "refine the threshold",
            },
        },
    )


def test_campaign_marks_narrow_high_confidence_line_as_converged():
    root = _record("root", parent=None, baseline=0.0, variant=0.20)
    middle = _record("middle", parent="root", baseline=0.0, variant=0.10)
    latest = _record("latest", parent="middle", baseline=0.0, variant=0.05)

    assessment = analyze_campaign([latest, middle, root])

    assert assessment.status == "converged"
    assert assessment.proposal is None
    assert assessment.initial_span == 0.20
    assert assessment.latest_span == 0.05


def test_campaign_repeated_low_confidence_condition_requests_more_evidence():
    root = _record("root", parent=None, baseline=0.0, variant=0.12, confidence=0.5)
    latest = _record("latest", parent="root", baseline=0.0, variant=0.12, confidence=0.5)

    assessment = analyze_campaign([latest, root])

    assert assessment.status == "increase_evidence"
    assert assessment.proposal is not None
    assert assessment.proposal.recommended_seed_count == 10
    assert assessment.proposal.parent_record_id == "latest"


def test_campaign_stops_escalating_after_three_weak_non_discriminating_studies():
    weak = "No strong paired effect is established yet; treat the current result as exploratory."
    root = _record("root", parent=None, baseline=0.0, variant=0.05, confidence=0.3, summary=weak)
    middle = _record("middle", parent="root", baseline=0.0, variant=0.10, confidence=0.3, summary=weak)
    latest = _record("latest", parent="middle", baseline=0.0, variant=0.15, confidence=0.3, summary=weak)

    assessment = analyze_campaign([latest, middle, root])

    assert assessment.status == "no_robust_effect"
    assert assessment.proposal is None
    assert "close it" in assessment.summary
