from symbiont.interpretation import interpret_study
from symbiont.study import (
    METRICS,
    ConditionSummary,
    MetricSummary,
    PairedDeltaSummary,
    StudyResult,
)


def _study_with_deltas(deltas: dict[str, float]) -> StudyResult:
    baseline_metrics = {}
    variant_metrics = {}
    paired = {}
    for metric in METRICS:
        base = 0.50
        delta = deltas.get(metric, 0.0)
        baseline_metrics[metric] = MetricSummary(base, 0.01, base - 0.01, base + 0.01)
        variant_metrics[metric] = MetricSummary(base + delta, 0.01, base + delta - 0.01, base + delta + 0.01)
        paired[metric] = PairedDeltaSummary(
            mean=delta,
            stdev=0.005 if delta else 0.0,
            minimum=delta - 0.002 if delta else 0.0,
            maximum=delta + 0.002 if delta else 0.0,
            direction_agreement=1.0,
        )
    return StudyResult(
        title="synthetic interpretation",
        parameter="poison_fraction",
        seeds=(1, 2, 3, 4, 5),
        baseline=ConditionSummary("baseline", 0.0, 5, baseline_metrics),
        variant=ConditionSummary("variant", 0.12, 5, variant_metrics),
        paired_deltas=paired,
    )


def test_interpretation_distinguishes_benefit_and_harm():
    interpretation = interpret_study(
        _study_with_deltas({"detection_rate": 0.05, "calibration_error": 0.03})
    )
    by_metric = {finding.metric: finding for finding in interpretation.findings}

    assert by_metric["detection_rate"].classification == "improved"
    assert by_metric["detection_rate"].evidence == "strong"
    assert by_metric["calibration_error"].classification == "worsened"
    assert by_metric["calibration_error"].evidence == "strong"
    assert 0 <= interpretation.confidence <= 1


def test_strong_effect_suggests_midpoint_follow_up():
    interpretation = interpret_study(_study_with_deltas({"precision": -0.04}))
    follow = interpretation.follow_up

    assert follow.parameter == "poison_fraction"
    assert follow.baseline == 0.0
    assert follow.variant == 0.06
    assert follow.recommended_seed_count >= 7
