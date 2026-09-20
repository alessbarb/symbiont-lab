from __future__ import annotations

import pytest

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.embodiment.causal_revision_sequence import (
    run_causal_revision_sequence_study,
)


def test_e4_is_deterministic_and_reports_all_phases():
    result = run_causal_revision_sequence_study(
        seeds=(101,),
        steps=160,
    )
    replay = run_causal_revision_sequence_study(
        seeds=(101,),
        steps=160,
    )
    assert result == replay
    assert result.replay_deterministic
    assert len(result.per_seed) == 1
    names = [phase.name for phase in result.per_seed[0].phases]
    assert names == [
        "stable_a",
        "sham",
        "permutation",
        "restored_a",
        "broken_effector",
        "repaired",
        "transplant_b",
        "return_a",
    ]


def test_e4_does_not_encode_h1_as_software_success():
    result = run_causal_revision_sequence_study(seeds=(101,), steps=160)
    seed = result.per_seed[0]

    assert isinstance(seed.permutation_revision, bool)
    assert isinstance(seed.break_revision, bool)
    assert isinstance(seed.transplant_revision, bool)
    assert isinstance(seed.sham_quieter_than_real_changes, bool)
    assert isinstance(result.h1_supported, bool)


def test_e4_protocol_is_registered():
    protocol = get_protocol("embodiment.causal-revision-sequence")
    result = protocol(seeds=(101,), steps=160)
    assert result.seeds == (101,)
    assert result.phase_ticks == 20


def test_e4_rejects_invalid_steps():
    with pytest.raises(ValueError):
        run_causal_revision_sequence_study(seeds=(101,), steps=159)
    with pytest.raises(ValueError):
        run_causal_revision_sequence_study(seeds=(101,), steps=162)
