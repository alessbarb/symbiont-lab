from __future__ import annotations

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.learning.replay_efficiency import _intervals
from symbiont_lab.studies.learning.replay_pressure_curve import ReplayDose


def test_replay_efficiency_protocol_registered():
    assert get_protocol("learning.replay-efficiency").__name__ == "run_replay_efficiency_study"


def test_replay_efficiency_is_loss_gain_per_added_step():
    doses = (
        ReplayDose(pressure=0.0, epochs=2, steps=12, test_loss=3.0, accuracy=0.0),
        ReplayDose(pressure=0.25, epochs=4, steps=21, test_loss=2.1, accuracy=0.1),
        ReplayDose(pressure=0.5, epochs=5, steps=30, test_loss=1.8, accuracy=0.2),
    )
    intervals = _intervals(doses)

    assert len(intervals) == 2
    assert intervals[0].added_steps == 9
    assert intervals[0].loss_gain == 0.9
    assert intervals[0].gain_per_step == 0.1
    assert intervals[1].added_steps == 9
    assert abs(intervals[1].gain_per_step - (0.3 / 9)) < 1e-12
