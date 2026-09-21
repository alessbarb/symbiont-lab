from types import SimpleNamespace

from symbiont_lab.physics3d.apparatus import PhysicsReadingProvider


class FakeApparatus:
    def sample_receptors(self):
        return {
            "opaque.a": 0.25,
            "opaque.b": 0.75,
            "opaque.unrequested": 0.5,
        }


def test_reading_provider_retains_exact_delivered_sample():
    provider = PhysicsReadingProvider(FakeApparatus())
    capabilities = (
        SimpleNamespace(capability_id="opaque.a"),
        SimpleNamespace(capability_id="opaque.b"),
    )

    readings = provider.sample(capabilities)

    assert {reading.capability_id: reading.value for reading in readings} == {
        "opaque.a": 0.25,
        "opaque.b": 0.75,
    }
    assert provider.last_values == {
        "opaque.a": 0.25,
        "opaque.b": 0.75,
    }
    assert isinstance(provider.last_monotonic_timestamp_ns, int)
    assert provider.last_monotonic_timestamp_ns > 0
