from __future__ import annotations

from dataclasses import replace
import json

import pytest

from symbiont.cognition.limits import KernelLimits
from symbiont.modeling.episodic import (
    EpisodicExperienceMemory,
    EpisodicMemoryError,
)
from symbiont.modeling.experience import (
    EpistemicStatus,
    ExperienceRecord,
    SourceKind,
)


ORG = "org_test"


def record(
    tick: int,
    *,
    context: tuple[str, ...] = ("sense.a", "state.a"),
    action: str | None = "action.p",
    outcomes: tuple[str, ...] = ("outcome.x",),
    record_id: str | None = None,
    status: EpistemicStatus = EpistemicStatus.OBSERVED,
    source: SourceKind = SourceKind.ACTION_OUTCOME,
) -> ExperienceRecord:
    return ExperienceRecord(
        record_id=record_id or f"transition.{tick:08d}",
        organism_id=ORG,
        tick_class=tick,
        context_tokens=context,
        action_token=action,
        outcome_tokens=outcomes,
        epistemic_status=status,
        evidence_refs=(f"evidence.{tick}",),
        confidence_class=7,
        source_kind=source,
    )


def test_only_independently_observed_transitions_become_lived_experience() -> None:
    memory = EpisodicExperienceMemory(ORG)
    predicted = record(
        0,
        record_id="model.00000000",
        status=EpistemicStatus.PREDICTED,
        source=SourceKind.MODEL,
    )
    memory.observe(predicted)
    assert memory.flush() is None
    assert memory.episodes == ()

    memory.observe(record(1))
    memory.flush()
    assert len(memory.episodes) == 1
    assert memory.episodes[0].source_record_ids == ("transition.00000001",)


def test_episode_segmentation_and_contextual_retrieval() -> None:
    memory = EpisodicExperienceMemory(ORG)
    memory.observe(record(0, context=("sense.a", "state.low"), action="action.p"))
    memory.observe(record(1, context=("sense.a", "state.low"), action="action.p"))
    # Different action is a generic motor-regime boundary.
    finalized = memory.observe(
        record(2, context=("sense.b", "state.high"), action="action.q", outcomes=("outcome.y",))
    )
    assert finalized is not None
    memory.flush()

    matches = memory.retrieve(("sense.a", "state.low"), action_token="action.p")
    assert matches
    assert matches[0].similarity > 0.7
    assert "action.p" in matches[0].episode.action_tokens


def test_reinterpretation_never_rewrites_factual_episode_core() -> None:
    memory = EpisodicExperienceMemory(ORG)
    memory.observe(record(0, context=("sense.a", "sense.b")))
    memory.flush()
    before = memory.episodes[0]

    changed = memory.reinterpret(
        "concept.new",
        ("sense.a", "sense.b"),
        min_overlap=1.0,
    )

    assert changed == 1
    assert memory.episodes[0] == before
    assert memory.interpretations_for(before.episode_id) == ("concept.new",)


def test_consolidation_requires_independent_temporal_epochs() -> None:
    limits = replace(
        KernelLimits(),
        episodic_epoch_ticks=10,
        episodic_min_consolidation_epochs=3,
    )
    memory = EpisodicExperienceMemory(ORG, kernel_limits=limits)
    for tick in (0, 10, 20):
        memory.observe(
            record(
                tick,
                context=("sense.a", "state.low"),
                action="action.p",
                outcomes=("outcome.x",),
            )
        )
        memory.flush()

    consolidated = memory.consolidate()
    assert len(consolidated) == 1
    item = consolidated[0]
    assert item.support_epochs == 3
    assert item.action_token == "action.p"
    assert item.outcome_tokens == ("outcome.x",)
    assert "sense.a" in item.context_tokens


def test_same_epoch_repetition_does_not_fake_independent_evidence() -> None:
    limits = replace(
        KernelLimits(),
        episodic_epoch_ticks=100,
        episodic_min_consolidation_epochs=2,
    )
    memory = EpisodicExperienceMemory(ORG, kernel_limits=limits)
    for tick in (1, 2, 3):
        memory.observe(record(tick))
        memory.flush()
    assert memory.consolidate() == ()


def test_state_conditioned_prediction_uses_similar_lived_experience() -> None:
    memory = EpisodicExperienceMemory(ORG)
    for tick in (0, 100, 200):
        memory.observe(
            record(
                tick,
                context=("sense.a", "posture.cluster.1"),
                action="action.p",
                outcomes=("outcome.left",),
            )
        )
        memory.flush()
    memory.observe(
        record(
            300,
            context=("sense.z", "posture.cluster.9"),
            action="action.p",
            outcomes=("outcome.right",),
        )
    )
    memory.flush()

    prediction = memory.predict(
        ("sense.a", "posture.cluster.1"),
        action_token="action.p",
    )
    assert prediction is not None
    assert prediction.predicted_outcomes[0] == "outcome.left"
    assert prediction.confidence > 0.5


def test_cognitive_replay_is_reactivation_only() -> None:
    memory = EpisodicExperienceMemory(ORG)
    memory.observe(record(0))
    memory.flush()
    before = memory.episodes

    replay = memory.cognitive_replay(("sense.a",), action_token="action.p")

    assert replay
    assert replay[0].action_tokens == ("action.p",)
    assert replay[0].trace
    assert replay[0].trace[0].context_tokens == ("sense.a", "state.a")
    assert memory.episodes == before
    assert memory.metrics(current_tick=1).replay_count == 1


def test_capacity_compacts_redundant_episodes_before_eviction() -> None:
    limits = replace(KernelLimits(), max_episodic_episodes=2)
    memory = EpisodicExperienceMemory(ORG, kernel_limits=limits)
    for tick in (0, 100, 200):
        memory.observe(
            record(
                tick,
                context=("sense.a", "state.same"),
                action="action.p",
                outcomes=("outcome.x",),
            )
        )
        memory.flush()

    assert len(memory.episodes) <= 2
    assert any(episode.compressed for episode in memory.episodes)
    assert sum(episode.recurrence for episode in memory.episodes) == 3
    metrics = memory.metrics(current_tick=201)
    assert metrics.compaction_count >= 1
    assert metrics.eviction_count == 0


def test_checkpoint_restores_pending_episodes_and_interpretations() -> None:
    memory = EpisodicExperienceMemory(ORG)
    memory.observe(record(0, context=("sense.a", "sense.b")))
    memory.flush()
    episode_id = memory.episodes[0].episode_id
    memory.reinterpret("concept.ab", ("sense.a", "sense.b"), min_overlap=1.0)
    memory.observe(record(1, context=("sense.pending",), action=None))

    payload = memory.checkpoint()
    restored = EpisodicExperienceMemory.restore(payload, organism_id=ORG)

    assert restored.episodes == memory.episodes
    assert restored.interpretations_for(episode_id) == ("concept.ab",)
    assert restored.metrics(current_tick=2).pending_records == 1
    restored.flush()
    assert len(restored.episodes) == 2


def test_checkpoint_fails_closed_on_wrong_schema_or_organism() -> None:
    memory = EpisodicExperienceMemory(ORG)
    payload = memory.checkpoint()

    bad_schema = dict(payload)
    bad_schema["schema_version"] = 999
    with pytest.raises(EpisodicMemoryError):
        EpisodicExperienceMemory.restore(bad_schema, organism_id=ORG)

    with pytest.raises(EpisodicMemoryError):
        EpisodicExperienceMemory.restore(payload, organism_id="other")



def test_reinterpretations_are_kernel_bounded() -> None:
    limits = replace(
        KernelLimits(),
        max_episodic_interpretations_per_episode=2,
    )
    memory = EpisodicExperienceMemory(ORG, kernel_limits=limits)
    memory.observe(record(0, context=("sense.a", "sense.b")))
    memory.flush()

    assert memory.reinterpret("concept.1", ("sense.a",), min_overlap=1.0) == 1
    assert memory.reinterpret("concept.2", ("sense.a",), min_overlap=1.0) == 1
    assert memory.reinterpret("concept.3", ("sense.a",), min_overlap=1.0) == 0
    assert memory.interpretations_for(memory.episodes[0].episode_id) == (
        "concept.1",
        "concept.2",
    )



def test_byte_pressure_is_enforced_before_checkpoint() -> None:
    limits = replace(
        KernelLimits(),
        max_episodic_episodes=64,
        max_episodic_checkpoint_bytes=2_400,
    )
    memory = EpisodicExperienceMemory(ORG, kernel_limits=limits)
    for tick in range(12):
        memory.observe(
            record(
                tick * 10,
                context=(f"sense.{tick}", "state.shared"),
                action=f"action.{tick % 3}",
                outcomes=(f"outcome.{tick % 4}",),
            )
        )
        memory.flush()

    payload = memory.checkpoint()
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    assert len(encoded) <= limits.max_episodic_checkpoint_bytes
    assert len(memory.episodes) < 12
    assert memory.metrics(current_tick=120).eviction_count > 0



def test_higher_order_interpretation_can_index_prior_interpretation() -> None:
    memory = EpisodicExperienceMemory(ORG)
    memory.observe(record(0, context=("sense.a", "sense.b")))
    memory.flush()
    episode_id = memory.episodes[0].episode_id

    assert memory.reinterpret("concept.low", ("sense.a",), min_overlap=1.0) == 1
    assert memory.reinterpret("concept.high", ("concept.low",), min_overlap=1.0) == 1

    assert memory.interpretations_for(episode_id) == (
        "concept.high",
        "concept.low",
    )
