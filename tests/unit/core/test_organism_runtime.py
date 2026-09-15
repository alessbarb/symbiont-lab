from __future__ import annotations

import json
import random

import pytest

from symbiont.core.runtime import OrganismRuntime
from symbiont.host.percepts import DEFAULT_PERCEPT_NAMES
from symbiont.core.signal_identity import SignalIdentity
from symbiont.core.signal_knowledge_types import SignalObservation, SignalObservationBatch
from symbiont.core.homeostasis import HomeostaticController


def test_rejects_non_positive_attention_budget():
    with pytest.raises(ValueError):
        OrganismRuntime(attention_budget=0.0)


def test_explicit_repair_consumes_maintenance_and_is_bounded():
    runtime = OrganismRuntime(explicit_metabolism=True,
                              homeostasis=HomeostaticController(integrity=0.5))
    before = runtime.metabolism.snapshot().reserve["maintenance"]
    repaired = runtime.repair(1.0)
    assert repaired == 0.25
    assert runtime.homeostasis.integrity == 0.75
    assert runtime.metabolism.snapshot().reserve["maintenance"] == before - 0.25


def test_predictor_promotion_is_explicitly_opt_in_and_checkpointed() -> None:
    runtime = OrganismRuntime(auto_promote_predictors=True)
    assert runtime.effective_configuration()["auto_promote_predictors"] is True
    restored = OrganismRuntime.from_checkpoint(runtime.checkpoint())
    assert restored.effective_configuration()["auto_promote_predictors"] is True


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


def test_full_runtime_checkpoint_contains_bounded_signal_knowledge(tmp_path):
    """The host checkpoint carries the complete bounded knowledge payload."""
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)
    identity = SignalIdentity(bytes(range(32)))
    signal_ids = tuple(identity.signal_id(f"pressure.{index}") for index in range(64))
    rng = random.Random(101)
    for tick in range(1, 257):
        runtime.signal_knowledge.observe(
            SignalObservationBatch(
                tick,
                tuple(SignalObservation(signal_id, True, True, rng.gauss(0.0, 1.0), "nominal") for signal_id in signal_ids),
            ),
            candidate_pairs=tuple((signal_ids[index], signal_ids[(index + 1) % 64]) for index in range(64)),
        )

    payload = runtime.checkpoint()
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    assert len(payload["signal_knowledge"]["profiles"]) == 64
    assert sum(len(profile["claims"]) for profile in payload["signal_knowledge"]["profiles"]) == 192
    assert len(encoded) < 2 * 1024 * 1024

    path = tmp_path / "runtime.json"
    runtime.save(path)
    assert path.stat().st_size == len(encoded)
    restored = OrganismRuntime.load_or_create(path, min_samples=1, investigate_ticks=0)
    assert restored.signal_knowledge.view() == runtime.signal_knowledge.view()


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


# --- v0.53: organism self-model wiring ---


def test_runtime_feeds_sampling_outcomes_into_self_model():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)
    for _ in range(10):
        runtime.tick()

    assert any(runtime.self_model.is_established(capability_id) for capability_id in DEFAULT_PERCEPT_NAMES)


def test_self_model_survives_checkpoint_round_trip():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)
    for _ in range(10):
        runtime.tick()
    payload = runtime.checkpoint()
    assert "self_model" in payload

    restored = OrganismRuntime.from_checkpoint(payload, min_samples=1, investigate_ticks=0)
    for capability_id in DEFAULT_PERCEPT_NAMES:
        if runtime.self_model.is_established(capability_id):
            assert restored.self_model.is_established(capability_id)


def test_fresh_organism_attention_allocations_unaffected_by_empty_self_model():
    runtime = OrganismRuntime(min_samples=1, attention_budget=1.0, investigate_ticks=0)
    result = runtime.tick()
    assert result.allocations


def test_established_but_persistently_unhealthy_sense_is_skipped_for_second_look():
    from types import SimpleNamespace

    from symbiont.core.selfmodel import MIN_SELF_MODEL_ATTEMPTS, SelfModel
    from symbiont.host.adaptive import AdaptiveSenseModel
    from symbiont.host.contracts import Capability, CapabilityKind, HostManifest
    from symbiont.host.lifecycle import LifecycleSnapshot
    from symbiont.host.readings import (
        CapabilitySamplingOutcome,
        ReadingPrivacyClass,
        ReadingQuality,
        SamplingOutcomeKind,
        SensorReading,
        Unit,
    )
    from symbiont.host.acclimation import CapabilityBaseline, HostAcclimation

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
    acclimation.restore("broken", CapabilityBaseline(count=10, mean=1.0, variance=1.0))
    acclimation.restore("healthy", CapabilityBaseline(count=10, mean=1.0, variance=1.0))

    self_model = SelfModel()
    for tick in range(max(MIN_SELF_MODEL_ATTEMPTS, 30)):
        self_model.observe(
            outcome=CapabilitySamplingOutcome(
                capability_id="broken",
                provider_id="fixture",
                kind=SamplingOutcomeKind.PROVIDER_FAILED,
                attributed_elapsed_s=0.01,
            ),
            tick=tick,
        )
        self_model.observe(
            outcome=CapabilitySamplingOutcome(
                capability_id="healthy",
                provider_id="fixture",
                kind=SamplingOutcomeKind.SUCCEEDED,
                attributed_elapsed_s=0.01,
                quality=ReadingQuality.NOMINAL,
            ),
            tick=tick,
        )

    adaptive = AdaptiveSenseModel()
    for tick in range(5):
        adaptive.observe([reading("broken", 1.0 + tick), reading("healthy", 1.0 + tick)])

    runtime = OrganismRuntime(
        discover_senses=True,
        bootstrap_semantic_senses=False,
        adaptive_senses=adaptive,
        acclimation=acclimation,
        self_model=self_model,
        investigate_ticks=1,
    )
    manifest = HostManifest(
        1,
        (
            Capability("broken", CapabilityKind.SIGNAL, "fixture"),
            Capability("healthy", CapabilityKind.SIGNAL, "fixture"),
        ),
        (),
    )
    snapshot = LifecycleSnapshot(
        1, manifest, (reading("broken", 1.0), reading("healthy", 1.0)), (), (), ("broken", "healthy")
    )
    runtime._lifecycle = SimpleNamespace(tick=lambda **kwargs: snapshot)

    result = runtime.tick()

    assert result.investigated_capability != "broken"


def test_one_failing_provider_only_degrades_its_own_capabilities_health():
    from dataclasses import dataclass, field as dc_field

    from symbiont.host.contracts import AccessMode, Capability, CapabilityKind, CapabilityScope, HostManifest
    from symbiont.host.discovery import HostDiscovery
    from symbiont.host.lifecycle import HostLifecycle
    from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit

    def _capability(capability_id: str) -> Capability:
        return Capability(
            capability_id=capability_id,
            kind=CapabilityKind.COMPUTE,
            source="fixture",
            access=AccessMode.READ_ONLY,
            scope=CapabilityScope.LOCAL,
        )

    @dataclass
    class _FakeDiscovery:
        provider_id: str
        capabilities: tuple[Capability, ...]

        def discover(self) -> tuple[Capability, ...]:
            return self.capabilities

    @dataclass
    class _MixedProvider:
        provider_id: str = "fixture"
        calls: int = dc_field(default=0)

        def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]:
            self.calls += 1
            readings = []
            for capability in capabilities:
                if capability.capability_id == "capability-broken":
                    continue  # silently omitted every time -> MISSING outcome
                readings.append(
                    SensorReading(
                        capability_id=capability.capability_id,
                        source="fixture",
                        value=1.0,
                        unit=Unit.COUNT,
                        monotonic_timestamp_ns=self.calls,
                        quality=ReadingQuality.NOMINAL,
                        privacy_class=ReadingPrivacyClass.AGGREGATE,
                    )
                )
            return tuple(readings)

    from symbiont.host.adaptive import AdaptiveSenseModel

    def _seed_reading(capability_id: str, value: float) -> SensorReading:
        return SensorReading(
            capability_id=capability_id,
            source="fixture",
            value=value,
            unit=Unit.COUNT,
            monotonic_timestamp_ns=1,
            quality=ReadingQuality.NOMINAL,
            privacy_class=ReadingPrivacyClass.AGGREGATE,
        )

    adaptive = AdaptiveSenseModel()
    for tick in range(10):
        adaptive.observe(
            [_seed_reading("capability-broken", 1.0 + tick), _seed_reading("capability-healthy", 1.0 + tick)]
        )

    discovery = HostDiscovery(
        providers=(_FakeDiscovery("fixture", (_capability("capability-broken"), _capability("capability-healthy"))),)
    )
    provider = _MixedProvider()
    lifecycle = HostLifecycle(discovery=discovery, reading_providers=(provider,))

    runtime = OrganismRuntime(
        discover_senses=True, bootstrap_semantic_senses=False, adaptive_senses=adaptive, investigate_ticks=0
    )
    runtime._lifecycle = lifecycle

    for _ in range(30):
        runtime.tick()

    assert runtime.self_model.health("capability-healthy") > 0.5
    assert runtime.self_model.health("capability-broken") < 0.5


# --- v0.54: idle decay wired into the second-look health gate ---


def test_health_without_current_tick_stays_undecayed_from_the_perspective_of_runtime():
    from symbiont.core.selfmodel import IDLE_GRACE_TICKS, SelfModel
    from symbiont.host.readings import CapabilitySamplingOutcome, ReadingQuality, SamplingOutcomeKind

    self_model = SelfModel()
    for tick in range(40):
        self_model.observe(
            outcome=CapabilitySamplingOutcome(
                capability_id="stale-but-was-healthy",
                provider_id="fixture",
                kind=SamplingOutcomeKind.SUCCEEDED,
                attributed_elapsed_s=0.01,
                quality=ReadingQuality.NOMINAL,
            ),
            tick=tick,
        )
    assert self_model.health(
        "stale-but-was-healthy", current_tick=39 + IDLE_GRACE_TICKS + 500
    ) == pytest.approx(0.5, abs=0.05)


def test_runtime_passes_current_tick_to_self_model_health_for_second_look_gate(monkeypatch):
    calls = []

    runtime = OrganismRuntime(min_samples=1, investigate_ticks=1)

    real_health = runtime.self_model.health

    def spy_health(sense_id, current_tick=None):
        calls.append(current_tick)
        return real_health(sense_id, current_tick=current_tick)

    monkeypatch.setattr(runtime.self_model, "health", spy_health)
    for _ in range(10):
        runtime.tick()

    assert any(tick_arg is not None for tick_arg in calls)


def test_a_sense_observed_just_before_checkpoint_is_not_idle_immediately_after_restore():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)
    for _ in range(10):
        runtime.tick()

    established = [
        capability_id for capability_id in DEFAULT_PERCEPT_NAMES if runtime.self_model.is_established(capability_id)
    ]
    assert established

    payload = runtime.checkpoint()
    restored = OrganismRuntime.from_checkpoint(payload, min_samples=1, investigate_ticks=0)

    sense_id = established[0]
    pre_checkpoint_health = runtime.self_model.health(sense_id)
    post_restore_health = restored.self_model.health(sense_id, current_tick=restored.tick_count)
    assert post_restore_health == pytest.approx(pre_checkpoint_health, abs=0.02)


# --- v0.55: optional genome wiring ---


def test_runtime_with_no_genome_is_unaffected():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)
    assert runtime.genome is None
    payload = runtime.checkpoint()
    assert payload["genome"] is None


def test_runtime_constructed_with_a_genome_round_trips_it_through_checkpoint():
    from symbiont.cognition.genome import GenomeCodec
    from tests.unit.cognition.test_genome import VALID_PAYLOAD

    genome = GenomeCodec().load(VALID_PAYLOAD)
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0, genome=genome)
    assert runtime.genome == genome

    payload = runtime.checkpoint()
    restored = OrganismRuntime.from_checkpoint(payload, min_samples=1, investigate_ticks=0)
    assert restored.genome == genome


def test_runtime_with_no_cognitive_graph_has_no_bridge():
    from symbiont.cognition.genome import GenomeCodec
    from tests.unit.cognition.test_genome import VALID_PAYLOAD

    genome = GenomeCodec().load(VALID_PAYLOAD)
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0, genome=genome)
    assert runtime.cognitive_bridge is None
    result = runtime.tick()
    assert result.cognition is None


def test_runtime_with_genome_and_graph_activates_cognition_each_tick():
    from symbiont.cognition.genome import GenomeCodec
    from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
    from symbiont.cognition.limits import KernelLimits
    from symbiont.cognition.types import EdgeKind, NodeKind
    from symbiont.host.percepts import DEFAULT_PERCEPT_NAMES
    from tests.unit.cognition.test_genome import VALID_PAYLOAD

    genome = GenomeCodec().load(VALID_PAYLOAD)
    sense_percept_name = next(iter(DEFAULT_PERCEPT_NAMES.values()))
    sense_node = PlasticNode(node_id=sense_percept_name, kind=NodeKind.SENSE)
    concept_node = PlasticNode(node_id="concept-x", kind=NodeKind.CONCEPT)
    edge = PlasticEdge(
        source_id=sense_percept_name, target_id="concept-x", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=0
    )
    graph = CognitiveGraph(nodes=(sense_node, concept_node), edges=(edge,), kernel_limits=KernelLimits())

    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0, genome=genome, cognitive_graph=graph)
    assert runtime.cognitive_bridge is not None

    result = runtime.tick()
    assert result.cognition is not None
    assert "concept-x" in result.cognition.activations


def test_cognitive_graph_state_survives_checkpoint_round_trip():
    from symbiont.cognition.genome import GenomeCodec
    from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
    from symbiont.cognition.limits import KernelLimits
    from symbiont.cognition.types import EdgeKind, NodeKind
    from symbiont.host.percepts import DEFAULT_PERCEPT_NAMES
    from tests.unit.cognition.test_genome import VALID_PAYLOAD

    genome = GenomeCodec().load(VALID_PAYLOAD)
    sense_percept_name = next(iter(DEFAULT_PERCEPT_NAMES.values()))
    sense_node = PlasticNode(node_id=sense_percept_name, kind=NodeKind.SENSE)
    concept_node = PlasticNode(node_id="concept-x", kind=NodeKind.CONCEPT)
    edge = PlasticEdge(
        source_id=sense_percept_name, target_id="concept-x", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=0
    )
    graph = CognitiveGraph(nodes=(sense_node, concept_node), edges=(edge,), kernel_limits=KernelLimits())

    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0, genome=genome, cognitive_graph=graph)
    for _ in range(10):
        runtime.tick()

    payload = runtime.checkpoint()
    restored = OrganismRuntime.from_checkpoint(payload, min_samples=1, investigate_ticks=0)

    assert restored.cognitive_bridge is not None
    assert {n.node_id for n in restored.cognitive_bridge.graph.nodes} == {sense_percept_name, "concept-x"}
    assert restored.cognitive_bridge.graph.edges[0].support == runtime.cognitive_bridge.graph.edges[0].support


def test_p4_repeated_checkpoint_calls_never_force_consolidation():
    """P4/design §12.2: OrganismRuntime.checkpoint() is a pure export --
    calling it many times in a row must never itself advance any
    consolidation state."""
    runtime = OrganismRuntime(discover_senses=False, bootstrap_semantic_senses=True, min_samples=1)
    for _ in range(1, 6):
        runtime.tick()
    first = runtime.checkpoint()
    for _ in range(20):
        assert runtime.checkpoint() == first


def test_checkpoint_byte_bound_is_retained_with_real_cognition():
    """Design PR4 bullet: checkpoint byte bound retained."""
    import json

    from symbiont.cognition.genome import GenomeCodec
    from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
    from symbiont.cognition.limits import KernelLimits
    from symbiont.cognition.types import EdgeKind, NodeKind

    genome_payload = {
        "schema_version": 1,
        "genome_id": "genome_bytebound00000000000000",
        "parent_ids": [],
        "kernel_compatibility": ">=0.55,<0.60",
        "development": {
            "initial_concepts": 4,
            "soft_node_budget": 64,
            "soft_edge_budget": 384,
            "consolidation_interval_ticks": 4,
        },
        "plasticity": {
            "learning_rate": {"initial": 0.05, "min": 0.001, "max": 0.08},
            "forgetting_rate": {"initial": 0.0005, "min": 0.0, "max": 0.005},
            "eligibility_decay": 0.9,
        },
        "structure": {
            "grow_threshold": 0.18,
            "prune_threshold": 0.01,
            "minimum_support": 16,
            "tentative_lifetime_ticks": 128,
        },
        "mutation_policy": {"continuous_sigma": 0.05, "max_fields_per_generation": 3},
    }
    limits = KernelLimits()
    genome = GenomeCodec().load(genome_payload)
    graph = CognitiveGraph(
        nodes=(PlasticNode(node_id="s", kind=NodeKind.SENSE), PlasticNode(node_id="c", kind=NodeKind.CONCEPT)),
        edges=(PlasticEdge(source_id="s", target_id="c", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=0),),
        kernel_limits=limits,
    )
    runtime = OrganismRuntime(
        discover_senses=False, bootstrap_semantic_senses=True, min_samples=1,
        genome=genome, kernel_limits=limits, cognitive_graph=graph,
    )
    for _ in range(1, 50):
        runtime.tick()
    encoded = json.dumps(runtime.checkpoint(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert len(encoded) <= limits.max_plastic_checkpoint_bytes


# --- v0.59.5: MemoryConsolidator wired for salient-event detection ---


def _drive_regime_shift_with_surprise(runtime, *, capability_id="compute.logical_cpu", stable_value=10.0, extreme_value=1000.0, extra_loss=1.0, stable_ticks=5, extreme_ticks=3):
    """Deterministically forces a real DriftKind.REGIME_SHIFT on `capability_id`
    (percept name "system_load" via DEFAULT_PERCEPT_NAMES) while also injecting
    a high-loss PredictionError for that same node, so the combined signal's
    score can cross fast_consolidation_threshold -- design §22's "flame"
    scenario. Uses the same _lifecycle-override pattern already used
    elsewhere in this file, not scripted drift-baseline internals."""
    from types import SimpleNamespace
    import dataclasses

    from symbiont.cognition.learning import PredictionError
    from symbiont.host.contracts import Capability, CapabilityKind, HostManifest
    from symbiont.host.lifecycle import LifecycleSnapshot
    from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit

    from symbiont.host.readings import CapabilitySamplingOutcome, SamplingOutcomeKind

    def reading(value):
        return SensorReading(
            capability_id=capability_id, source="fixture", value=value, unit=Unit.COUNT,
            monotonic_timestamp_ns=1, quality=ReadingQuality.NOMINAL, privacy_class=ReadingPrivacyClass.AGGREGATE,
        )

    def outcome():
        return (
            CapabilitySamplingOutcome(
                capability_id=capability_id, provider_id="fixture",
                kind=SamplingOutcomeKind.SUCCEEDED, attributed_elapsed_s=0.0, quality=ReadingQuality.NOMINAL,
            ),
        )

    manifest = HostManifest(1, (Capability(capability_id, CapabilityKind.SIGNAL, "fixture"),), ())
    stable_snapshot = LifecycleSnapshot(1, manifest, (reading(stable_value),), (), (), (capability_id,), outcome())
    extreme_snapshot = LifecycleSnapshot(1, manifest, (reading(extreme_value),), (), (), (capability_id,), outcome())

    real_bridge = runtime.cognitive_bridge
    if real_bridge is not None and not getattr(real_bridge, "_is_synthetic_fake", False):
        original_tick = real_bridge.tick

        def boosted_tick(*args, **kwargs):
            result = original_tick(*args, **kwargs)
            boosted = result.prediction_errors + (
                PredictionError(predictor_id="synthetic", target_id="system_load", error=extra_loss, loss=extra_loss),
            )
            return dataclasses.replace(result, prediction_errors=boosted)

        runtime._cognitive_bridge = SimpleNamespace(
            tick=boosted_tick, restore=real_bridge.restore,
            export_checkpoint=real_bridge.export_checkpoint, graph=real_bridge.graph,
        )
    else:
        fake_result = SimpleNamespace(
            prediction_errors=(PredictionError(predictor_id="synthetic", target_id="system_load", error=extra_loss, loss=extra_loss),),
        )
        runtime._cognitive_bridge = SimpleNamespace(
            tick=lambda *a, **k: fake_result, export_checkpoint=lambda: None,
            restore=lambda *a, **k: None, graph=None, _is_synthetic_fake=True,
        )

    runtime._lifecycle = SimpleNamespace(tick=lambda **kwargs: stable_snapshot)
    for _ in range(stable_ticks):
        runtime.tick()

    runtime._lifecycle = SimpleNamespace(tick=lambda **kwargs: extreme_snapshot)
    result = None
    for _ in range(extreme_ticks):
        result = runtime.tick()
    return result


def test_a_single_extraordinary_regime_shift_creates_a_durable_salient_trace():
    """Scenario A ('flame'), design §22: a real regime shift combined with a
    real high-loss prediction error commits a SalientEventTrace, verified
    through the actual OrganismRuntime.tick() wiring, not a bare consolidator
    call."""
    from symbiont.host.drift import DriftKind

    runtime = OrganismRuntime(discover_senses=False, bootstrap_semantic_senses=True, min_samples=1, investigate_ticks=0)
    result = _drive_regime_shift_with_surprise(runtime)

    assert result.drift_observations["system_load"].kind == DriftKind.REGIME_SHIFT
    checkpoint = runtime.checkpoint()
    assert len(checkpoint["memory"]["salient_events"]) == 1
    assert checkpoint["memory"]["salient_events"][0]["pattern_id"] == "system_load"


def test_p3_salient_trace_never_contains_a_raw_reading():
    """P3: a fast salient event may change durable memory after one tick,
    but persisted fields are only bounded categorical classes and safe ids
    -- never the extreme raw value (1000.0) or exact loss (1.0) that
    triggered it."""
    runtime = OrganismRuntime(discover_senses=False, bootstrap_semantic_senses=True, min_samples=1, investigate_ticks=0)
    _drive_regime_shift_with_surprise(runtime)

    checkpoint = runtime.checkpoint()
    traces = checkpoint["memory"]["salient_events"]
    assert traces  # the scenario above is proven to commit at least one trace
    for trace in traces:
        for key, value in trace.items():
            if key == "pattern_id":
                continue
            assert isinstance(value, int) and 0 <= value <= 15
    encoded = str(checkpoint["memory"])
    assert "1000.0" not in encoded
    assert "1000" not in encoded


def test_p8_low_reliability_sense_cannot_create_a_one_shot_trace():
    """Scenario C ('noisy sensor'), design §21 P8: a signal whose reliability
    sits below fast_min_reliability must never commit a fast trace even when
    the other four dimensions alone would already clear the score
    threshold -- proving the explicit reliability gate does real work beyond
    what the weighted score already enforces."""
    from symbiont.core.consolidation import ConsolidationSignal, MemoryKind

    runtime = OrganismRuntime(discover_senses=False, bootstrap_semantic_senses=True, min_samples=1)
    borderline_unreliable = ConsolidationSignal(novelty=1.0, surprise=1.0, attention=1.0, reliability=0.59, coherence=1.0)
    assert borderline_unreliable.score() >= runtime._kernel_limits.fast_consolidation_threshold
    outcome = runtime.memory_consolidator.observe("noisy_percept", MemoryKind.SALIENT_EVENT, borderline_unreliable, tick=1)
    assert outcome.path == "slow"
    assert runtime.memory_consolidator.salient_events == ()


def test_reacclimation_gate_blocks_salient_fast_path_after_restore():
    """§16a extended: the exact scenario A signal, replayed immediately
    after a restore, must NOT commit while reacclimation is active, and
    MUST commit once the reacclimation window has elapsed -- proving the
    gate is real, not merely absent evidence of firing."""
    from symbiont.cognition.limits import KernelLimits

    limits = KernelLimits(reacclimation_ticks=20)
    runtime = OrganismRuntime(discover_senses=False, bootstrap_semantic_senses=True, min_samples=1, investigate_ticks=0, kernel_limits=limits)
    checkpoint = runtime.checkpoint()
    restored = OrganismRuntime.from_checkpoint(checkpoint, min_samples=1, investigate_ticks=0, kernel_limits=limits)

    _drive_regime_shift_with_surprise(restored, stable_ticks=1, extreme_ticks=3)
    gated_checkpoint = restored.checkpoint()
    assert gated_checkpoint["memory"]["salient_events"] == []

    for _ in range(20):
        restored.tick()
    _drive_regime_shift_with_surprise(restored, capability_id="compute.logical_cpu", stable_value=10.0, extreme_value=2000.0, stable_ticks=1, extreme_ticks=3)
    reacclimated_checkpoint = restored.checkpoint()
    assert len(reacclimated_checkpoint["memory"]["salient_events"]) == 1


def test_scenario_b_ordinary_operation_never_fast_paths_without_a_predictor():
    """Scenario B ('street name'), design §22: an ordinary residence with no
    cognitive predictor wired can only ever contribute novelty+attention+
    reliability to the score (surprise pinned to 0 absent a predictor,
    coherence pinned to 0 per this PR's Global Constraints). Given the score
    weights (0.20/0.30/0.20/0.20/0.10), the maximum reachable score without
    a predictor is 0.20*1 + 0.20*1 + 0.20*1 = 0.60, always below
    fast_consolidation_threshold (0.80) -- so ordinary drift, however
    extreme, can never fast-path on its own. This is a real, falsifiable
    consequence of the weights, not a tautology of MemoryConsolidator's own
    bound (see test_p10 below for that one)."""
    runtime = OrganismRuntime(discover_senses=False, bootstrap_semantic_senses=True, min_samples=1, investigate_ticks=0)
    for _ in range(60):
        runtime.tick()
    checkpoint = runtime.checkpoint()
    assert checkpoint["memory"]["salient_events"] == []


def test_p9_salient_trace_never_mutates_structure_by_itself():
    """P9: driving the exact scenario-A fast-path commit through the real
    OrganismRuntime.tick() wiring, with a real genome/graph attached, must
    never add or remove a graph edge or node -- MemoryConsolidator has no
    structural API to call, so this guards against a future wiring mistake
    that accidentally connects the two."""
    from symbiont.cognition.genome import GenomeCodec
    from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
    from symbiont.cognition.limits import KernelLimits
    from symbiont.cognition.types import EdgeKind, NodeKind

    genome_payload = {
        "schema_version": 1, "genome_id": "genome_p9test0000000000000000000", "parent_ids": [],
        "kernel_compatibility": ">=0.55,<0.60",
        "development": {"initial_concepts": 4, "soft_node_budget": 64, "soft_edge_budget": 384, "consolidation_interval_ticks": 4},
        "plasticity": {"learning_rate": {"initial": 0.05, "min": 0.001, "max": 0.08}, "forgetting_rate": {"initial": 0.0005, "min": 0.0, "max": 0.005}, "eligibility_decay": 0.9},
        "structure": {"grow_threshold": 0.18, "prune_threshold": 0.01, "minimum_support": 16, "tentative_lifetime_ticks": 128},
        "mutation_policy": {"continuous_sigma": 0.05, "max_fields_per_generation": 3},
    }
    limits = KernelLimits()
    genome = GenomeCodec().load(genome_payload)
    graph = CognitiveGraph(
        nodes=(PlasticNode(node_id="system_load", kind=NodeKind.SENSE), PlasticNode(node_id="c", kind=NodeKind.CONCEPT)),
        edges=(PlasticEdge(source_id="system_load", target_id="c", kind=EdgeKind.EXCITATORY, weight=0.5, plasticity=0.5, delay_ticks=0),),
        kernel_limits=limits,
    )
    runtime = OrganismRuntime(
        discover_senses=False, bootstrap_semantic_senses=True, min_samples=1, investigate_ticks=0,
        genome=genome, kernel_limits=limits, cognitive_graph=graph,
    )
    edge_count_before = len(runtime.cognitive_bridge.graph.edges)
    node_count_before = len(runtime.cognitive_bridge.graph.nodes)

    _drive_regime_shift_with_surprise(runtime)
    assert runtime.memory_consolidator.salient_events  # the commit really happened

    assert len(runtime.cognitive_bridge.graph.edges) == edge_count_before
    assert len(runtime.cognitive_bridge.graph.nodes) == node_count_before


def test_p10_memory_stays_bounded_over_a_long_real_residence():
    """P10 end to end: candidates, salient traces and all durable
    projections respect kernel limits under a long real run, not just the
    standalone consolidator (already covered in PR1)."""
    runtime = OrganismRuntime(discover_senses=False, bootstrap_semantic_senses=True, min_samples=1)
    for _ in range(300):
        runtime.tick()
    checkpoint = runtime.checkpoint()
    assert len(checkpoint["memory"]["salient_events"]) <= runtime._kernel_limits.max_salient_event_traces
    assert len(checkpoint["memory"]["statistical"]) <= runtime._kernel_limits.max_consolidation_candidates
