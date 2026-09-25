from __future__ import annotations

import pytest
from symbiont.core.capsule import CapsuleKeyPair, create_capsule
from symbiont.core.trust import SourceTrustModel, agreement_score, observe_capsule_trust

from symbiont.host.acclimation import CapabilityBaseline, HostAcclimation
from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit


def _reading(capability_id: str, value: float) -> SensorReading:
    return SensorReading(
        capability_id=capability_id,
        source="test",
        value=value,
        unit=Unit.RATIO,
        monotonic_timestamp_ns=0,
        quality=ReadingQuality.NOMINAL,
        privacy_class=ReadingPrivacyClass.AGGREGATE,
    )


# --- agreement_score ---


def test_agreement_score_is_one_at_perfect_match():
    local = CapabilityBaseline(count=5, mean=1.0, variance=0.04)
    assert agreement_score(local, 1.0) == pytest.approx(1.0)


def test_agreement_score_decreases_with_distance():
    local = CapabilityBaseline(count=5, mean=1.0, variance=0.04)
    close = agreement_score(local, 1.2)
    far = agreement_score(local, 10.0)
    assert 0.0 < far < close < 1.0


def test_agreement_score_none_without_local_baseline():
    assert agreement_score(None, 1.0) is None


def test_agreement_score_none_with_zero_stdev_local_baseline():
    local = CapabilityBaseline(count=5, mean=1.0, variance=0.0)
    assert agreement_score(local, 5.0) is None


# --- SourceTrustModel ---


def test_rejects_non_positive_max_contexts():
    with pytest.raises(ValueError):
        SourceTrustModel(max_contexts=0)


def test_rejects_non_positive_min_samples():
    with pytest.raises(ValueError):
        SourceTrustModel(min_samples=0)


def test_rejects_agreement_outside_unit_interval():
    model = SourceTrustModel()
    with pytest.raises(ValueError):
        model.observe(source=b"x" * 32, pattern_family="cpu", agreement=1.5)
    with pytest.raises(ValueError):
        model.observe(source=b"x" * 32, pattern_family="cpu", agreement=-0.1)


def test_not_learned_before_min_samples():
    model = SourceTrustModel(min_samples=3)
    model.observe(source=b"a" * 32, pattern_family="cpu", agreement=0.9)

    assert not model.is_learned(b"a" * 32, "cpu")
    assert model.reliability(b"a" * 32, "cpu") is None


def test_learned_once_min_samples_reached():
    model = SourceTrustModel(min_samples=2)
    model.observe(source=b"a" * 32, pattern_family="cpu", agreement=0.8)
    model.observe(source=b"a" * 32, pattern_family="cpu", agreement=1.0)

    assert model.is_learned(b"a" * 32, "cpu")
    snapshot = model.reliability(b"a" * 32, "cpu")
    assert snapshot.count == 2
    assert snapshot.mean == pytest.approx(0.9)


def test_sources_and_pattern_families_are_tracked_independently():
    model = SourceTrustModel(min_samples=1)
    model.observe(source=b"a" * 32, pattern_family="cpu", agreement=1.0)
    model.observe(source=b"a" * 32, pattern_family="disk", agreement=0.2)
    model.observe(source=b"b" * 32, pattern_family="cpu", agreement=0.5)

    assert model.reliability(b"a" * 32, "cpu").mean == pytest.approx(1.0)
    assert model.reliability(b"a" * 32, "disk").mean == pytest.approx(0.2)
    assert model.reliability(b"b" * 32, "cpu").mean == pytest.approx(0.5)


def test_known_sources_reflects_observed_signers():
    model = SourceTrustModel(min_samples=1)
    model.observe(source=b"a" * 32, pattern_family="cpu", agreement=1.0)
    model.observe(source=b"b" * 32, pattern_family="cpu", agreement=1.0)

    assert model.known_sources == (b"a" * 32, b"b" * 32)


def test_context_count_is_bounded():
    model = SourceTrustModel(max_contexts=1, min_samples=1)
    model.observe(source=b"a" * 32, pattern_family="cpu", agreement=1.0)
    model.observe(source=b"a" * 32, pattern_family="disk", agreement=1.0)

    assert model.reliability(b"a" * 32, "cpu") is not None
    assert model.reliability(b"a" * 32, "disk") is None


def test_reliability_exposes_no_classification_surface():
    """Same discipline as everywhere else: descriptive statistics only,
    never a trust/distrust verdict (ADR-0003)."""
    model = SourceTrustModel(min_samples=1)
    model.observe(source=b"a" * 32, pattern_family="cpu", agreement=1.0)
    snapshot = model.reliability(b"a" * 32, "cpu")

    public_attrs = {name for name in dir(snapshot) if not name.startswith("_")}
    assert public_attrs <= {"count", "mean", "variance"}


# --- observe_capsule_trust ---


def test_observe_capsule_trust_rejects_forged_capsule():
    import dataclasses

    keypair = CapsuleKeyPair.generate()
    capsule = create_capsule(
        keypair, {"acclimation": {"cpu": {"count": 5, "mean": 1.0, "variance": 0.01}}}
    )
    forged = dataclasses.replace(
        capsule, payload={"acclimation": {"cpu": {"count": 5, "mean": 999.0, "variance": 0.01}}}
    )

    model = SourceTrustModel()
    acclimation = HostAcclimation(min_samples=2)
    acclimation.observe([_reading("cpu", 1.0), _reading("cpu", 1.0)])

    with pytest.raises(ValueError):
        observe_capsule_trust(model, acclimation=acclimation, capsule=forged)


def test_observe_capsule_trust_updates_model_for_shared_capabilities():
    keypair = CapsuleKeyPair.generate()
    capsule = create_capsule(
        keypair,
        {
            "acclimation": {
                "cpu": {"count": 5, "mean": 1.01, "variance": 0.001},
                "unknown_to_us": {"count": 5, "mean": 42.0, "variance": 0.0},
            }
        },
    )
    acclimation = HostAcclimation(min_samples=2)
    acclimation.observe(
        [_reading("cpu", 1.0), _reading("cpu", 1.02), _reading("cpu", 0.99), _reading("cpu", 1.01)]
    )

    model = SourceTrustModel()
    scores = observe_capsule_trust(model, acclimation=acclimation, capsule=capsule)

    assert "cpu" in scores
    assert "unknown_to_us" not in scores  # no local baseline for it
    assert model.reliability(keypair.public_bytes, "cpu") is not None


def test_observe_capsule_trust_skips_capabilities_without_local_baseline():
    keypair = CapsuleKeyPair.generate()
    capsule = create_capsule(
        keypair, {"acclimation": {"never_seen": {"count": 5, "mean": 1.0, "variance": 0.0}}}
    )
    acclimation = HostAcclimation(min_samples=2)  # nothing observed at all

    model = SourceTrustModel()
    scores = observe_capsule_trust(model, acclimation=acclimation, capsule=capsule)

    assert scores == {}
    assert model.known_sources == ()


def test_observe_capsule_trust_handles_capsule_with_no_acclimation_section():
    keypair = CapsuleKeyPair.generate()
    capsule = create_capsule(keypair, {"rhythms": []})
    acclimation = HostAcclimation(min_samples=2)

    model = SourceTrustModel()
    scores = observe_capsule_trust(model, acclimation=acclimation, capsule=capsule)

    assert scores == {}
