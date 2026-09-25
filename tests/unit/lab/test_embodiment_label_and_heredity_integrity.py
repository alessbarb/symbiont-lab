from __future__ import annotations

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.embodiment.heredity_leakage_challenge import (
    run_heredity_leakage_challenge_study,
)
from symbiont_lab.studies.embodiment.label_invariance import run_label_invariance_study


def test_e8_label_invariance_replay():
    result = run_label_invariance_study(seeds=(101, 127), steps=80)
    replay = run_label_invariance_study(seeds=(101, 127), steps=80)
    assert result == replay
    assert result.replay_deterministic
    assert 0.0 <= result.invariant_rate <= 1.0


def test_e7_heredity_leakage_replay():
    result = run_heredity_leakage_challenge_study(seeds=(101, 127))
    replay = run_heredity_leakage_challenge_study(seeds=(101, 127))
    assert result == replay
    assert result.replay_deterministic
    assert 0.0 <= result.no_leak_rate <= 1.0


def test_e7_e8_protocols_registered():
    e7 = get_protocol("embodiment.heredity-leakage-challenge")
    e8 = get_protocol("embodiment.label-invariance")
    assert e7(seeds=(101,)).seeds == (101,)
    assert e8(seeds=(101,), steps=40).seeds == (101,)
