import pytest

from symbiont.core.exchange import ExchangeEnvelope, ExchangeReplayGuard


def test_exchange_is_bounded_and_replay_protected() -> None:
    envelope = ExchangeEnvelope("peer-a", 1, {"pattern": "stable"})
    guard = ExchangeReplayGuard()

    assert guard.accept(envelope)
    assert not guard.accept(envelope)
    assert guard.accept(ExchangeEnvelope("peer-a", 2, {"pattern": "stable"}))


def test_oversized_exchange_is_rejected() -> None:
    envelope = ExchangeEnvelope("peer-a", 0, {"payload": "x" * 5000})

    with pytest.raises(ValueError):
        envelope.encode()
