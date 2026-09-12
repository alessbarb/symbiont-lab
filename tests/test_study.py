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
    assert all(summary.stdev >= 0 for summary in first.variant.metrics.values())
    assert all(0 <= summary.direction_agreement <= 1 for summary in first.paired_deltas.values())
    for metric in METRICS:
        assert first.delta(metric) == pytest.approx(
            first.variant.metrics[metric].mean - first.baseline.metrics[metric].mean
        )


def test_study_rejects_unsupported_parameter_and_empty_seeds():
    spec = ExperimentSpec(hosts=4, steps=10)
    with pytest.raises(ValueError):
        run_comparative_study(spec, parameter="hosts", baseline_value=4, variant_value=8, seeds=(1,))
    with pytest.raises(ValueError):
        run_comparative_study(spec, parameter="poison_fraction", baseline_value=0, variant_value=0.2, seeds=())
