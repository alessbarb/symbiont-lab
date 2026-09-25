from __future__ import annotations

from types import SimpleNamespace

import pytest
from symbiont.core.runtime import RuntimeTickResult

from symbiont.actuation.types import Actuation
from symbiont.cognition.types import NodeKind
from symbiont.modeling import (
    EpistemicStatus,
    ExperienceRecord,
    ModeledOrganismRuntime,
    PrivateModelOrganismRuntime,
    SourceKind,
    build_training_corpus,
)


def _direct(record_id: str, tick: int) -> ExperienceRecord:
    return ExperienceRecord(
        record_id=record_id,
        organism_id="organism-a",
        tick_class=tick,
        context_tokens=(f"sense.{tick}",),
        action_token=None,
        outcome_tokens=(f"outcome.{tick}",),
        epistemic_status=EpistemicStatus.OBSERVED,
        evidence_refs=(f"evidence.{tick}",),
        confidence_class=7,
        source_kind=SourceKind.DIRECT,
    )


def test_raw_and_contradicted_model_predictions_cannot_train_successor():
    records = [_direct(f"r{tick}", tick) for tick in range(4)]
    prediction = ExperienceRecord(
        record_id="model.p1",
        organism_id="organism-a",
        tick_class=5,
        context_tokens=("sense.1",),
        action_token=None,
        outcome_tokens=("outcome.predicted",),
        epistemic_status=EpistemicStatus.PREDICTED,
        evidence_refs=(),
        confidence_class=6,
        source_kind=SourceKind.MODEL,
    )
    contradicted = ExperienceRecord(
        record_id="validation.bad",
        organism_id="organism-a",
        tick_class=6,
        context_tokens=("sense.1",),
        action_token=None,
        outcome_tokens=("outcome.wrong",),
        epistemic_status=EpistemicStatus.CONTRADICTED,
        evidence_refs=("evidence.actual",),
        confidence_class=6,
        source_kind=SourceKind.MODEL,
    )
    corpus = build_training_corpus((*records, prediction, contradicted))
    ids = {record.record_id for record in corpus.train + corpus.validation + corpus.test}
    assert prediction.record_id not in ids
    assert contradicted.record_id not in ids


def test_independently_supported_model_prediction_can_enter_future_corpus():
    records = [_direct(f"r{tick}", tick) for tick in range(4)]
    validated = ExperienceRecord(
        record_id="validation.p1",
        organism_id="organism-a",
        tick_class=5,
        context_tokens=("sense.1",),
        action_token=None,
        outcome_tokens=("outcome.predicted",),
        epistemic_status=EpistemicStatus.SUPPORTED,
        evidence_refs=("evidence.independent",),
        confidence_class=6,
        source_kind=SourceKind.MODEL,
    )
    corpus = build_training_corpus((*records, validated))
    all_records = corpus.train + corpus.validation + corpus.test
    assert validated.record_id in {record.record_id for record in all_records}


def test_private_runtime_captures_temporal_transition_and_restores_ledger():
    runtime = PrivateModelOrganismRuntime(
        organism_id="private-runtime",
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    first = runtime.tick()
    assert runtime.experience_ledger.records == ()

    second = runtime.tick()
    assert len(runtime.experience_ledger.records) == 1
    record = runtime.experience_ledger.records[0]
    assert record.record_id.startswith("transition.")
    assert record.tick_class == first.tick
    assert second.tick == first.tick + 1
    assert record.outcome_tokens
    assert all(
        "system_load" not in token and "storage_pressure" not in token
        for token in record.context_tokens
    )
    assert all(not token.startswith("event.") for token in record.context_tokens)

    restored = PrivateModelOrganismRuntime.from_checkpoint(runtime.checkpoint())
    assert restored.capture_private_experience is True
    assert restored.experience_ledger.records == runtime.experience_ledger.records
    assert restored._pending_private_frame is None


def test_private_runtime_captures_motor_as_context_and_next_tick_as_outcome():
    runtime = PrivateModelOrganismRuntime(
        organism_id="private-motor",
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    a = Actuation(
        actuator_id="actuator.0123456789abcdef",
        requested=0.8,
        delivered=0.6,
        cost=0.01,
        health_at_execution=1.0,
    )
    b = Actuation(
        actuator_id="actuator.fedcba9876543210",
        requested=0.5,
        delivered=0.4,
        cost=0.01,
        health_at_execution=1.0,
    )
    acted = RuntimeTickResult(
        tick=1,
        snapshot=None,
        percepts=(),
        drift_observations={},
        allocations=(),
        investigated_capability=None,
        evidence_gathered=0,
        dissent=None,
        narrative=(),
        actuation=a,
        actuations=(a, b),
    )
    observed_after = RuntimeTickResult(
        tick=2,
        snapshot=None,
        percepts=(),
        drift_observations={},
        allocations=(),
        investigated_capability=None,
        evidence_gathered=0,
        dissent=None,
        narrative=(),
    )

    previous = runtime._capture_private_frame(acted)
    current = runtime._capture_private_frame(observed_after)
    episode = runtime._finalize_private_transition(previous, current)

    assert episode.action_token == "action.motor.composite"
    assert "actuator.0123456789abcdef" not in episode.action_token
    assert "actuator.fedcba9876543210" not in episode.action_token
    assert sum("delivered." in token for token in episode.context_tokens) == 2
    assert episode.outcome_tokens == ("outcome.sensory.stable",)
    assert episode.source_kind is SourceKind.ACTION_OUTCOME
    joined = " ".join(
        (*episode.context_tokens, *episode.outcome_tokens, episode.action_token)
    ).lower()
    for anatomical_term in ("arm", "leg", "knee", "elbow", "shoulder", "hip"):
        assert anatomical_term not in joined


def test_private_runtime_drops_pending_transition_on_terminal_tick(monkeypatch):
    runtime = PrivateModelOrganismRuntime(
        organism_id="private-terminal",
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    prior = RuntimeTickResult(
        tick=1,
        snapshot=None,
        percepts=(),
        drift_observations={},
        allocations=(),
        investigated_capability=None,
        evidence_gathered=0,
        dissent=None,
        narrative=(),
    )
    runtime._pending_private_frame = runtime._capture_private_frame(prior)

    terminal = RuntimeTickResult(
        tick=2,
        snapshot=None,
        percepts=(),
        drift_observations={},
        allocations=(),
        investigated_capability=None,
        evidence_gathered=0,
        dissent=None,
        narrative=(),
        runtime_events=("death", "resource_release"),
    )

    monkeypatch.setattr(
        ModeledOrganismRuntime,
        "tick",
        lambda self: terminal,
    )

    result = runtime.tick()

    assert result is terminal
    assert runtime._pending_private_frame is None
    assert runtime.experience_ledger.records == ()


def test_private_runtime_uses_opaque_primitive_identity_as_action_token():
    runtime = PrivateModelOrganismRuntime(
        organism_id="private-primitive-token",
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    runtime._last_executed_primitive_id = "primitive.0123456789abcdef"
    runtime._last_motor_origin_detail = "primitive_prospective"
    actuation = Actuation(
        actuator_id="actuator.0123456789abcdef",
        requested=0.5,
        delivered=0.4,
        cost=0.01,
        health_at_execution=1.0,
    )
    result = RuntimeTickResult(
        tick=1,
        snapshot=None,
        percepts=(),
        drift_observations={},
        allocations=(),
        investigated_capability=None,
        evidence_gathered=0,
        dissent=None,
        narrative=(),
        actuation=actuation,
        actuations=(actuation,),
    )

    frame = runtime._capture_private_frame(result)

    assert frame.action_token == "action.primitive.0123456789abcdef"
    assert all("requested." not in token for token in frame.context_tokens)
    assert all("delivered." not in token for token in frame.context_tokens)


def test_observed_outcome_credit_never_uses_counterfactual_prediction():
    runtime = PrivateModelOrganismRuntime(
        organism_id="private-observed-value",
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    episode = ExperienceRecord(
        record_id="transition.observed",
        organism_id=runtime.organism_id,
        tick_class=10,
        context_tokens=("sense.opaque",),
        action_token="action.primitive.actual",
        outcome_tokens=("outcome.observed.actual",),
        epistemic_status=EpistemicStatus.OBSERVED,
        evidence_refs=("evidence.actual",),
        confidence_class=7,
        source_kind=SourceKind.ACTION_OUTCOME,
    )

    runtime._schedule_observed_outcome_value_credit(
        episode,
        baseline_deviation=0.8,
        tick=10,
    )

    assert runtime._pending_outcome_value_credit
    assert {
        outcome_id
        for _due, outcome_id, _baseline, _discount in runtime._pending_outcome_value_credit
    } == {"outcome.observed.actual"}


def test_counterfactual_context_uses_training_vocabulary_not_concept_tokens():
    from types import SimpleNamespace

    runtime = PrivateModelOrganismRuntime(
        organism_id="private-context-vocabulary",
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    percept = SimpleNamespace(name="opaque.input", value=0.75)
    tokens = runtime._private_context_tokens_from_percepts(
        (percept,),
        {"opaque.input": "signal.opaque.123"},
    )

    assert "sense.signal.opaque.123" in tokens
    assert any(token.startswith("state.sense.") for token in tokens)
    assert all("concept.active" not in token for token in tokens)


def test_private_frame_captures_pre_consequence_homeostatic_baseline():
    runtime = PrivateModelOrganismRuntime(
        organism_id="private-homeostatic-frame",
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    result = RuntimeTickResult(
        tick=1,
        snapshot=None,
        percepts=(),
        drift_observations={},
        allocations=(),
        investigated_capability=None,
        evidence_gathered=0,
        dissent=None,
        narrative=(),
    )

    frame = runtime._capture_private_frame(result)

    assert frame.homeostatic_deviation == runtime.homeostatic_deviation


def test_observed_outcome_credit_resolves_against_pre_consequence_baseline(monkeypatch):
    runtime = PrivateModelOrganismRuntime(
        organism_id="private-immediate-value",
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    episode = ExperienceRecord(
        record_id="transition.immediate",
        organism_id=runtime.organism_id,
        tick_class=10,
        context_tokens=("sense.opaque",),
        action_token="action.primitive.actual",
        outcome_tokens=("outcome.immediate",),
        epistemic_status=EpistemicStatus.OBSERVED,
        evidence_refs=("evidence.immediate",),
        confidence_class=7,
        source_kind=SourceKind.ACTION_OUTCOME,
    )
    runtime._schedule_observed_outcome_value_credit(
        episode,
        baseline_deviation=0.8,
        tick=10,
    )
    monkeypatch.setattr(runtime._homeostasis, "deviation", lambda: 0.2)

    runtime._resolve_outcome_value_credit(tick=14)

    estimate = runtime._prospective_agency.outcome_value_ledger.estimate("outcome.immediate")
    assert estimate is not None
    assert estimate.mean_value == pytest.approx(0.6)


def test_private_frame_episodic_projection_uses_direct_cognitive_ids():
    runtime = PrivateModelOrganismRuntime(
        organism_id="private-cognitive-episode",
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    runtime._cognitive_bridge = SimpleNamespace(
        graph=SimpleNamespace(
            nodes=(
                SimpleNamespace(node_id="sensor.identity.alpha", kind=NodeKind.SENSE),
                SimpleNamespace(node_id="sensor.identity.beta", kind=NodeKind.SENSE),
                SimpleNamespace(node_id="concept.000001", kind=NodeKind.CONCEPT),
            )
        )
    )
    cognition = SimpleNamespace(
        activations={
            "sensor.identity.alpha": 0.9,
            "sensor.identity.beta": 0.4,
            "concept.000001": 0.8,
        },
        active_concept_ids=("concept.000001",),
    )
    result = RuntimeTickResult(
        tick=1,
        snapshot=None,
        percepts=(),
        drift_observations={},
        allocations=(),
        investigated_capability=None,
        evidence_gathered=0,
        dissent=None,
        narrative=(),
        cognition=cognition,
    )

    frame = runtime._capture_private_frame(result)

    assert frame.episodic_projection.sense_ids == (
        "sensor.identity.alpha",
        "sensor.identity.beta",
    )
    assert frame.episodic_projection.concept_ids == ("concept.000001",)
    assert all(
        not sense_id.startswith("signal.") for sense_id in frame.episodic_projection.sense_ids
    )
