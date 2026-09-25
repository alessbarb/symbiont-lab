from __future__ import annotations

import pytest

from symbiont_lab.physics3d.bodies import DEFAULT_BODY_REGISTRY


def test_default_body_registry_exposes_canonical_anthropomorphic_contract() -> None:
    descriptor = DEFAULT_BODY_REGISTRY.get("anthropomorphic-v6")
    assert descriptor.body_kind == "anthropomorphic-v6"
    assert descriptor.motor_dof == 31
    assert descriptor.receptor_count > 31
    assert descriptor.effector_count == 62
    assert descriptor.as_dict()["available"] is True


def test_body_registry_rejects_unknown_body_kind() -> None:
    with pytest.raises(ValueError, match="unsupported body kind"):
        DEFAULT_BODY_REGISTRY.get("unknown-body")


def test_default_registry_exposes_three_distinct_morphologies() -> None:
    bodies = {item.body_kind: item for item in DEFAULT_BODY_REGISTRY.list()}
    assert set(bodies) == {
        "anthropomorphic-v6",
        "crawler-v1",
        "asymmetric-v1",
    }

    assert bodies["crawler-v1"].motor_dof == 12
    assert bodies["crawler-v1"].effector_count == 24
    assert bodies["crawler-v1"].receptor_count == 57

    assert bodies["asymmetric-v1"].motor_dof == 15
    assert bodies["asymmetric-v1"].effector_count == 30
    assert bodies["asymmetric-v1"].receptor_count == 69

    contracts = {
        (
            body.receptor_count,
            body.effector_count,
        )
        for body in bodies.values()
    }
    assert len(contracts) == 3


def test_alternative_body_contracts_remain_opaque_ordinals() -> None:
    for body_kind in ("crawler-v1", "asymmetric-v1"):
        descriptor = DEFAULT_BODY_REGISTRY.get(body_kind)
        assert descriptor.receptor_ids == tuple(
            f"rec.{i}" for i in range(descriptor.receptor_count)
        )
        assert descriptor.effector_ids == tuple(
            f"eff.{i}" for i in range(descriptor.effector_count)
        )
        assert len(descriptor.interoceptive_receptor_ids) == 4


def test_body_catalog_exposes_observer_only_presentation_models() -> None:
    for descriptor in DEFAULT_BODY_REGISTRY.list():
        payload = descriptor.as_dict()
        model = payload["observer_model"]
        assert model["base_link"]
        assert len(model["joints"]) == descriptor.motor_dof
        assert model["segments"]
        assert all(len(item["axis"]) == 3 for item in model["joints"])
