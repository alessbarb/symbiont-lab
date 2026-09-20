from __future__ import annotations

from symbiont.actuation.types import Actuation
from symbiont.core.runtime import RuntimeTickResult
from symbiont.modeling import (
    EpistemicStatus,
    ExperienceRecord,
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
    assert all("system_load" not in token and "storage_pressure" not in token for token in record.context_tokens)
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
        actuation=Actuation(
            actuator_id="actuator.0123456789abcdef",
            requested=0.8,
            delivered=0.6,
            cost=0.01,
            health_at_execution=1.0,
        ),
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

    assert episode.action_token is not None
    assert episode.action_token.startswith("action.motor.")
    assert "actuator.0123456789abcdef" not in episode.action_token
    assert "internal.motor.delivered.4" in episode.context_tokens
    assert episode.outcome_tokens == ("outcome.sensory.stable",)
    assert episode.source_kind is SourceKind.ACTION_OUTCOME
    joined = " ".join(
        (*episode.context_tokens, *episode.outcome_tokens, episode.action_token)
    ).lower()
    for anatomical_term in ("arm", "leg", "knee", "elbow", "shoulder", "hip"):
        assert anatomical_term not in joined
