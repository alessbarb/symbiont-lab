import pytest

from symbiont.experiment import ExperimentSpec
from symbiont.study import METRICS, run_comparative_study


def test_comparative_study_is_reproducible_and_paired_by_seed():
    spec = ExperimentSpec(hosts=10, steps=80, threat_rate=0.03)
    first = run_comparative_study(
        spec,
        parameter="poison_fraction",
        baseline_value=0.0,
        variant_value=0.20,
        seeds=(2, 5, 9),
        title="poison resilience",
    )
    second = run_comparative_study(
        spec,
        parameter="poison_fraction",
        baseline_value=0.0,
        variant_value=0.20,
        seeds=(2, 5, 9),
        title="poison resilience",
    )

    assert first == second
    assert first.baseline.runs == 3
    assert first.variant.runs == 3
    assert set(first.baseline.metrics) == set(METRICS)
    assert set(first.paired_deltas) == set(METRICS)

    for summary in first.variant.metrics.values():
        if summary.stdev is not None:
            assert summary.stdev >= 0
        assert 0 <= summary.defined_runs <= first.variant.runs

    for summary in first.paired_deltas.values():
        if summary.direction_agreement is not None:
            assert 0 <= summary.direction_agreement <= 1
        assert 0 <= summary.pairs <= len(first.seeds)

    for metric in METRICS:
        baseline = first.baseline.metrics[metric].mean
        variant = first.variant.metrics[metric].mean
        delta = first.delta(metric)
        if baseline is None or variant is None:
            assert delta is None
        else:
            assert delta == pytest.approx(variant - baseline)


def test_zero_denominator_metrics_are_undefined_not_zero():
    study = run_comparative_study(
        ExperimentSpec(hosts=8, steps=70, threat_rate=0.0),
        parameter="threat_rate",
        baseline_value=0.0,
        variant_value=0.0,
        seeds=(3, 7),
        title="no threats",
    )

    assert study.baseline.metrics["attention_recall"].mean is None
    assert study.baseline.metrics["classification_recall"].mean is None
    assert study.paired_deltas["attention_recall"].mean is None
    assert study.paired_deltas["classification_recall"].pairs == 0
    assert study.baseline.metrics["attention_false_positive_rate"].mean is not None


def test_study_rejects_unsupported_parameter_and_empty_seeds():
    spec = ExperimentSpec(hosts=4, steps=10)
    with pytest.raises(ValueError):
        run_comparative_study(spec, parameter="hosts", baseline_value=4, variant_value=8, seeds=(1,))
    with pytest.raises(ValueError):
        run_comparative_study(spec, parameter="poison_fraction", baseline_value=0, variant_value=0.2, seeds=())
