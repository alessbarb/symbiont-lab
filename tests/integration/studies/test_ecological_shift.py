import pytest

from symbiont_lab.experiments.runner import ExperimentRunner
from symbiont_lab.experiments.spec import ExperimentSpec
from symbiont_lab.studies.heritage.ecological_shift import run_ecological_shift_study


def test_ecological_shift_is_deterministic_paired_and_rate_scoped():
    kwargs = dict(
        source_seeds=(3, 7),
        source_threat_rate=0.06,
        target_threat_rates=(0.02, 0.06),
        target_offset=1009,
        hosts=16,
        steps=120,
        poison_fraction=0.08,
        heterogeneity=0.12,
        heritage_limit=8,
    )
    first = run_ecological_shift_study(**kwargs)
    second = run_ecological_shift_study(**kwargs)

    assert first == second
    assert first.target_seeds == (1012, 1016)
    assert 50 < first.analysis_split_step < 120
    assert len(first.comparisons) == 4
    assert len(first.world_digest) == 64

    for row in first.comparisons:
        assert len(row.world_digest) == 64
        assert row.analysis_split_step == first.analysis_split_step
        assert row.target_threat_rate in {0.02, 0.06}

    for rate in (0.02, 0.06):
        summary = first.summaries[rate]
        assert summary.comparisons == 2
        assert "early_attention_delta" in summary.metrics
        assert "late_attention_delta" in summary.metrics
        assert 0 <= summary.metrics["global_brier_delta"].pairs <= 2


def test_ecological_shift_rejects_invalid_designs():
    with pytest.raises(ValueError):
        run_ecological_shift_study(source_seeds=())
    with pytest.raises(ValueError):
        run_ecological_shift_study(source_seeds=(1,), target_offset=0)
    with pytest.raises(ValueError):
        run_ecological_shift_study(source_seeds=(1, 1))
    with pytest.raises(ValueError):
        run_ecological_shift_study(target_threat_rates=(0.01, 0.01))
    with pytest.raises(ValueError):
        run_ecological_shift_study(target_threat_rates=(1.1,))


def test_ecological_shift_rejects_source_target_seed_collision():
    with pytest.raises(ValueError):
        run_ecological_shift_study(
            source_seeds=(3, 1012),
            target_offset=1009,
            hosts=2,
            steps=10,
        )


def test_experiment_runner_executes_ecological_shift_protocol(tmp_path):
    spec = ExperimentSpec(
        experiment_id="heritage.ecological-shift-test",
        protocol="heritage.ecological-shift",
        protocol_version=1,
        hosts=10,
        steps=90,
        seed=13,
        threat_rate=0.05,
        poison_fraction=0.08,
        heterogeneity=0.12,
        seeds=[13],
        extra_params={
            "heritage": {
                "source_threat_rate": 0.05,
                "target_threat_rates": [0.02, 0.05],
                "target_offset": 1009,
                "heritage_limit": 6,
            }
        },
    )

    result, manifest, run_dir = ExperimentRunner(tmp_path).run(spec)

    assert manifest.protocol == "heritage.ecological-shift"
    assert manifest.world_digest == result.world_digest
    assert manifest.world_digest != "na"
    assert len(result.comparisons) == 2
    assert (run_dir / "manifest.json").is_file()
    assert (run_dir / "metrics.json").is_file()
    assert manifest.metrics["result"]["analysis_split_step"] == result.analysis_split_step
