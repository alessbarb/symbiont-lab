"""Longitudinal Integrity v1 §11: cold restart equivalence with developed cognition.

Develops representative state in the organism, crosses a real serialization
boundary into a new runtime, and compares an explicit, bounded continuity
surface: what must be identical, what must have been reset, what must have
been reapplied, and how the future may differ.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

import pytest

from symbiont.cognition.birth import load_base_cognition
from symbiont.cognition.limits import KernelLimits
from symbiont.core.social.communication import ConsentBoundChannel, SignedMessage
from symbiont.core.social.exchange import ExchangeEnvelope
from symbiont.host.continuity import (
    CONDITIONAL_FIELDS,
    PRIVATE_MODEL,
    ContinuityClass,
    entries_for,
)
from symbiont.host.contracts import Capability, CapabilityKind
from symbiont.host.discovery import HostDiscovery
from symbiont.host.lifecycle import HostLifecycle
from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit
from symbiont.modeling import (
    ArchitectureId,
    ModelArtifactManifest,
    ModelObjective,
    ModelState,
    TrainingRequest,
)
from symbiont.modeling.private_runtime import PrivateModelOrganismRuntime

RUNTIME_KWARGS = dict(
    bootstrap_semantic_senses=False,
    discover_senses=True,
    min_samples=1,
    investigate_ticks=0,
)
SIGNALS = ("signal.alpha", "signal.beta", "signal.gamma")
PEER = "peer-a"
DEVELOPMENT_TICKS = 40
CONTINUATION_TICKS = 40
# A cold restart is identical at the boundary, but its future is not identical
# to never having stopped. Two documented resets cause that, and only these
# fields may differ afterwards; every other field must stay byte-identical.
#
# 1. One-tick causal traces do not cross a process boundary (design §3.2). The
#    pending private frame is dropped, so the transition spanning the restart is
#    never recorded, and the bridge has no previous-tick activations for its
#    first post-restore update.
# 2. Every restore opens the organism-owned reacclimation gate, which pauses
#    structural consolidation for kernel_limits.reacclimation_ticks.
#
# Fabricating either would bridge a causal consequence that never happened in
# the restored timeline. The remaining fields diverge downstream of cognition.
# Receptor utility is fed by the bridge's predictive gain, so under sensory
# plasticity (canonical profile v1) the sensory system and the body schema built
# on it are downstream of cognition as well.
RESTART_SENSITIVE_FIELDS = {
    "experience_ledger",
    "private_learning_state",
    "episodic_memory",
    "cognitive_bridge",
    "generative_cognition",
    "signal_knowledge",
    "development",
    "innate_reactivity",
    "metabolism",
    "living_body",
    "narrative_journal",
    "sensory_system",
    "body_schema",
}
# Save metadata: never part of the organism's future-equivalence surface.
SAVE_METADATA = {"checkpoint_lineage", "runtime_provenance"}


class _Discovery:
    provider_id = "synthetic"

    def discover(self) -> tuple[Capability, ...]:
        return tuple(
            Capability(signal, CapabilityKind.SIGNAL, self.provider_id) for signal in SIGNALS
        )


@dataclass
class _Host:
    """Deterministic host: every reading is a function of the sample count."""

    calls: int = 0
    provider_id: str = "synthetic"

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]:
        self.calls += 1
        return tuple(
            SensorReading(
                capability_id=capability.capability_id,
                source=self.provider_id,
                value=round(1.0 + math.sin(self.calls / (3.0 + index)), 6),
                unit=Unit.COUNT,
                monotonic_timestamp_ns=self.calls,
                quality=ReadingQuality.NOMINAL,
                privacy_class=ReadingPrivacyClass.AGGREGATE,
            )
            for index, capability in enumerate(capabilities)
        )


def _host_kwargs(host: _Host) -> dict:
    lifecycle = HostLifecycle(discovery=HostDiscovery((_Discovery(),)), reading_providers=(host,))
    return dict(host_lifecycle=lifecycle, host_reading_providers=(host,))


def _channel(organism_id: str) -> ConsentBoundChannel:
    channel = ConsentBoundChannel("habitat-restart", b"shared-key")
    channel.authorize(PEER, organism_id)
    channel.authorize(organism_id, PEER)
    return channel


def _inbound(channel: ConsentBoundChannel, recipient: str, sequence: int) -> SignedMessage:
    claim = f"claim-{sequence}"
    envelope = ExchangeEnvelope(PEER, sequence, {claim: json.dumps({"payload": claim})})
    return channel.send(envelope, recipient)


def _develop() -> tuple[PrivateModelOrganismRuntime, ConsentBoundChannel, _Host]:
    """One organism with acquired state in every preserved family it can reach."""
    genome, graph = load_base_cognition(kernel_limits=KernelLimits(), running_version=(0, 99, 0))
    host = _Host()
    runtime = PrivateModelOrganismRuntime(
        organism_id="restart-subject",
        genome=genome,
        cognitive_graph=graph,
        **_host_kwargs(host),
        **RUNTIME_KWARGS,
    )
    runtime.run(DEVELOPMENT_TICKS)

    request = TrainingRequest(
        organism_id=runtime.organism_id,
        corpus_hash="a" * 64,
        tokenizer_hash="b" * 64,
        architecture_id=ArchitectureId.GRU_V1,
        objective=ModelObjective.NEXT_TOKEN,
        seed=7,
        context_window=32,
        requested_parameters=1_000_000,
        requested_epochs=4,
        requested_steps=100,
        created_tick_class=0,
    )
    artifact = ModelArtifactManifest.build(
        request=request, parameter_count=100_000, weights_hash="c" * 64, artifact_bytes=1024
    )
    shadow = runtime.adopt_private_model(artifact, evaluation_summary=(0, 1))
    runtime.activate_private_model(
        shadow.model_id, promotion_authorized=True, evaluation_summary=(1, 2)
    )

    runtime.originate_social_claim(
        proposition_tokens=("sense.a", "relates", "sense.b"),
        evidence_id="evidence.own",
        confidence_class=5,
    )

    channel = _channel(runtime.organism_id)
    runtime.attach_communication_channel(channel)
    assert runtime.receive_communication(_inbound(channel, runtime.organism_id, 1))

    runtime.set_predictor_promotion_enabled(False)
    return runtime, channel, host


def _cold_restart(
    runtime: PrivateModelOrganismRuntime, channel: ConsentBoundChannel, host: _Host
) -> PrivateModelOrganismRuntime:
    """New process: a new runtime and a new host handle at the same host time."""
    serialized = json.dumps(runtime.checkpoint())
    del runtime
    restored = PrivateModelOrganismRuntime.from_checkpoint(
        json.loads(serialized), **_host_kwargs(_Host(calls=host.calls)), **RUNTIME_KWARGS
    )
    restored.attach_communication_channel(channel)
    return restored


def _state(runtime: PrivateModelOrganismRuntime) -> dict:
    return json.loads(json.dumps(runtime.checkpoint(advance_lineage=False)))


@pytest.fixture
def developed() -> tuple[PrivateModelOrganismRuntime, ConsentBoundChannel, _Host]:
    return _develop()


def test_development_reaches_the_preserved_families(developed) -> None:
    """Guard the test itself: an empty organism would make equivalence trivial."""
    runtime, _, _ = developed
    state = _state(runtime)

    assert state["saved_at_tick"] == DEVELOPMENT_TICKS
    assert state["genome"] is not None and state["gene_expression"] is not None
    assert state["cognitive_bridge"]["graph"]["nodes"]
    assert len(runtime.experience_ledger.records) > 10
    assert state["episodic_memory"]
    assert runtime.model_registry.active is not None
    assert len(runtime.social_evidence_ledger.claims) == 1
    assert state["exchange_guard"] == {PEER: 1}
    assert state["narrative_journal"]

    preserved = {
        field
        for entry in entries_for(PRIVATE_MODEL)
        if entry.continuity is ContinuityClass.MUST_PRESERVE
        for field in entry.checkpoint_fields
    }
    assert preserved - CONDITIONAL_FIELDS <= set(state)


def test_restart_is_not_a_biological_event(developed) -> None:
    runtime, channel, host = developed
    identity = runtime.state_hash()
    before = _state(runtime)

    restored = _cold_restart(runtime, channel, host)
    after = _state(restored)

    assert restored.state_hash() == identity
    assert {key for key in before if before[key] != after[key]} <= SAVE_METADATA


def test_restart_preserves_meaning_not_just_bytes(developed) -> None:
    runtime, channel, host = developed
    organism_id = runtime.organism_id
    tick = runtime.tick_count
    active_model = runtime.model_registry.active.model_id
    experience_ids = [record.record_id for record in runtime.experience_ledger.records]
    graph_nodes = len(runtime.cognitive_bridge.graph.nodes)
    own_claims = runtime.social_evidence_ledger.claims

    restored = _cold_restart(runtime, channel, host)

    # identity and organism time
    assert restored.organism_id == organism_id
    assert restored.tick_count == tick
    # learned state
    assert len(restored.cognitive_bridge.graph.nodes) == graph_nodes
    assert [record.record_id for record in restored.experience_ledger.records] == experience_ids
    # model and ancestry
    assert restored.model_registry.active.model_id == active_model
    assert restored.model_registry.active.state is ModelState.ACTIVE
    # social state, in its single canonical owner (ARCH-1)
    assert restored.social_evidence_ledger.claims == own_claims
    # replay protection
    assert not restored.receive_communication(_inbound(channel, organism_id, 1))
    assert restored._exchange_guard.checkpoint() == {PEER: 1}


def test_restart_resets_transient_state_and_reapplies_configuration(developed) -> None:
    runtime, channel, host = developed
    assert runtime._pending_private_frame is not None

    restored = _cold_restart(runtime, channel, host)

    # MUST_RESET: nothing that would bridge the process boundary survives.
    assert restored._pending_private_frame is None
    assert restored._pending_outcome_value_credit == []
    assert restored._private_model_bridge is None
    assert restored._reacclimation_remaining == KernelLimits().reacclimation_ticks
    # MUST_REAPPLY_CONFIG: the session ran with promotion disabled.
    assert restored._predictor_promotion_enabled is False
    assert restored._cognitive_plasticity_enabled is True
    assert restored.checkpoint()["runtime_provenance"]["changed_since_restore"] == []


def test_restarted_future_differs_only_on_the_declared_surface(developed) -> None:
    control, channel, host = developed
    restored = _cold_restart(control, channel, host)

    for branch in (control, restored):
        branch.run(CONTINUATION_TICKS)
        branch.receive_communication(_inbound(channel, branch.organism_id, 2))
    uninterrupted = _state(control)
    restarted = _state(restored)

    differing = {key for key in uninterrupted if uninterrupted[key] != restarted[key]}
    differing -= SAVE_METADATA
    assert differing <= RESTART_SENSITIVE_FIELDS
    assert {"experience_ledger", "cognitive_bridge"} <= differing
    # Identity, genome, models, social knowledge, communication state,
    # symbols and recorded configuration are untouched by the restart.
    assert len(set(uninterrupted) - SAVE_METADATA - RESTART_SENSITIVE_FIELDS) > 40


def test_the_only_unrecorded_experience_is_the_transition_spanning_the_restart(
    developed,
) -> None:
    control, channel, host = developed
    restored = _cold_restart(control, channel, host)
    control.run(CONTINUATION_TICKS)
    restored.run(CONTINUATION_TICKS)

    control_ids = [record.record_id for record in control.experience_ledger.records]
    restored_ids = [record.record_id for record in restored.experience_ledger.records]
    missing = [record_id for record_id in control_ids if record_id not in restored_ids]

    # Exactly one transition is absent, and nothing was invented in its place.
    assert len(missing) == 1
    assert set(restored_ids) < set(control_ids)
    (bridging,) = [r for r in control.experience_ledger.records if r.record_id in missing]
    assert bridging.tick_class == DEVELOPMENT_TICKS


def test_reacclimation_gate_holds_structure_then_releases(developed) -> None:
    runtime, channel, host = developed
    restored = _cold_restart(runtime, channel, host)
    window = KernelLimits().reacclimation_ticks

    def topology(subject: PrivateModelOrganismRuntime) -> tuple[set[str], int]:
        # The gate holds concepts and connections. Receptors are deliberately
        # outside it: a restored organism may adapt its sensors at once.
        graph = subject.cognitive_bridge.graph
        receptors = {node.node_id for node in graph.nodes if node.node_id.startswith("sensor.")}
        held_edges = [
            edge
            for edge in graph.edges
            if edge.source_id not in receptors and edge.target_id not in receptors
        ]
        return {node.node_id for node in graph.nodes} - receptors, len(held_edges)

    at_restart = topology(restored)
    restored.run(window - 1)
    assert restored.reacclimation_remaining == 1
    assert topology(restored) == at_restart

    restored.run(1)
    assert restored.reacclimation_remaining == 0


def test_observer_reads_do_not_change_the_continuity_outcome(developed) -> None:
    observed, channel, host = developed
    quiet, _, quiet_host = _develop()
    for _ in range(5):
        observed.checkpoint(advance_lineage=False)
        observed.state_hash()

    assert _state(_cold_restart(observed, channel, host)) == _state(
        _cold_restart(quiet, channel, quiet_host)
    )
