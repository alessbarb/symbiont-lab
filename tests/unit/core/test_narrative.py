from __future__ import annotations

from symbiont.core.attention import AttentionAllocation
from symbiont.core.evidence import DissentRecord
from symbiont.core.narrative import narrate_capability, narrate_host

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


def test_unfamiliar_capability_has_infinite_uncertainty_and_says_so():
    entry = narrate_capability(capability_id="new.thing", baseline=None)

    assert entry.familiarity == "unfamiliar"
    assert entry.uncertainty == float("inf")
    assert not entry.attended
    assert entry.attention_cost is None
    assert entry.evidence_gathered == 0
    assert not entry.contested
    assert "not yet familiar" in entry.summary


def test_familiar_capability_reports_coefficient_of_variation():
    baseline = CapabilityBaseline(count=5, mean=2.0, variance=4.0)
    entry = narrate_capability(capability_id="cpu", baseline=baseline)

    assert entry.familiarity == "familiar"
    assert entry.uncertainty == 1.0
    assert "familiar" in entry.summary
    assert "0.001" not in entry.summary  # sanity: not accidentally near-zero-formatted


def test_attended_capability_reports_attention_and_cost():
    baseline = CapabilityBaseline(count=5, mean=1.0, variance=0.0)
    allocation = AttentionAllocation(name="cpu", uncertainty=0.0, cost=1.0)

    entry = narrate_capability(capability_id="cpu", baseline=baseline, allocation=allocation)

    assert entry.attended
    assert entry.attention_cost == 1.0
    assert "received attention" in entry.summary


def test_not_attended_capability_says_so():
    baseline = CapabilityBaseline(count=5, mean=1.0, variance=0.0)
    entry = narrate_capability(capability_id="cpu", baseline=baseline, allocation=None)

    assert not entry.attended
    assert entry.attention_cost is None
    assert "did not receive attention" in entry.summary


def test_evidence_gathered_is_reported_in_summary():
    baseline = CapabilityBaseline(count=5, mean=1.0, variance=0.0)
    entry = narrate_capability(capability_id="cpu", baseline=baseline, evidence_gathered=3)

    assert entry.evidence_gathered == 3
    assert "3 new reading(s)" in entry.summary


def test_no_evidence_gathered_omits_evidence_clause():
    baseline = CapabilityBaseline(count=5, mean=1.0, variance=0.0)
    entry = narrate_capability(capability_id="cpu", baseline=baseline, evidence_gathered=0)

    assert "reading(s)" not in entry.summary


def test_contested_revision_reports_what_changed():
    baseline = CapabilityBaseline(count=5, mean=1.0, variance=0.04)
    dissent = DissentRecord(
        capability_id="cpu", prior_mean=1.0, prior_stdev=0.2, evidence_mean=5.0, z_score=20.0
    )

    entry = narrate_capability(capability_id="cpu", baseline=baseline, dissent=dissent)

    assert entry.contested
    assert entry.dissent is dissent
    assert "contested" in entry.summary
    assert "5.000" in entry.summary  # evidence mean
    assert "1.000" in entry.summary  # prior mean
    assert "20.00" in entry.summary  # z-score


def test_uncontested_revision_omits_contested_clause():
    baseline = CapabilityBaseline(count=5, mean=1.0, variance=0.04)
    entry = narrate_capability(capability_id="cpu", baseline=baseline, dissent=None)

    assert not entry.contested
    assert entry.dissent is None
    assert "contested" not in entry.summary


def test_narrate_host_covers_every_known_capability():
    acclimation = HostAcclimation(min_samples=2)
    acclimation.observe([_reading("cpu", 1.0), _reading("cpu", 1.0)])
    acclimation.observe([_reading("disk", 1.0)])  # not yet acclimated

    entries = narrate_host(acclimation)

    assert {entry.capability_id for entry in entries} == {"cpu", "disk"}
    by_id = {entry.capability_id: entry for entry in entries}
    assert by_id["cpu"].familiarity == "familiar"
    assert by_id["disk"].familiarity == "unfamiliar"


def test_narrate_host_cross_references_allocations_and_dissent():
    acclimation = HostAcclimation(min_samples=2)
    acclimation.observe([_reading("cpu", 1.0), _reading("cpu", 1.0)])
    allocation = AttentionAllocation(name="cpu", uncertainty=0.0, cost=1.0)
    dissent = DissentRecord(
        capability_id="cpu", prior_mean=1.0, prior_stdev=0.1, evidence_mean=5.0, z_score=40.0
    )

    entries = narrate_host(
        acclimation,
        allocations=[allocation],
        evidence_counts={"cpu": 2},
        dissent_by_capability={"cpu": dissent},
    )

    entry = entries[0]
    assert entry.attended
    assert entry.evidence_gathered == 2
    assert entry.contested


def test_narrative_entry_exposes_no_threat_or_classification_field():
    """Same discipline as everywhere else: a structured explanation, never a
    threat or classification verdict (ADR-0003)."""
    entry = narrate_capability(capability_id="cpu", baseline=None)

    public_attrs = {name for name in dir(entry) if not name.startswith("_")}
    assert public_attrs <= {
        "capability_id",
        "familiarity",
        "uncertainty",
        "attended",
        "attention_cost",
        "evidence_gathered",
        "dissent",
        "contested",
        "summary",
    }
