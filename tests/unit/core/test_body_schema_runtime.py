from __future__ import annotations

from symbiont.core.runtime import OrganismRuntime


def test_runtime_starts_with_undeveloped_body_schema():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)

    assert runtime.body_schema.state == "undeveloped"
    assert runtime.body_schema.part_count == 0
    assert runtime.checkpoint()["body_schema"]["state"] == "undeveloped"


def test_runtime_learns_partial_sensory_body_from_established_self_model():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)

    runtime.run(10)
    payload = runtime.body_schema.export_representation(current_tick=runtime.tick_count)

    assert payload["state"] == "partial"
    assert payload["parts"]
    assert all(part["kind"] == "sense" for part in payload["parts"])
    assert payload["dependencies"] == []
    assert "id_salt" not in payload
    # BodySchema ids are its own opaque namespace, not host capability ids.
    assert all(part["part_id"].startswith("part.sense.") for part in payload["parts"])


def test_runtime_checkpoint_round_trip_preserves_body_schema_and_private_identity_namespace():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)
    runtime.run(10)
    checkpoint = runtime.checkpoint()
    before_representation = runtime.body_schema.export_representation(current_tick=runtime.tick_count)

    restored = OrganismRuntime.from_checkpoint(checkpoint, min_samples=1, investigate_ticks=0)

    assert restored.body_schema.export(current_tick=restored.tick_count) == checkpoint["body_schema"]
    assert restored.body_schema.export_representation(current_tick=restored.tick_count) == before_representation
    assert "id_salt" in checkpoint["body_schema"]
    assert "id_salt" not in before_representation


def test_old_checkpoint_without_body_schema_restores_cold_and_learns_later():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)
    runtime.run(10)
    checkpoint = runtime.checkpoint()
    checkpoint.pop("body_schema")

    restored = OrganismRuntime.from_checkpoint(checkpoint, min_samples=1, investigate_ticks=0)

    assert restored.body_schema.state == "undeveloped"
    restored.tick()
    assert restored.body_schema.state == "partial"


def test_checkpoint_body_schema_never_contains_raw_self_model_keys():
    runtime = OrganismRuntime(min_samples=1, investigate_ticks=0)
    runtime.run(10)
    checkpoint = runtime.checkpoint()

    serialized_body = repr(checkpoint["body_schema"])
    for sense_id in checkpoint["self_model"]:
        assert sense_id not in serialized_body
