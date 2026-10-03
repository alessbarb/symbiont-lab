from __future__ import annotations

import pytest

from symbiont.modeling import (
    ModeledOrganismRuntime,
    SequenceChannel,
    SequenceGroundingLedger,
    SequenceMessage,
    SymbolAction,
    SymbolSequence,
    choose_sequence,
)
from symbiont.modeling.symbols import MAX_HISTORY


def test_variable_length_sequences_are_opaque_and_ordered() -> None:
    runtime = ModeledOrganismRuntime(organism_id="sequence-a", bootstrap_semantic_senses=False)
    symbols = runtime.symbol_policy.symbol_space
    one = SymbolSequence((symbols[0],))
    two = SymbolSequence((symbols[0], symbols[1]))
    reversed_two = SymbolSequence((symbols[1], symbols[0]))
    assert one.sequence_id != two.sequence_id != reversed_two.sequence_id
    assert two.sequence_id != reversed_two.sequence_id


def test_sequence_bounds_and_decision_invariants() -> None:
    runtime = ModeledOrganismRuntime(organism_id="sequence-b", bootstrap_semantic_senses=False)
    symbols = runtime.symbol_policy.symbol_space
    with pytest.raises(ValueError):
        SymbolSequence(())
    with pytest.raises(ValueError):
        SymbolSequence(tuple(symbols[:5]))
    decision = choose_sequence(
        runtime.symbol_policy,
        local_context_tokens=("opaque.local",),
        neighbor_ids=("receiver",),
        tick=1,
    )
    assert decision.selected_action in (SymbolAction.SILENCE, SymbolAction.EMIT)
    if decision.selected_action is SymbolAction.EMIT:
        assert decision.selected_symbols and 1 <= len(decision.selected_symbols) <= 4


def test_receiver_grounding_is_local_exact_and_checkpoint_replay_safe() -> None:
    sender = ModeledOrganismRuntime(organism_id="sequence-sender", bootstrap_semantic_senses=False)
    receiver = ModeledOrganismRuntime(
        organism_id="sequence-receiver", bootstrap_semantic_senses=False
    )
    channel = SequenceChannel(authorized_pairs={(sender.organism_id, receiver.organism_id)})
    sequence = SymbolSequence(
        (sender.symbol_policy.symbol_space[0], sender.symbol_policy.symbol_space[1])
    )
    channel.deliver(
        SequenceMessage(sequence, sender.organism_id, receiver.organism_id, 0),
        receiver=receiver.sequence_grounding_ledger,
        tick=0,
    )
    receiver.observe_sequence_outcome(("opaque.outcome",), tick=1)
    assert receiver.predict_sequence(sequence) == ("opaque.outcome",)
    restored = SequenceGroundingLedger.restore(
        receiver.sequence_grounding_ledger.checkpoint(), organism_id=receiver.organism_id
    )
    assert restored.checkpoint() == receiver.sequence_grounding_ledger.checkpoint()


def test_sequence_delivery_rejects_wrong_owner_and_duplicate() -> None:
    sender = ModeledOrganismRuntime(
        organism_id="sequence-sender-2", bootstrap_semantic_senses=False
    )
    receiver = ModeledOrganismRuntime(
        organism_id="sequence-receiver-2", bootstrap_semantic_senses=False
    )
    channel = SequenceChannel(authorized_pairs={(sender.organism_id, receiver.organism_id)})
    message = SequenceMessage(
        SymbolSequence((sender.symbol_policy.symbol_space[0],)),
        sender.organism_id,
        receiver.organism_id,
        0,
    )
    channel.deliver(message, receiver=receiver.sequence_grounding_ledger, tick=0)
    with pytest.raises(ValueError):
        channel.deliver(message, receiver=receiver.sequence_grounding_ledger, tick=0)
    with pytest.raises(ValueError):
        receiver.sequence_grounding_ledger.receive(message, tick=0)


def test_modeled_sequence_decision_history_is_bounded_and_restorable() -> None:
    runtime = ModeledOrganismRuntime(
        organism_id="sequence-bounded", bootstrap_semantic_senses=False
    )
    receiver = ModeledOrganismRuntime(
        organism_id="sequence-bounded-peer", bootstrap_semantic_senses=False
    )
    for tick in range(MAX_HISTORY + 17):
        runtime.autonomous_sequence_decision(
            (receiver,), local_context_tokens=("opaque.local",), tick=tick
        )

    assert len(runtime.sequence_decisions) == MAX_HISTORY
    restored = ModeledOrganismRuntime.from_checkpoint(
        runtime.checkpoint(), bootstrap_semantic_senses=False
    )
    assert restored.sequence_decisions == runtime.sequence_decisions
