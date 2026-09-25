from symbiont_lab.studies.campaigns.comparative import (
    METRICS,
    ConditionSummary,
    MetricSummary,
    PairedDeltaSummary,
    StudyResult,
)
from symbiont_lab.studies.campaigns.interpretation import interpret_study


def _study_with_deltas(deltas: dict[str, float | None]) -> StudyResult:
    baseline_metrics = {}
    variant_metrics = {}
    paired = {}
    for metric in METRICS:
        base = 0.50
        delta = deltas.get(metric, 0.0)
        if delta is None:
            baseline_metrics[metric] = MetricSummary(None, None, None, None, 0)
            variant_metrics[metric] = MetricSummary(None, None, None, None, 0)
            paired[metric] = PairedDeltaSummary(
                mean=None,
                stdev=None,
                minimum=None,
                maximum=None,
                direction_agreement=None,
                pairs=0,
            )
            continue
        baseline_metrics[metric] = MetricSummary(
            base,
            0.01,
            base - 0.01,
            base + 0.01,
            5,
        )
        variant_metrics[metric] = MetricSummary(
            base + delta,
            0.01,
            base + delta - 0.01,
            base + delta + 0.01,
            5,
        )
        paired[metric] = PairedDeltaSummary(
            mean=delta,
            stdev=0.005 if delta else 0.0,
            minimum=delta - 0.002 if delta else 0.0,
            maximum=delta + 0.002 if delta else 0.0,
            direction_agreement=1.0,
            pairs=5,
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
        _study_with_deltas({"attention_recall": 0.05, "calibration_error": 0.03})
    )
    by_metric = {finding.metric: finding for finding in interpretation.findings}

    assert by_metric["attention_recall"].classification == "improved"
    assert by_metric["attention_recall"].evidence == "strong"
    assert by_metric["calibration_error"].classification == "worsened"
    assert by_metric["calibration_error"].evidence == "strong"
    assert 0 <= interpretation.confidence <= 1


def test_strong_effect_suggests_midpoint_follow_up():
    interpretation = interpret_study(_study_with_deltas({"attention_precision": -0.04}))
    follow = interpretation.follow_up

    assert follow.parameter == "poison_fraction"
    assert follow.baseline == 0.0
    assert follow.variant == 0.06
    assert follow.recommended_seed_count >= 7


def test_undefined_metric_is_not_interpreted_as_zero():
    interpretation = interpret_study(_study_with_deltas({"classification_recall": None}))
    by_metric = {finding.metric: finding for finding in interpretation.findings}

    finding = by_metric["classification_recall"]
    assert finding.classification == "undefined"
    assert finding.delta is None
    assert "undefined" in finding.text
