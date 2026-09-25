from __future__ import annotations

import json
from dataclasses import replace

import pytest

from symbiont.cognition.limits import KernelLimits
from symbiont.modeling.episodic import (
    EpisodicExperienceMemory,
    EpisodicMemoryError,
    EpisodicProjection,
)
from symbiont.modeling.experience import (
    EpistemicStatus,
    ExperienceRecord,
    SourceKind,
)

ORG = "episodic-v2-test"


def record(
    tick: int,
    *,
    context: tuple[str, ...] = ("sense.raw.a", "internal.pressure.low"),
    action: str | None = "action.motor.composite",
    outcomes: tuple[str, ...] = ("outcome.sense.channel.a.up.3",),
    status: EpistemicStatus = EpistemicStatus.OBSERVED,
    source: SourceKind = SourceKind.ACTION_OUTCOME,
) -> ExperienceRecord:
    return ExperienceRecord(
        record_id=f"transition.test.{tick}",
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


def projection(
    *,
    senses: tuple[str, ...] = ("sensor.identity.alpha", "sensor.identity.beta"),
    concepts: tuple[str, ...] = ("concept.000001",),
    internal: tuple[str, ...] = ("internal.pressure.low",),
    action: str | None = "action.motor.composite",
    outcomes: tuple[str, ...] = ("outcome.sense.channel.a.up.3",),
) -> EpisodicProjection:
    return EpisodicProjection(
        sense_ids=senses,
        concept_ids=concepts,
        internal_tokens=internal,
        action_token=action,
    ).with_effects(outcomes)


def test_model_records_never_become_lived_episodes() -> None:
    memory = EpisodicExperienceMemory(ORG)
    predicted = ExperienceRecord(
        record_id="model.test",
        organism_id=ORG,
        tick_class=0,
        context_tokens=("sense.raw.a",),
        action_token=None,
        outcome_tokens=("outcome.predicted",),
        epistemic_status=EpistemicStatus.PREDICTED,
        evidence_refs=(),
        confidence_class=4,
        source_kind=SourceKind.MODEL,
    )
    assert memory.observe(predicted) is None
    assert memory.flush() is None
    assert memory.episodes == ()


def test_direct_cognitive_projection_is_preserved_in_family() -> None:
    memory = EpisodicExperienceMemory(ORG)
    memory.observe(record(0), projection())
    memory.flush()

    episode = memory.episodes[0]
    assert episode.projection.sense_ids == (
        "sensor.identity.alpha",
        "sensor.identity.beta",
    )
    assert episode.projection.concept_ids == ("concept.000001",)
    assert "sense.raw.a" not in episode.projection.sense_ids


def test_continuous_variants_compact_into_one_family() -> None:
    limits = replace(KernelLimits(), episodic_epoch_ticks=10)
    memory = EpisodicExperienceMemory(ORG, kernel_limits=limits)

    variants = (
        ("outcome.sense.channel.a.up.2",),
        ("outcome.sense.channel.a.up.3",),
        ("outcome.sense.channel.a.up.4",),
        ("outcome.sense.channel.a.up.5",),
    )
    for index, outcomes in enumerate(variants):
        memory.observe(
            record(index * 10, outcomes=outcomes),
            projection(outcomes=outcomes),
        )
        memory.flush()

    assert len(memory.episodes) == 1
    family = memory.episodes[0]
    assert family.recurrence == 4
    assert family.compressed is True
    assert memory.metrics(current_tick=40).compaction_count == 3
    assert family.projection.effect_features


def test_state_similarity_tolerates_partial_sensor_overlap() -> None:
    left = projection(
        senses=("sensor.a", "sensor.b", "sensor.c"),
        concepts=("concept.x",),
    )
    right = projection(
        senses=("sensor.a", "sensor.b", "sensor.d"),
        concepts=("concept.x",),
    )
    unrelated = projection(
        senses=("sensor.x", "sensor.y"),
        concepts=("concept.z",),
        internal=("internal.pressure.high",),
    )

    related_score = EpisodicExperienceMemory.projection_similarity(left, right)
    unrelated_score = EpisodicExperienceMemory.projection_similarity(left, unrelated)

    assert related_score > 0.65
    assert related_score > unrelated_score


def test_empty_concept_sets_do_not_create_false_similarity() -> None:
    left = projection(
        senses=("sensor.a",),
        concepts=(),
        internal=("internal.pressure.low",),
    )
    right = projection(
        senses=("sensor.z",),
        concepts=(),
        internal=("internal.pressure.high",),
    )

    assert EpisodicExperienceMemory.projection_similarity(left, right) < 0.4


def test_consolidation_uses_independent_epochs_of_same_family() -> None:
    limits = replace(
        KernelLimits(),
        episodic_epoch_ticks=10,
        episodic_min_consolidation_epochs=3,
    )
    memory = EpisodicExperienceMemory(ORG, kernel_limits=limits)

    for tick in (0, 10, 20):
        memory.observe(record(tick), projection())
        memory.flush()

    consolidated = memory.consolidate()
    assert len(consolidated) == 1
    item = consolidated[0]
    assert item.support_epochs == 3
    assert item.sense_ids == (
        "sensor.identity.alpha",
        "sensor.identity.beta",
    )
    assert item.concept_ids == ("concept.000001",)


def test_reinterpretation_indexes_old_family_without_rewriting_projection() -> None:
    memory = EpisodicExperienceMemory(ORG)
    memory.observe(record(0), projection(concepts=()))
    memory.flush()
    before = memory.episodes[0].projection

    changed = memory.reinterpret(
        "concept.new",
        ("sensor.identity.alpha", "sensor.identity.beta"),
        min_overlap=1.0,
    )

    assert changed == 1
    assert memory.episodes[0].projection == before
    assert memory.interpretations_for(memory.episodes[0].episode_id) == ("concept.new",)


def test_prediction_is_conditioned_on_sparse_cognitive_state() -> None:
    memory = EpisodicExperienceMemory(ORG)
    for index in range(4):
        outcomes = ("outcome.sense.channel.a.up.3",)
        memory.observe(
            record(index * 10, outcomes=outcomes),
            projection(
                senses=("sensor.state.a",),
                concepts=("concept.state.a",),
                outcomes=outcomes,
            ),
        )
        memory.flush()

    for index in range(4):
        outcomes = ("outcome.sense.channel.a.down.3",)
        memory.observe(
            record(100 + index * 10, outcomes=outcomes),
            projection(
                senses=("sensor.state.b",),
                concepts=("concept.state.b",),
                outcomes=outcomes,
            ),
        )
        memory.flush()

    predicted = memory.predict(
        EpisodicProjection(
            sense_ids=("sensor.state.a",),
            concept_ids=("concept.state.a",),
            internal_tokens=("internal.pressure.low",),
            action_token="action.motor.composite",
        ),
        action_token="action.motor.composite",
    )

    assert predicted is not None
    assert any(
        ".up" in token or token == "effect.balance.up" for token in predicted.predicted_outcomes
    )


def test_compact_families_fit_hundreds_under_default_byte_budget() -> None:
    memory = EpisodicExperienceMemory(ORG)
    for index in range(220):
        senses = (f"sensor.identity.{index:04d}",)
        concepts = (f"concept.{index % 32:06d}",)
        outcomes = (f"outcome.sense.channel.{index:04d}.up.{index % 7}",)
        memory.observe(
            record(
                index * 2,
                action=f"action.{index:04d}",
                outcomes=outcomes,
            ),
            projection(
                senses=senses,
                concepts=concepts,
                action=f"action.{index:04d}",
                outcomes=outcomes,
            ),
        )
        memory.flush()

    payload = memory.checkpoint()
    size = len(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())

    assert len(memory.episodes) >= 180
    assert size <= KernelLimits().max_episodic_checkpoint_bytes
    assert memory.metrics(current_tick=500).eviction_count == 0


def test_checkpoint_does_not_bridge_pending_episode_across_restart() -> None:
    memory = EpisodicExperienceMemory(ORG)
    memory.observe(record(0), projection())
    assert memory.metrics(current_tick=0).pending_records == 1

    restored = EpisodicExperienceMemory.restore(
        memory.checkpoint(),
        organism_id=ORG,
    )

    assert restored.metrics(current_tick=0).pending_records == 0
    assert restored.episodes == ()


def test_v1_checkpoint_migrates_to_sparse_v2() -> None:
    legacy = {
        "schema_version": 1,
        "organism_id": ORG,
        "episodes": [
            {
                "episode_id": "episode.legacy",
                "start_tick": 10,
                "end_tick": 10,
                "occurrence_ticks": [10],
                "trace": [],
                "initial_context": [
                    "sense.signal.aaa",
                    "internal.pressure.low",
                ],
                "terminal_context": [],
                "action_tokens": ["action.motor.composite"],
                "outcome_tokens": ["outcome.sense.channel.a.up.3"],
                "evidence_refs": ["evidence.legacy"],
                "source_record_ids": ["transition.legacy"],
                "novelty": 1.0,
                "surprise": 1.0,
                "recurrence": 1,
                "compressed": False,
            }
        ],
        "interpretations": {},
        "retrieval_counts": {},
        "metrics": {},
    }

    restored = EpisodicExperienceMemory.restore(
        legacy,
        organism_id=ORG,
    )

    assert restored.SCHEMA_VERSION == 2
    assert len(restored.episodes) == 1
    assert restored.episodes[0].projection.effect_features


def test_checkpoint_rejects_wrong_identity() -> None:
    memory = EpisodicExperienceMemory(ORG)
    payload = memory.checkpoint()
    with pytest.raises(EpisodicMemoryError):
        EpisodicExperienceMemory.restore(payload, organism_id="other")


def test_provenance_retains_hash_not_raw_context() -> None:
    memory = EpisodicExperienceMemory(ORG)
    original = record(
        0,
        context=tuple(f"sense.raw.{index}" for index in range(100)),
    )
    memory.observe(original, projection())
    memory.flush()

    episode = memory.episodes[0]
    assert episode.trace
    assert episode.trace[0].source_content_hash == original.content_hash
    checkpoint_text = json.dumps(memory.checkpoint())
    assert "sense.raw.99" not in checkpoint_text


def test_episodic_memory_does_not_fabricate_raw_replay_records() -> None:
    memory = EpisodicExperienceMemory(ORG)
    memory.observe(record(0), projection())
    memory.flush()
    assert memory.replay_records() == ()


def test_borderline_family_variant_is_retained_as_bounded_exception() -> None:
    memory = EpisodicExperienceMemory(ORG)
    base_outcomes = (
        "outcome.sense.channel.a.up.3",
        "outcome.sense.channel.b.up.3",
    )
    variant_outcomes = (
        "outcome.sense.channel.a.up.4",
        "outcome.sense.channel.c.up.4",
    )
    memory.observe(
        record(0, outcomes=base_outcomes),
        projection(
            senses=("sensor.a", "sensor.b", "sensor.c"),
            concepts=("concept.shared",),
            outcomes=base_outcomes,
        ),
    )
    memory.flush()
    memory.observe(
        record(10, outcomes=variant_outcomes),
        projection(
            senses=("sensor.d", "sensor.e", "sensor.f"),
            concepts=("concept.shared",),
            outcomes=variant_outcomes,
        ),
    )
    memory.flush()

    assert len(memory.episodes) == 1
    family = memory.episodes[0]
    assert family.recurrence == 2
    assert 1 <= len(family.exceptions) <= 4

    match = memory.retrieve(
        EpisodicProjection(
            sense_ids=("sensor.d", "sensor.e", "sensor.f"),
            concept_ids=("concept.shared",),
            internal_tokens=("internal.pressure.low",),
            action_token="action.motor.composite",
        ),
        action_token="action.motor.composite",
        k=1,
    )
    assert match
    assert match[0].episode_id == family.episode_id
