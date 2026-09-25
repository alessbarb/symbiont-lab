import pytest

from symbiont.actuation.dimension import (
    ActionDimension,
    ActionDimensionRegistry,
    opaque_dimension_id,
)


def test_opaque_dimension_id_is_deterministic_and_opaque():
    first = opaque_dimension_id("slot.0")
    second = opaque_dimension_id("slot.0")
    other = opaque_dimension_id("slot.1")

    assert first == second
    assert first != other
    assert first.startswith("action.dimension.")
    assert "slot.0" not in first


def test_action_dimension_rejects_non_opaque_id():
    with pytest.raises(ValueError):
        ActionDimension(
            dimension_id="right_knee",
            actuator_slot_id="slot.0",
            availability=True,
            controllability=0.0,
            confidence=0.0,
            usage_count=0,
            embodiment_bound=False,
        )


def test_action_dimension_rejects_out_of_range_scores():
    with pytest.raises(ValueError):
        ActionDimension(
            dimension_id=opaque_dimension_id("slot.0"),
            actuator_slot_id="slot.0",
            availability=True,
            controllability=1.5,
            confidence=0.0,
            usage_count=0,
            embodiment_bound=False,
        )


def test_registry_discover_is_idempotent():
    registry = ActionDimensionRegistry()

    first = registry.discover("slot.0")
    second = registry.discover("slot.0")

    assert first == second
    assert len(registry.items) == 1
    assert registry.get(first).usage_count == 0


def test_registry_record_usage_accumulates_and_clamps():
    registry = ActionDimensionRegistry()
    dimension_id = registry.discover("slot.0")

    registry.record_usage(dimension_id, controllability=1.4, confidence=-0.2, embodiment_bound=True)
    updated = registry.get(dimension_id)

    assert updated.usage_count == 1
    assert updated.controllability == 1.0
    assert updated.confidence == 0.0
    assert updated.embodiment_bound is True


def test_registry_record_usage_unknown_dimension_raises():
    registry = ActionDimensionRegistry()

    with pytest.raises(KeyError):
        registry.record_usage("action.dimension.missing", controllability=0.5, confidence=0.5, embodiment_bound=False)


def test_registry_enforces_capacity_keeping_most_used():
    registry = ActionDimensionRegistry(capacity=2)
    a = registry.discover("slot.a")
    b = registry.discover("slot.b")
    registry.record_usage(a, controllability=0.1, confidence=0.1, embodiment_bound=False)
    registry.record_usage(a, controllability=0.1, confidence=0.1, embodiment_bound=False)
    registry.record_usage(b, controllability=0.1, confidence=0.1, embodiment_bound=False)
    c = registry.discover("slot.c")

    assert len(registry.items) == 2
    remaining_ids = {item.dimension_id for item in registry.items}
    assert a in remaining_ids
    assert b in remaining_ids
    assert c not in remaining_ids


def test_registry_checkpoint_restore_roundtrip():
    registry = ActionDimensionRegistry(capacity=8)
    dimension_id = registry.discover("slot.0")
    registry.record_usage(dimension_id, controllability=0.7, confidence=0.6, embodiment_bound=True)

    restored = ActionDimensionRegistry.restore(registry.checkpoint())

    assert restored.checkpoint() == registry.checkpoint()


def test_registry_restore_none_gives_empty_registry():
    restored = ActionDimensionRegistry.restore(None)
    assert restored.items == ()


def test_registry_restore_rejects_wrong_schema_version():
    with pytest.raises(ValueError):
        ActionDimensionRegistry.restore({"schema_version": 99, "capacity": 8, "items": []})
