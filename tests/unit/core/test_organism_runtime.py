from __future__ import annotations

import pytest

from symbiont.core.runtime import OrganismRuntime


def test_rejects_non_positive_attention_budget():
    with pytest.raises(ValueError):
        OrganismRuntime(attention_budget=0.0)


def test_rejects_negative_investigate_ticks():
    with pytest.raises(ValueError):
        OrganismRuntime(investigate_ticks=-1)


def test_investigate_ticks_zero_disables_investigation():
    runtime = OrganismRuntime(investigate_ticks=0, min_samples=1)
    result = runtime.tick()

    assert result.investigated_capability is None
    assert result.evidence_gathered == 0
    assert result.dissent is None


def test_run_rejects_non_positive_ticks():
    runtime = OrganismRuntime()
    with pytest.raises(ValueError):
        runtime.run(0)


def test_single_tick_produces_a_full_record():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=1)
    result = runtime.tick()

    assert result.tick == 1
    assert result.snapshot.tick == 1
    assert result.percepts
    assert isinstance(result.narrative, tuple)
    assert result.narrative  # every known capability gets a narrative entry


def test_tick_count_and_run_accumulate_across_calls():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)
    runtime.tick()
    results = runtime.run(3)

    assert runtime.tick_count == 4
    assert [r.tick for r in results] == [2, 3, 4]


def test_acclimation_and_rhythm_model_accumulate_across_ticks():
    runtime = OrganismRuntime(min_samples=2, investigate_ticks=0)
    runtime.run(2)

    assert runtime.acclimation.acclimated_capabilities
    assert runtime.rhythm_model.learned_contexts


def test_drift_observations_reported_per_percept():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)
    result = runtime.tick()

    assert set(result.drift_observations) == {percept.name for percept in result.percepts if percept.value is not None}


def test_attention_always_allocates_at_least_one_capability_once_known():
    runtime = OrganismRuntime(min_samples=1, attention_budget=1.0, investigate_ticks=0)
    result = runtime.tick()

    assert result.allocations


def test_investigation_targets_the_top_attention_allocation():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=2)
    result = runtime.tick()

    if result.allocations:
        assert result.investigated_capability == result.allocations[0].name
        assert result.evidence_gathered == 2


def test_checkpoint_reflects_accumulated_state():
    runtime = OrganismRuntime(min_samples=2, investigate_ticks=0)
    runtime.run(2)

    checkpoint = runtime.checkpoint()
    assert checkpoint["acclimation"]
    assert checkpoint["saved_at_tick"] == 2


def test_checkpoint_before_any_tick_is_an_empty_shell():
    runtime = OrganismRuntime()
    checkpoint = runtime.checkpoint()

    assert checkpoint["acclimation"] == {}
    assert checkpoint["rhythms"] == []
    assert checkpoint["drift"] == {}
    assert checkpoint["saved_at_tick"] == 0


# --- v0.46: durable state (save/from_checkpoint/load_or_create) ---


def test_save_and_load_or_create_resumes_tick_count(tmp_path):
    path = tmp_path / "state.json"
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)
    runtime.run(3)
    runtime.save(path)

    restored = OrganismRuntime.load_or_create(path, min_samples=1, investigate_ticks=0)

    assert restored.tick_count == 3
    assert restored.acclimation.acclimated_capabilities


def test_load_or_create_starts_fresh_when_no_file_exists(tmp_path):
    restored = OrganismRuntime.load_or_create(tmp_path / "missing.json", min_samples=1)
    assert restored.tick_count == 0


def test_restored_runtime_continues_ticking_normally(tmp_path):
    path = tmp_path / "state.json"
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)
    runtime.run(2)
    runtime.save(path)

    restored = OrganismRuntime.load_or_create(path, min_samples=1, investigate_ticks=0)
    result = restored.tick()

    assert result.tick == 3
    assert restored.tick_count == 3


def test_from_checkpoint_with_v1_payload_defaults_tick_count_to_zero():
    v1_payload = {"schema_version": 1, "acclimation": {"cpu": {"count": 5, "mean": 1.0, "variance": 0.0}}}
    restored = OrganismRuntime.from_checkpoint(v1_payload, min_samples=1)

    assert restored.tick_count == 0
    assert restored.acclimation.is_acclimated("cpu")


def test_narrative_entry_never_exposes_a_threat_or_classification_field():
    """Same discipline as v0.41: the runtime composes existing narration,
    it does not add a new verdict surface on top of it (ADR-0003)."""
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)
    result = runtime.tick()

    for entry in result.narrative:
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


# --- A05: a stale, no-longer-discovered capability must not starve investigation ---


def test_stale_acclimation_entry_does_not_prevent_investigating_a_live_capability():
    from symbiont.host.acclimation import CapabilityBaseline

    runtime = OrganismRuntime(min_samples=1, investigate_ticks=1)
    # Seed a capability the acclimation model "knows" but that discovery will
    # never actually report this tick — it must never be allowed to occupy
    # the entire attention budget and block investigation of real senses.
    runtime.acclimation.restore("phantom-capability", CapabilityBaseline(count=1, mean=0.0, variance=0.0))

    result = runtime.tick()

    assert result.investigated_capability != "phantom-capability"
    if result.allocations:
        assert result.investigated_capability is not None


# --- B03: a sense learned as active but absent from the current manifest ---
# --- must not starve a genuinely live capability of the whole budget.    ---


def test_a_learned_but_currently_absent_sense_does_not_starve_a_live_one():
    from types import SimpleNamespace

    from symbiont.host.acclimation import CapabilityBaseline, HostAcclimation
    from symbiont.host.adaptive import AdaptiveSenseModel
    from symbiont.host.contracts import Capability, CapabilityKind, HostManifest
    from symbiont.host.lifecycle import LifecycleSnapshot
    from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit

    def reading(capability_id: str, value: float) -> SensorReading:
        return SensorReading(
            capability_id=capability_id,
            source="fixture",
            value=value,
            unit=Unit.COUNT,
            monotonic_timestamp_ns=1,
            quality=ReadingQuality.NOMINAL,
            privacy_class=ReadingPrivacyClass.AGGREGATE,
        )

    acclimation = HostAcclimation()
    acclimation.observe([reading("gone", 1.0)])
    acclimation.restore("live", CapabilityBaseline(count=10, mean=10.0, variance=1.0))

    adaptive = AdaptiveSenseModel()
    for tick in range(5):
        adaptive.observe([reading("gone", 10.0 + tick), reading("live", 10.0)])

    runtime = OrganismRuntime(
        discover_senses=True,
        bootstrap_semantic_senses=False,
        adaptive_senses=adaptive,
        acclimation=acclimation,
        investigate_ticks=1,
    )
    manifest = HostManifest(1, (Capability("live", CapabilityKind.SIGNAL, "fixture"),), ())
    snapshot = LifecycleSnapshot(1, manifest, (reading("live", 10.0),), (), (), ("live",))
    runtime._lifecycle = SimpleNamespace(tick=lambda **kwargs: snapshot)

    result = runtime.tick()

    assert result.allocations
    assert result.allocations[0].name == "live"
    assert result.investigated_capability == "live"


# --- B06: evicting a sense must also retire its drift baseline ---


def test_drift_baselines_stay_bounded_as_sensed_capabilities_renew():
    from types import SimpleNamespace

    from symbiont.host.adaptive import AdaptiveSenseModel
    from symbiont.host.contracts import Capability, CapabilityKind, HostManifest
    from symbiont.host.lifecycle import LifecycleSnapshot
    from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit

    def reading(capability_id: str, value: float) -> SensorReading:
        return SensorReading(
            capability_id=capability_id,
            source="fixture",
            value=value,
            unit=Unit.COUNT,
            monotonic_timestamp_ns=1,
            quality=ReadingQuality.NOMINAL,
            privacy_class=ReadingPrivacyClass.AGGREGATE,
        )

    adaptive = AdaptiveSenseModel(
        min_samples=1, active_limit=2, max_candidates=2, relation_window=2, exploration_limit=2, probe_limit=2
    )
    runtime = OrganismRuntime(
        discover_senses=True, bootstrap_semantic_senses=False, adaptive_senses=adaptive, investigate_ticks=0
    )

    for group in range(20):
        ids = (f"signal.group{group}.a", f"signal.group{group}.b")
        caps = tuple(Capability(cid, CapabilityKind.SIGNAL, "fixture") for cid in ids)
        readings = tuple(reading(cid, 1.0) for cid in ids)
        snapshot = LifecycleSnapshot(group, HostManifest(1, caps, ()), readings, (), (), ids)
        runtime._lifecycle = SimpleNamespace(tick=lambda **kwargs: snapshot)
        for _ in range(5):
            runtime.tick()

    assert len(runtime.adaptive_senses.states) <= 2
    assert len(runtime._drift_baselines) <= 2
