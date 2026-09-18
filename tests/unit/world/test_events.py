import pytest

from symbiont_world.events import EventJournal, WorldEvent


def _event(**overrides) -> WorldEvent:
    defaults = dict(
        event_id="e1",
        world_id="genesis",
        tick=0,
        kind="RESOURCE_ACQUIRED",
        actor="org-a",
        position="0,0",
    )
    defaults.update(overrides)
    return WorldEvent(**defaults)


def test_unknown_kind_rejected():
    with pytest.raises(ValueError):
        _event(kind="NOT_A_REAL_KIND")


def test_causal_and_contributing_ids_are_distinct_and_immutable():
    event = _event(causal_parent_ids=["p1"], contributing_event_ids=["c1", "c2"])
    assert event.causal_parent_ids == ("p1",)
    assert event.contributing_event_ids == ("c1", "c2")


def test_journal_is_append_only():
    journal = EventJournal()
    assert not hasattr(journal, "remove")
    assert not hasattr(journal, "update")
    journal.append(_event())
    assert len(journal) == 1


def test_journal_replay_returns_events_in_append_order():
    journal = EventJournal()
    first = _event(event_id="e1", tick=0)
    second = _event(event_id="e2", tick=1)
    journal.append(first)
    journal.append(second)
    assert journal.replay() == (first, second)
