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



def test_recurring_resolved_target_reopens_without_duplicate_agenda_entry():
    agenda = GenerativeAgenda()
    agenda.add_target(target())
    agenda.resolve("target-1")

    agenda.observe_target(target())

    assert len(agenda.targets) == 1
    refreshed = agenda.targets[0]
    assert refreshed.status is TargetStatus.ELIGIBLE
    assert refreshed.recurrence == 3


def test_unchanged_recurring_target_does_not_break_anti_rumination_suppression():
    agenda = GenerativeAgenda(max_reselection_without_progress=2, suppression_duration=8)
    agenda.add_target(target())
    agenda.record_progress("target-1", tick=1, progress=AgendaProgress())
    agenda.record_progress("target-1", tick=2, progress=AgendaProgress())
    before = agenda.targets[0]
    assert before.status is TargetStatus.SUPPRESSED

    agenda.observe_target(target())

    after = agenda.targets[0]
    assert after.status is TargetStatus.SUPPRESSED
    assert after.suppressed_until == before.suppressed_until
    assert after.recurrence == before.recurrence + 1


def test_materially_changed_recurring_signal_can_reactivate_suppressed_target():
    agenda = GenerativeAgenda(max_reselection_without_progress=2, suppression_duration=8)
    agenda.add_target(target())
    agenda.record_progress("target-1", tick=1, progress=AgendaProgress())
    agenda.record_progress("target-1", tick=2, progress=AgendaProgress())

    changed = GenerativeTarget(
        "target-1",
        AgendaSource.UNCERTAINTY,
        ("state-ref", "new-evidence-ref"),
        3,
        0.4,
        0.7,
        1,
        0.9,
    )
    agenda.observe_target(changed)

    refreshed = agenda.targets[0]
    assert refreshed.status is TargetStatus.ELIGIBLE
    assert refreshed.no_progress_count == 0
