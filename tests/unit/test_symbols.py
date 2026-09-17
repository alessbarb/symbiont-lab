from __future__ import annotations

import pytest

from symbiont.modeling import (
    ModeledOrganismRuntime,
    SymbolAction,
    SymbolChannel,
    SymbolGroundingLedger,
    SymbolMessage,
    SymbolPolicy,
    default_symbol_space,
)


def test_opaque_space_is_bounded_and_deterministic() -> None:
    assert default_symbol_space() == default_symbol_space()
    assert len(default_symbol_space()) == 32
    assert all(item.startswith("symbol.") and len(item) == 19 for item in default_symbol_space())


def test_receiver_learns_and_contradiction_is_retained() -> None:
    ledger = SymbolGroundingLedger("receiver")
    message = SymbolMessage(default_symbol_space()[0], "sender", "receiver", 1)
    ledger.receive(message, tick=1)
    ledger.observe_outcome("outcome.0", tick=2, supported=True)
    ledger.observe_outcome("outcome.0", tick=3, supported=True)
    ledger.observe_outcome("outcome.0", tick=4, supported=False)
    assert ledger.predict(message.symbol_id) == "outcome.0"
    assert ledger.associations[0].contradiction == 1


def test_channel_rejects_spoofed_receiver_and_duplicates() -> None:
    symbol = default_symbol_space()[0]
    ledger = SymbolGroundingLedger("receiver")
    channel = SymbolChannel(authorized_pairs={("sender", "receiver")})
    channel.deliver(SymbolMessage(symbol, "sender", "receiver", 0), receiver=ledger, tick=0)
    with pytest.raises(ValueError):
        channel.deliver(SymbolMessage(symbol, "sender", "receiver", 0), receiver=ledger, tick=0)
    with pytest.raises(ValueError):
        ledger.receive(SymbolMessage(symbol, "sender", "other", 1), tick=1)


def test_policy_checkpoint_replays_and_silence_is_allowed() -> None:
    policy = SymbolPolicy("organism", seed=101)
    first = policy.choose(local_context_token="context.0", neighbor_ids=("receiver",), tick=0)
    restored = SymbolPolicy.restore(policy.checkpoint(), organism_id="organism")
    second = restored.choose(local_context_token="context.0", neighbor_ids=("receiver",), tick=1)
    assert first.selected_action in (SymbolAction.EMIT, SymbolAction.SILENCE)
    assert second.selected_action in (SymbolAction.EMIT, SymbolAction.SILENCE)
    assert restored.cost == policy.cost + second.cost


def test_new_runtime_starts_without_acquired_symbols() -> None:
    child = ModeledOrganismRuntime(organism_id="child", bootstrap_semantic_senses=False, symbol_policy_seed=7)
    assert child.symbol_grounding_ledger.exposures == ()
    assert child.symbol_grounding_ledger.associations == ()
    assert child.symbol_policy.organism_id == "child"
