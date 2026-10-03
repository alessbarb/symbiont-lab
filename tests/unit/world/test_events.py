import pytest

from environment.events import EventJournal, WorldEvent


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


def test_journal_incremental_indexes_match_replay_semantics():
    journal = EventJournal()
    events = [
        _event(event_id="e1", tick=0),
        _event(event_id="e2", tick=0),
        _event(event_id="e3", tick=1),
        _event(event_id="e4", tick=2),
    ]
    for event in events:
        journal.append(event)

    assert journal.events_for_tick(0) == tuple(events[:2])
    assert journal.events_for_tick(1) == (events[2],)
    assert journal.events_for_tick(99) == ()
    assert journal.tail(2) == tuple(events[-2:])
    assert journal.snapshot_range(1, 3) == journal.snapshot()[1:3]

    page, cursor, has_more = journal.page_after("e1", limit=2)
    assert page == (events[1], events[2])
    assert cursor == "e3"
    assert has_more is True


def test_page_after_preserves_legacy_first_duplicate_id_semantics():
    journal = EventJournal()
    first = _event(event_id="dup", tick=0)
    second = _event(event_id="middle", tick=1)
    duplicate = _event(event_id="dup", tick=2)
    for event in (first, second, duplicate):
        journal.append(event)

    page, _, _ = journal.page_after("dup", limit=8)
    assert page == (second, duplicate)


def test_prefix_digest_is_stable_across_snapshot_restore_and_prefixes():
    journal = EventJournal()
    for index in range(5):
        journal.append(_event(event_id=f"e{index}", tick=index // 2))

    restored = EventJournal.from_snapshot(journal.snapshot())
    assert restored.prefix_digest() == journal.prefix_digest()
    for count in range(6):
        assert restored.prefix_digest(count) == journal.prefix_digest(count)

    changed = journal.snapshot()
    changed[0] = {**changed[0], "event_id": "different"}
    changed_journal = EventJournal.from_snapshot(changed)
    assert changed_journal.prefix_digest(1) != journal.prefix_digest(1)
