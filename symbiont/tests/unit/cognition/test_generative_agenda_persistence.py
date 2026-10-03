from symbiont.cognition.generative import (
    AgendaProgress,
    AgendaSource,
    GenerativeAgenda,
    GenerativeTarget,
    TargetStatus,
)


def test_agenda_checkpoint_preserves_selection_progress_and_suppression():
    agenda = GenerativeAgenda(max_reselection_without_progress=1, suppression_duration=4)
    agenda.add_target(
        GenerativeTarget(
            target_id="target-0",
            source=AgendaSource.RECURRING_CONFLICT,
            source_refs=("internal-conflict",),
            created_tick=2,
            uncertainty=0.7,
            persistence=0.6,
            recurrence=3,
        )
    )
    agenda.select(tick=3)
    agenda.record_progress("target-0", tick=3, progress=AgendaProgress())

    restored = GenerativeAgenda.from_checkpoint(agenda.checkpoint())

    target = restored.targets[0]
    assert target.selection_count == 1
    assert target.no_progress_count == 1
    assert target.status is TargetStatus.SUPPRESSED
    assert target.suppressed_until == 7
    assert target.source_refs == ("internal-conflict",)


def test_agenda_checkpoint_rejects_non_object_targets():
    agenda = GenerativeAgenda()

    try:
        GenerativeAgenda.from_checkpoint({**agenda.checkpoint(), "targets": {}})
    except ValueError as exc:
        assert "invalid agenda checkpoint" in str(exc)
    else:
        raise AssertionError("invalid agenda checkpoint was accepted")
