from __future__ import annotations

import pytest

from symbiont_lab.physics3d.alternative_bodies import (
    ASYMMETRIC_SPEC,
    CRAWLER_SPEC,
    AsymmetricPhysics,
    CrawlerPhysics,
)
from symbiont_lab.physics3d.articulated import build_articulated_urdf


@pytest.mark.parametrize("spec", [CRAWLER_SPEC, ASYMMETRIC_SPEC])
def test_alternative_body_urdf_contains_exact_motor_constitution(spec) -> None:
    urdf = build_articulated_urdf(spec)

    assert urdf.count("<joint name=") == spec.motor_dof
    assert urdf.count('type="revolute"') == spec.motor_dof
    for joint in spec.joint_specs:
        assert f'name="{joint.name}"' in urdf


@pytest.mark.parametrize("spec", [CRAWLER_SPEC, ASYMMETRIC_SPEC])
def test_alternative_body_contract_dimensions_are_self_consistent(spec) -> None:
    assert spec.effector_count == spec.motor_dof * 2
    assert len(spec.effector_ids()) == spec.effector_count
    assert len(spec.receptor_ids()) == spec.total_receptor_count
    assert len(spec.interoceptive_receptor_ids()) == 4
    assert spec.total_receptor_count == (
        spec.motor_dof * 2 + 10 + spec.somatic_region_count * 2 + 1 + 4
    )


@pytest.mark.parametrize(
    ("body_cls", "spec"),
    [
        (CrawlerPhysics, CRAWLER_SPEC),
        (AsymmetricPhysics, ASYMMETRIC_SPEC),
    ],
)
def test_alternative_body_loads_headless_when_pybullet_available(body_cls, spec) -> None:
    pybullet = pytest.importorskip("pybullet")
    client = pybullet.connect(pybullet.DIRECT)
    try:
        body = body_cls(pybullet, client)
        assert len(body.motor_joint_indices) == spec.motor_dof
        assert len(body.effector_ids) == spec.effector_count
        assert len(body.receptor_ids) == spec.physical_receptor_count

        sampled = body.sample_receptors()
        assert tuple(sampled) == body.receptor_ids
        checkpoint = body.export_physical_state()
        assert checkpoint["body_kind"] == spec.body_kind
        assert checkpoint["schema_version"] == spec.state_schema_version
        assert len(checkpoint["joints"]) == spec.motor_dof
    finally:
        pybullet.disconnect(client)
