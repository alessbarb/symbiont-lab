from __future__ import annotations

import pytest

from symbiont_lab.studies.common.actuator_probing_calendar import probing_calendar


def test_calendar_length_matches_window_ticks():
    calendar = probing_calendar(organism_id="org-1", actuator_id="actuator.a", window_index=0, window_ticks=8)
    assert len(calendar) == 8


def test_calendar_is_balanced_even_length():
    calendar = probing_calendar(organism_id="org-1", actuator_id="actuator.a", window_index=0, window_ticks=8)
    assert sum(calendar) == 4


def test_calendar_is_balanced_within_one_odd_length():
    calendar = probing_calendar(organism_id="org-1", actuator_id="actuator.a", window_index=0, window_ticks=7)
    assert sum(calendar) in (3, 4)


def test_calendar_is_deterministic_for_same_inputs():
    first = probing_calendar(organism_id="org-1", actuator_id="actuator.a", window_index=2, window_ticks=10)
    second = probing_calendar(organism_id="org-1", actuator_id="actuator.a", window_index=2, window_ticks=10)
    assert first == second


def test_calendar_differs_across_window_index():
    windows = [
        probing_calendar(organism_id="org-1", actuator_id="actuator.a", window_index=i, window_ticks=12)
        for i in range(5)
    ]
    assert len(set(windows)) > 1


def test_calendar_differs_across_actuator_id():
    a = probing_calendar(organism_id="org-1", actuator_id="actuator.a", window_index=0, window_ticks=12)
    b = probing_calendar(organism_id="org-1", actuator_id="actuator.b", window_index=0, window_ticks=12)
    assert a != b


def test_calendar_differs_across_organism_id():
    a = probing_calendar(organism_id="org-1", actuator_id="actuator.a", window_index=0, window_ticks=12)
    b = probing_calendar(organism_id="org-2", actuator_id="actuator.a", window_index=0, window_ticks=12)
    assert a != b


def test_calendar_rejects_non_positive_window_ticks():
    with pytest.raises(ValueError):
        probing_calendar(organism_id="org-1", actuator_id="actuator.a", window_index=0, window_ticks=0)
