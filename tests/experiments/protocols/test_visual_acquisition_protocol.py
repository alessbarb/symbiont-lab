"""Visual Acquisition v1 D1: mechanical scoring, decision and staging contracts.

These tests check arithmetic and rules on synthetic traces; they say nothing
about whether Symbiont acquires visual structure.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from symbiont.cognition.learning import huber_loss
from symbiont_lab.experiments.loader import load_experiment_file
from symbiont_lab.studies.learning.visual_acquisition import (
    ARM_B_ABLATION,
    MIN_VISUAL_TARGETS,
    a_beats_b_on_intersection,
    decision_inputs,
    run_visual_acquisition_study,
    score_window,
    summarize,
    visual_targets,
)

pytestmark = pytest.mark.experiment_contract


def test_visual_targets_require_all_sources_visual() -> None:
    sensors = [
        SimpleNamespace(cognitive_name="v", source_ids=("rec.120",)),
        SimpleNamespace(cognitive_name="mixed", source_ids=("rec.120", "rec.3")),
        SimpleNamespace(cognitive_name="body", source_ids=("rec.3",)),
    ]
    assert visual_targets(sensors, frozenset({"rec.120"})) == frozenset({"v"})


def test_baselines_use_same_series_and_loss_prequentially() -> None:
    series = [0.0, 1.0, 0.0, 1.0]
    rows = [({"t": value}, {"t": [0.25]}) for value in series]
    scored = score_window(rows, targets=frozenset({"t"}), start=2, stop=4)["t"]
    assert scored["ticks"] == 2
    assert scored["learned_loss"] == pytest.approx(0.25)
    assert scored["persist_loss"] == pytest.approx((huber_loss(-1.0) + huber_loss(1.0)) / 2)
    assert scored["mean_loss"] == pytest.approx((huber_loss(-0.5) + huber_loss(1 - 1 / 3)) / 2)
    assert scored["zero_loss"] == pytest.approx((huber_loss(0.0) + huber_loss(1.0)) / 2)


def test_window_stops_at_horizon() -> None:
    rows = [({"t": float(i)}, {"t": [1.0]}) for i in range(10)]
    assert score_window(rows, targets=frozenset({"t"}), start=4, stop=6)["t"]["ticks"] == 2


def test_only_targets_predicted_through_whole_window_count() -> None:
    rows = {
        "full": {
            "ticks": 4,
            "learned_loss": 0.1,
            "persist_loss": 0.3,
            "mean_loss": 0.2,
            "zero_loss": 0.5,
        }
    }
    rows["partial"] = {
        "ticks": 3,
        "learned_loss": 9.0,
        "persist_loss": 0.0,
        "mean_loss": 0.0,
        "zero_loss": 0.0,
    }
    summary = summarize(rows, window=4)
    assert summary["visual_targets_with_predictors"] == 1
    assert summary["gain_persist"] == pytest.approx(0.2)
    assert summary["gain_zero"] == pytest.approx(0.4)


def _targets(names, loss):
    return {name: {"learned_loss": loss} for name in names}


def test_a_vs_b_compares_only_the_intersection() -> None:
    a = _targets([f"t{i}" for i in range(10)], 0.1)
    a.update(_targets(["only_a"], 9.0))
    b = _targets([f"t{i}" for i in range(2, 12)], 0.2)
    result = a_beats_b_on_intersection(a, b)
    assert result["intersection"] == 8 and result["a_better"] is True
    few_b = _targets([f"t{i}" for i in range(MIN_VISUAL_TARGETS - 1)], 0.0)
    assert a_beats_b_on_intersection(a, few_b)["a_better"] is True


def _row(seed, *, targets=10, gains=0.1, b=None, x_predictors=0):
    full = _targets([f"t{i}" for i in range(targets)], 0.1)
    perf = {
        "assessable": targets >= MIN_VISUAL_TARGETS,
        "gain_persist": gains,
        "gain_mean": gains,
        "gain_zero": gains,
    }
    b_full = b if b is not None else {}
    return {
        "seed": seed,
        "visual_predictors_at_x": x_predictors,
        "arms": {
            "A": {"horizons": {"1000": {"performance": perf, "full_window_targets": full}}},
            "B": {"horizons": {"1000": {"full_window_targets": b_full}}},
        },
    }


def test_failure_taxonomy_follows_preregistration() -> None:
    def overall(rows):
        return decision_inputs(rows, horizon="1000")["d1"]

    assert overall([_row(613), _row(617)]) == "passed"
    assert overall([_row(613), _row(617, targets=3), _row(619, targets=2)]) == "not_assessable"
    assert overall([_row(613), _row(617, x_predictors=1)]) == "preexisting_structure_at_X"
    assert overall([_row(613), _row(617, gains=-0.1)]) == "no_predictive_utility"
    b_equal = _targets([f"t{i}" for i in range(10)], 0.05)
    assert overall([_row(613), _row(617, b=b_equal)]) == "acquisition_not_isolated"


def test_arm_b_ablation_is_lab_owned_and_complete() -> None:
    assert ARM_B_ABLATION.as_dict() == {"plasticity_enabled": False, "predictor_promotion": False}


def test_performance_requires_a_single_frozen_horizon() -> None:
    with pytest.raises(ValueError, match="single frozen horizon"):
        run_visual_acquisition_study(seeds=(), horizons=(500, 1000), report_performance=True)


def test_development_stage_never_computes_performance() -> None:
    spec = load_experiment_file(
        "experiments/learning/visual-acquisition-v1/development/experiment.toml"
    )
    assert spec.protocol == "learning.visual-acquisition-v1"
    assert list(spec.seeds) == [101, 127, 149]
    assert spec.extra_params["vision"]["report_performance"] is False
    assert spec.extra_params["vision"]["horizons"] == [500, 1000, 1500, 2000]


def test_d1_v2_changes_only_the_protected_environment() -> None:
    from symbiont_lab.physics3d.environments import environment_recipe, nursery_support_amount

    v1 = environment_recipe("vision-nursery-d1-v1")
    v2 = environment_recipe("vision-nursery-d1-v2")
    assert v2["fixtures"] == v1["fixtures"]  # identical stimulus
    assert "metabolic_support" not in v1
    support = v2["metabolic_support"]
    assert support == {"kind": "bounded_maintenance", "rate_per_tick": 0.6, "ceiling_fraction": 0.9}
    # Bounded, deterministic, never refills to full.
    assert nursery_support_amount(v2, energy_reserve=800.0, max_energy=1600.0) == 0.6
    assert nursery_support_amount(v2, energy_reserve=1439.9, max_energy=1600.0) == pytest.approx(
        0.1
    )
    assert nursery_support_amount(v2, energy_reserve=1500.0, max_energy=1600.0) == 0.0
    assert nursery_support_amount(v1, energy_reserve=100.0, max_energy=1600.0) == 0.0


def test_runner_applies_the_acquisition_guard_every_tick() -> None:
    import inspect

    from symbiont_lab.studies.learning import visual_acquisition as va

    for fn in (va.make_state_x, va.run_arm):
        source = inspect.getsource(fn)
        assert "RunGuard(RunKind.ACQUISITION_VISION)" in source
        assert "_guard_step(runtime, guard" in source


def test_d1_v2_development_spec() -> None:
    spec = load_experiment_file(
        "experiments/learning/visual-acquisition-v1/d1-v2-development/experiment.toml"
    )
    vision = spec.extra_params["vision"]
    assert vision["environment"] == "vision-nursery-d1-v2"
    assert vision["report_performance"] is False
    assert vision["horizons"] == [500, 1000, 1500, 2000, 2500, 3000, 3500, 4000]
    assert list(spec.seeds) == [101, 127, 149]
