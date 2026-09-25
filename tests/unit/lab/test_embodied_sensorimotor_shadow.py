from __future__ import annotations

import pytest

from symbiont_lab.studies.learning.embodied_sensorimotor_shadow import (
    _condition_actions,
    run_embodied_sensorimotor_shadow,
)


def test_shadow_conditions_preserve_causal_actions_and_zero_control():
    actions = [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]]
    assert _condition_actions(actions, condition="causal", seed=3) == actions
    assert _condition_actions(actions, condition="no_action", seed=3) == [
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 0.0],
    ]


def test_shadow_rejects_short_protocol():
    with pytest.raises(ValueError, match="at least 64"):
        run_embodied_sensorimotor_shadow((1,), ticks=63)
