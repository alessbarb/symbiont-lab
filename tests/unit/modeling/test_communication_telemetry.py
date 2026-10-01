import pytest

from symbiont.modeling import (
    CommunicationEvent,
    CommunicationTelemetry,
    GroundingEvent,
    SequenceChannel,
    SequenceMessage,
    SymbolSequence,
)


def event(event_id="e1", tick=1, kind="EMIT", sender="a", receiver="b", message="m"):
    return CommunicationEvent(
        event_id, tick, kind, sender, receiver, message, ("symbol.x",), 1, "delivered"
    )


def test_event_is_canonical_and_round_trips():
    item = event()
    assert CommunicationEvent.restore(item.to_dict()) == item
    assert item.digest == CommunicationEvent.restore(item.to_dict()).digest
    assert "ground_truth" not in item.to_dict()


def test_telemetry_deduplicates_and_records_truncation():
    telemetry = CommunicationTelemetry(max_events=2, max_events_per_tick=2)
    assert telemetry.record(event("e1", 1))
    assert not telemetry.record(event("e1", 1))
    assert telemetry.record(event("e2", 2))
    assert telemetry.record(event("e3", 3))
    assert len(telemetry.events) == 2
    assert telemetry.history_truncated
    assert telemetry.earliest_available_tick == 2


def test_per_tick_ceiling_fails_closed_without_fabricating_event():
    telemetry = CommunicationTelemetry(max_events=4, max_events_per_tick=1)
    assert telemetry.record(event("e1", 1))
    assert not telemetry.record(event("e2", 1))
    assert [item.event_id for item in telemetry.events] == ["e1"]
    assert telemetry.history_truncated


def test_grounding_per_tick_ceiling_is_bounded():
    telemetry = CommunicationTelemetry(max_events=4, max_events_per_tick=1)
    grounding = GroundingEvent("g1", 1, "b", "m", 1, 0, 1, 1, 0, 1)
    assert telemetry.record_grounding(grounding)
    assert not telemetry.record_grounding(GroundingEvent("g2", 1, "b", "m2", 1, 0, 1, 1, 0, 1))
    assert telemetry.history_truncated


def test_telemetry_sink_failure_does_not_change_delivery_or_grounding():
    telemetry = CommunicationTelemetry(max_events=1, max_events_per_tick=1)
    channel = SequenceChannel(authorized_pairs={("a", "b")}, telemetry=telemetry)
    from symbiont.modeling import SequenceGroundingLedger

    receiver = SequenceGroundingLedger("b")
    channel.deliver(
        SequenceMessage(SymbolSequence(("symbol.x",)), "a", "b", 3), receiver=receiver, tick=3
    )
    receiver.observe_outcome(("outcome.ok",), tick=3)
    # The local ledger changed even though the bounded observation sink was full.
    assert receiver.predict_exact(SymbolSequence(("symbol.x",))) == ("outcome.ok",)


def test_checkpoint_restore_does_not_duplicate_events():
    telemetry = CommunicationTelemetry(max_events=4)
    telemetry.record(event())
    restored = CommunicationTelemetry.restore(telemetry.checkpoint())
    assert restored.export() == telemetry.export()
    assert not restored.record(event())


def test_sequence_channel_emits_only_after_real_delivery():
    telemetry = CommunicationTelemetry()
    channel = SequenceChannel(authorized_pairs={("a", "b")}, telemetry=telemetry)
    from symbiont.modeling import SequenceGroundingLedger

    receiver = SequenceGroundingLedger("b")
    channel.deliver(
        SequenceMessage(SymbolSequence(("symbol.x",)), "a", "b", 3), receiver=receiver, tick=3
    )
    assert len(telemetry.events) == 1
    assert telemetry.events[0].event_kind == "DELIVER"
    assert telemetry.events[0].receiver_id == "b"


def test_event_rejects_unbounded_or_malformed_payload():
    with pytest.raises(ValueError):
        event(message="x" * 129)
    with pytest.raises(ValueError):
        CommunicationEvent("e", 1, "EMIT", "a", "b", "m", (), 1, "delivered")
