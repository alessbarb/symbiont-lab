import pytest

from symbiont.core.communication import ConsentBoundChannel
from symbiont.core.exchange import ExchangeEnvelope


def test_local_channel_requires_consent_and_authenticates() -> None:
    channel = ConsentBoundChannel("habitat", b"secret")
    envelope = ExchangeEnvelope("a", 1, {"x": "y"})
    with pytest.raises(PermissionError):
        channel.send(envelope, "b")
    channel.authorize("a", "b")
    message = channel.send(envelope, "b")
    assert channel.verify(message)


def test_revocation_invalidates_existing_message() -> None:
    channel = ConsentBoundChannel("habitat", b"secret")
    channel.authorize("a", "b")
    message = channel.send(ExchangeEnvelope("a", 1, {"x": "y"}), "b")
    channel.revoke()
    assert not channel.verify(message)
