"""Vision Acquisition v1 D1: mechanical scoring and decision contracts (§5, §7).

These tests check arithmetic and rules on synthetic traces; they say nothing
about whether Symbiont acquires visual structure.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from symbiont.cognition.learning import huber_loss
from symbiont_lab.experiments.loader import load_experiment_file
from symbiont_lab.studies.learning.vision_acquisition import (
    MIN_VISUAL_TARGETS,
    decision_inputs,
    score_late_window,
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
    ticks = [({"t": value}, {"t": [0.25]}) for value in series]
    scored = score_late_window(ticks, targets=frozenset({"t"}), late_start=2)["t"]
    assert scored["ticks"] == 2
    assert scored["learned_loss"] == pytest.approx(0.25)
    # tick 2: prev 1.0, mean of (0, 1) = 0.5 ; tick 3: prev 0.0, mean of (0, 1, 0)
    assert scored["persist_loss"] == pytest.approx((huber_loss(-1.0) + huber_loss(1.0)) / 2)
    assert scored["mean_loss"] == pytest.approx((huber_loss(-0.5) + huber_loss(1 - 1 / 3)) / 2)


def test_only_targets_predicted_through_whole_window_count() -> None:
    rows = {"full": {"ticks": 4, "learned_loss": 0.1, "persist_loss": 0.3, "mean_loss": 0.2}}
    rows["partial"] = {"ticks": 3, "learned_loss": 9.0, "persist_loss": 0.0, "mean_loss": 0.0}
    summary = summarize(rows, window=4)
    assert summary["visual_targets_with_predictors"] == 1
    assert summary["gain_persist"] == pytest.approx(0.2)
    assert summary["assessable"] is (1 >= MIN_VISUAL_TARGETS)


def _seed(seed, a_gain, b_assessable, b_gain, x_predictors=0):
    arm = lambda assessable, gain: {  # noqa: E731
        "assessable": assessable,
        "gain_persist": gain,
        "gain_mean": gain,
    }
    return {
        "seed": seed,
        "visual_predictors_at_x": x_predictors,
        "arms": {"A": arm(True, a_gain), "B": arm(b_assessable, b_gain)},
    }


def test_decision_rules_follow_preregistration() -> None:
    passing = decision_inputs([_seed(613, 0.1, False, None), _seed(617, 0.2, True, 0.05)])
    assert passing == {
        "assessable_seeds": [613, 617],
        "d1_assessable": True,
        "c2_utility": True,
        "c3_novelty": True,
        "c4_acquisition_not_sensors": True,
    }
    utility_fails = decision_inputs([_seed(613, 0.1, False, None), _seed(617, -0.1, False, None)])
    assert utility_fails["c2_utility"] is False
    sensors_suffice = decision_inputs([_seed(613, 0.1, True, 0.3), _seed(617, 0.1, False, None)])
    assert sensors_suffice["c4_acquisition_not_sensors"] is False
    preexisting = decision_inputs([_seed(613, 0.1, False, None, x_predictors=2)])
    assert preexisting["c3_novelty"] is False and preexisting["d1_assessable"] is False


def test_held_out_spec_is_the_preregistered_one() -> None:
    spec = load_experiment_file("experiments/learning/vision-acquisition-d1/experiment.toml")
    assert spec.protocol == "learning.vision-acquisition-d1"
    assert list(spec.seeds) == [613, 617, 619]
    assert spec.steps == 2000
    assert spec.extra_params["vision"] == {"late_window": 400}
    dev = load_experiment_file("experiments/learning/vision-acquisition-d1-dev/experiment.toml")
    assert not set(dev.seeds) & set(spec.seeds)
