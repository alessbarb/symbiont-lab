from __future__ import annotations

import pytest

from symbiont_lab.physics3d.bodies import DEFAULT_BODY_REGISTRY


def test_default_body_registry_exposes_canonical_anthropomorphic_contract() -> None:
    descriptor = DEFAULT_BODY_REGISTRY.get("anthropomorphic-v4")
    assert descriptor.body_kind == "anthropomorphic-v4"
    assert descriptor.motor_dof == 31
    assert descriptor.receptor_count > 31
    assert descriptor.effector_count == 62
    assert descriptor.as_dict()["available"] is True


def test_body_registry_rejects_unknown_body_kind() -> None:
    with pytest.raises(ValueError, match="unsupported body kind"):
        DEFAULT_BODY_REGISTRY.get("unknown-body")
