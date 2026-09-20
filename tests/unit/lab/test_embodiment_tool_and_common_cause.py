from __future__ import annotations

import pytest

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.embodiment.tool_body_distinction import run_tool_body_distinction_study
from symbiont_lab.studies.embodiment.hidden_common_cause import run_hidden_common_cause_study


def test_e2_replay_and_bounds():
    result = run_tool_body_distinction_study(seeds=(101,127), steps=200)
    replay = run_tool_body_distinction_study(seeds=(101,127), steps=200)
    assert result == replay
    assert result.replay_deterministic
    for value in (
        result.body_detection_rate,
        result.attached_assimilation_rate,
        result.remote_assimilation_rate,
        result.uncontrolled_assimilation_rate,
    ):
        assert 0.0 <= value <= 1.0


def test_e6_replay_and_bounds():
    result = run_hidden_common_cause_study(seeds=(101,127), steps=200)
    replay = run_hidden_common_cause_study(seeds=(101,127), steps=200)
    assert result == replay
    assert result.replay_deterministic
    for value in (
        result.true_positive_rate,
        result.confounded_false_positive_rate,
        result.independent_false_positive_rate,
    ):
        assert 0.0 <= value <= 1.0


def test_e2_e6_protocols_registered():
    e2 = get_protocol("embodiment.tool-body-distinction")
    e6 = get_protocol("embodiment.hidden-common-cause")
    assert e2(seeds=(101,), steps=100).seeds == (101,)
    assert e6(seeds=(101,), steps=100).seeds == (101,)


def test_e2_e6_reject_short_runs():
    with pytest.raises(ValueError):
        run_tool_body_distinction_study(seeds=(101,), steps=10)
    with pytest.raises(ValueError):
        run_hidden_common_cause_study(seeds=(101,), steps=10)
