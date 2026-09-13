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
