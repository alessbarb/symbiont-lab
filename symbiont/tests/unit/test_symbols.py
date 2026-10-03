from __future__ import annotations

import pytest

from symbiont.modeling import (
    ModeledOrganismRuntime,
    SymbolAction,
    SymbolChannel,
    SymbolGroundingLedger,
    SymbolMessage,
    SymbolPolicy,
    SymbolReinforcementSignal,
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
    child = ModeledOrganismRuntime(
        organism_id="child", bootstrap_semantic_senses=False, symbol_policy_seed=7
    )
    assert child.symbol_grounding_ledger.exposures == ()
    assert child.symbol_grounding_ledger.associations == ()
    assert child.symbol_policy.organism_id == "child"


def test_choose_is_unaffected_by_reinforce() -> None:
    """Existing choose() must stay a pure seeded hash; reinforce() only affects choose_adaptive()."""
    policy = SymbolPolicy("organism", seed=101)
    before = policy.choose(local_context_token="context.0", neighbor_ids=("receiver",), tick=0)
    policy.reinforce(
        local_context_token="context.0", symbol_id=default_symbol_space()[0], success=True, tick=1
    )
    after = policy.choose(local_context_token="context.0", neighbor_ids=("receiver",), tick=0)
    assert before.selected_symbol_id == after.selected_symbol_id
    assert before.selected_action == after.selected_action


def test_choose_adaptive_matches_choose_before_any_reinforcement() -> None:
    policy = SymbolPolicy("organism", seed=101)
    plain = policy.choose(local_context_token="context.0", neighbor_ids=("receiver",), tick=0)
    adaptive_policy = SymbolPolicy("organism", seed=101)
    adaptive = adaptive_policy.choose_adaptive(
        local_context_token="context.0", neighbor_ids=("receiver",), tick=0
    )
    assert plain.selected_symbol_id == adaptive.selected_symbol_id
    assert plain.selected_action == adaptive.selected_action


def test_reinforce_biases_choose_adaptive_toward_rewarded_symbol() -> None:
    policy = SymbolPolicy("organism", seed=101)
    space = policy.symbol_space
    target = space[5]
    other = [s for s in space if s != target]
    for tick in range(1, 40):
        policy.reinforce(local_context_token="context.0", symbol_id=target, success=True, tick=tick)
        for decoy in other[:3]:
            policy.reinforce(
                local_context_token="context.0", symbol_id=decoy, success=False, tick=tick
            )
    decision = policy.choose_adaptive(
        local_context_token="context.0", neighbor_ids=("receiver",), tick=1000
    )
    assert decision.selected_action is SymbolAction.EMIT
    assert decision.selected_symbol_id == target


def test_emission_bias_eviction_is_bounded() -> None:
    policy = SymbolPolicy("organism", seed=3, max_bias_entries=2)
    policy.reinforce(local_context_token="a", symbol_id="symbol.1", success=True, tick=1)
    policy.reinforce(local_context_token="b", symbol_id="symbol.2", success=True, tick=2)
    policy.reinforce(local_context_token="c", symbol_id="symbol.3", success=True, tick=3)
    checkpoint = policy.checkpoint()
    assert len(checkpoint["emission_bias"]) <= 2


def test_symbol_policy_checkpoint_v2_roundtrip_preserves_bias() -> None:
    policy = SymbolPolicy("organism", seed=5)
    policy.reinforce(
        local_context_token="context.0", symbol_id=default_symbol_space()[0], success=True, tick=1
    )
    policy.reinforce(
        local_context_token="context.0", symbol_id=default_symbol_space()[1], success=False, tick=2
    )
    checkpoint = policy.checkpoint()
    assert checkpoint["schema_version"] == 2
    restored = SymbolPolicy.restore(checkpoint, organism_id="organism")
    before = policy.choose_adaptive(local_context_token="context.0", neighbor_ids=("r",), tick=100)
    after = restored.choose_adaptive(local_context_token="context.0", neighbor_ids=("r",), tick=100)
    assert before.selected_symbol_id == after.selected_symbol_id


def test_symbol_policy_restores_legacy_v1_checkpoint_with_empty_bias() -> None:
    policy = SymbolPolicy("organism", seed=9)
    policy.choose(local_context_token="context.0", neighbor_ids=("r",), tick=0)
    legacy = policy.checkpoint()
    del legacy["emission_bias"]
    del legacy["max_bias_entries"]
    legacy["schema_version"] = 1
    restored = SymbolPolicy.restore(legacy, organism_id="organism")
    assert restored._emission_bias == {}


def test_symbol_policy_rejects_unknown_schema_version() -> None:
    policy = SymbolPolicy("organism", seed=9)
    payload = policy.checkpoint()
    payload["schema_version"] = 99
    with pytest.raises(ValueError):
        SymbolPolicy.restore(payload, organism_id="organism")


def test_symbol_reinforcement_signal_validates_fields() -> None:
    signal = SymbolReinforcementSignal(
        symbol_id=default_symbol_space()[0],
        context_token="context.0",
        outcome_token="outcome.0",
        sender_id="a",
        receiver_id="b",
        tick=1,
        success=True,
    )
    assert signal.success is True
    with pytest.raises(ValueError):
        SymbolReinforcementSignal(
            symbol_id=default_symbol_space()[0],
            context_token="context.0",
            outcome_token="outcome.0",
            sender_id="a",
            receiver_id="b",
            tick=-1,
            success=True,
        )


def test_report_symbol_reinforcement_updates_sender_policy() -> None:
    sender = ModeledOrganismRuntime(
        organism_id="sender", bootstrap_semantic_senses=False, symbol_policy_seed=11
    )
    symbol = sender.symbol_policy.symbol_space[0]
    signal = SymbolReinforcementSignal(
        symbol_id=symbol,
        context_token="context.0",
        outcome_token="outcome.0",
        sender_id="sender",
        receiver_id="receiver",
        tick=1,
        success=True,
    )
    sender.report_symbol_reinforcement(signal)
    assert sender.symbol_policy._emission_bias[("context.0", symbol)] == (1, 0)
    with pytest.raises(ValueError):
        sender.report_symbol_reinforcement(
            SymbolReinforcementSignal(
                symbol_id=symbol,
                context_token="context.0",
                outcome_token="outcome.0",
                sender_id="not-sender",
                receiver_id="receiver",
                tick=1,
                success=True,
            )
        )
