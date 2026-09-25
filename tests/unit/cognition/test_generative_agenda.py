from __future__ import annotations

import pytest

from symbiont.cognition.generative import (
    AgendaContaminationError,
    AgendaProgress,
    AgendaSource,
    GenerativeAgenda,
    GenerativeTarget,
    TargetStatus,
)


def target(target_id: str = "target-1") -> GenerativeTarget:
    return GenerativeTarget(
        target_id, AgendaSource.UNCERTAINTY, ("state-ref",), 0, 0.8, 0.7, 2, 0.6
    )


def test_selection_is_deterministic_and_resolved_targets_leave_agenda():
    agenda = GenerativeAgenda()
    agenda.add_target(target())
    selected = agenda.select(tick=1)
    assert [item.target.target_id for item in selected] == ["target-1"]
    agenda.resolve("target-1")
    assert agenda.select(tick=2) == ()
    assert agenda.targets[0].status is TargetStatus.RESOLVED


def test_no_progress_suppresses_repeated_target_and_later_reactivates_it():
    agenda = GenerativeAgenda(max_reselection_without_progress=2, suppression_duration=4)
    agenda.add_target(target())
    agenda.record_progress("target-1", tick=1, progress=AgendaProgress())
    agenda.record_progress("target-1", tick=2, progress=AgendaProgress())
    assert agenda.select(tick=2) == ()
    agenda.record_progress("target-1", tick=7, progress=AgendaProgress(uncertainty_changed=True))
    assert agenda.select(tick=7)


def test_external_target_is_release_blocking_contamination():
    agenda = GenerativeAgenda()
    with pytest.raises(AgendaContaminationError):
        agenda.reject_external_target("benchmark-answer")
    assert agenda.agenda_contamination_count == 1
