from __future__ import annotations

import pytest
from symbiont.core.evidence import EvidenceRevisionLedger

from symbiont.host.acclimation import HostAcclimation
from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit


def _reading(capability_id: str, value: float | None) -> SensorReading:
    return SensorReading(
        capability_id=capability_id,
        source="test",
        value=value,
        unit=Unit.RATIO,
        monotonic_timestamp_ns=0,
        quality=ReadingQuality.NOMINAL if value is not None else ReadingQuality.UNAVAILABLE,
        privacy_class=ReadingPrivacyClass.AGGREGATE,
    )


def test_rejects_non_positive_conflict_z():
    with pytest.raises(ValueError):
        EvidenceRevisionLedger(conflict_z=0.0)


def test_rejects_non_positive_max_dissent():
    with pytest.raises(ValueError):
        EvidenceRevisionLedger(max_dissent=0)


def test_revise_with_no_prior_baseline_just_observes_without_dissent():
    ledger = EvidenceRevisionLedger()
    acclimation = HostAcclimation(min_samples=5)

    result = ledger.revise(
        acclimation=acclimation,
        capability_id="cpu",
        evidence=[_reading("cpu", 1.0), _reading("cpu", 1.1)],
    )

    assert result.dissent is None
    assert not acclimation.is_acclimated("cpu")  # only 2 of 5 min_samples so far
    assert ledger.dissent_history == ()


def test_agreeing_evidence_revises_without_dissent():
    ledger = EvidenceRevisionLedger(conflict_z=2.0)
    acclimation = HostAcclimation(min_samples=2)
    acclimation.observe([_reading("cpu", 1.0), _reading("cpu", 1.0)])

    result = ledger.revise(
        acclimation=acclimation, capability_id="cpu", evidence=[_reading("cpu", 1.0)]
    )

    assert result.dissent is None
    assert result.baseline.count == 3
    assert ledger.dissent_history == ()


def test_conflicting_evidence_still_revises_but_records_dissent():
    ledger = EvidenceRevisionLedger(conflict_z=2.0)
    acclimation = HostAcclimation(min_samples=2)
    acclimation.observe(
        [_reading("cpu", 1.0), _reading("cpu", 1.05), _reading("cpu", 0.95), _reading("cpu", 1.02)]
    )
    prior = acclimation.baseline("cpu")

    result = ledger.revise(
        acclimation=acclimation, capability_id="cpu", evidence=[_reading("cpu", 10.0)]
    )

    assert result.dissent is not None
    assert result.dissent.capability_id == "cpu"
    assert result.dissent.prior_mean == pytest.approx(prior.mean)
    assert result.dissent.evidence_mean == pytest.approx(10.0)
    # revision happened despite the conflict: the new value is folded in, not held back
    assert result.baseline.count == 5
    assert result.baseline.mean != pytest.approx(prior.mean)
    assert ledger.dissent_history == (result.dissent,)


def test_zero_stdev_prior_never_flagged_as_dissent():
    """A constant baseline has no z-score basis to compare against — no
    false dissent should be manufactured from a degenerate prior."""
    ledger = EvidenceRevisionLedger(conflict_z=2.0)
    acclimation = HostAcclimation(min_samples=2)
    acclimation.observe([_reading("cpu", 1.0), _reading("cpu", 1.0)])

    result = ledger.revise(
        acclimation=acclimation, capability_id="cpu", evidence=[_reading("cpu", 99.0)]
    )

    assert result.dissent is None


def test_unavailable_readings_are_ignored():
    ledger = EvidenceRevisionLedger()
    acclimation = HostAcclimation(min_samples=2)
    acclimation.observe([_reading("cpu", 1.0), _reading("cpu", 1.0)])
    prior = acclimation.baseline("cpu")

    result = ledger.revise(
        acclimation=acclimation, capability_id="cpu", evidence=[_reading("cpu", None)]
    )

    assert result.dissent is None
    assert result.baseline.count == prior.count  # nothing observed, count unchanged


def test_dissent_history_is_bounded():
    ledger = EvidenceRevisionLedger(conflict_z=2.0, max_dissent=2)
    acclimation = HostAcclimation(min_samples=2)
    acclimation.observe([_reading("cpu", 1.0), _reading("cpu", 1.0)])

    for spike in (10.0, 20.0, 30.0):
        ledger.revise(
            acclimation=acclimation, capability_id="cpu", evidence=[_reading("cpu", spike)]
        )

    assert len(ledger.dissent_history) == 2
    assert [d.evidence_mean for d in ledger.dissent_history] == [20.0, 30.0]


def test_dissent_record_exposes_no_classification_surface():
    """Same discipline as everywhere else in this system: a statistical
    disagreement, never a threat or classification signal (ADR-0003)."""
    ledger = EvidenceRevisionLedger(conflict_z=2.0)
    acclimation = HostAcclimation(min_samples=2)
    acclimation.observe([_reading("cpu", 1.0), _reading("cpu", 1.0)])

    result = ledger.revise(
        acclimation=acclimation, capability_id="cpu", evidence=[_reading("cpu", 99.0)]
    )

    public_attrs = {name for name in dir(result.dissent) if not name.startswith("_")}
    assert public_attrs <= {
        "capability_id",
        "prior_mean",
        "prior_stdev",
        "evidence_mean",
        "z_score",
    }
